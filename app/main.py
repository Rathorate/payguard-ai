import hmac
import io
import json
import logging
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile, File, Form, Query, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, update, delete, func, or_
from sqlalchemy.exc import IntegrityError
from pypdf import PdfReader

from .config import Settings
from .models import Base, Tenant, User, LoginSession, Dispute, Audit, Webhook, Submission, RateBucket, database
from .security import digest, hash_password, verify_password
from .providers import PayPal, ProviderError, generate_draft
from .schemas import Credentials, Registration, NewDispute, NewEvidence, Version, DraftEdit, Approval, SubmissionInput
from .service import audit, get_dispute, evidence_for, transition, editable, add_evidence, serialize, demo_seed

log = logging.getLogger('payguard')
STATIC = Path(__file__).resolve().parent.parent / 'static'
MAX_BODY = 6 * 1024 * 1024


def create_app(settings=None):
    settings = settings or Settings()
    settings.validate()
    engine, sessions = database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app):
        if settings.demo:
            Base.metadata.create_all(engine)
        yield
        engine.dispose()

    app = FastAPI(title='PayGuard AI', version='1.0.0', lifespan=lifespan)
    app.state.settings, app.state.sessions, app.state.engine = settings, sessions, engine
    app.state.paypal = PayPal(settings)
    app.state.drafter = generate_draft

    # ASGI body cap also covers chunked uploads; never trust Content-Length alone.
    class BodyLimit:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope['type'] != 'http':
                return await self.app(scope, receive, send)
            size, chunks = 0, []
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                size += len(message.get('body', b''))
                if size > MAX_BODY:
                    await send({'type': 'http.response.start', 'status': 413, 'headers': [(b'content-type', b'application/json')]})
                    await send({'type': 'http.response.body', 'body': b'{"detail":"Request body exceeds 6 MB"}'})
                    return
                chunks.append(message.get('body', b''))
                if not message.get('more_body', False):
                    break
            consumed = False

            async def replay():
                nonlocal consumed
                if not consumed:
                    consumed = True
                    return {'type': 'http.request', 'body': b''.join(chunks), 'more_body': False}
                return await receive()
            await self.app(scope, replay, send)

    app.add_middleware(BodyLimit)

    @app.middleware('http')
    async def headers(request, call_next):
        request_id = secrets.token_hex(8)
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            log.exception('request_failed id=%s path=%s', request_id, request.url.path)
            from fastapi.responses import JSONResponse
            response = JSONResponse({'detail': 'Internal error', 'request_id': request_id}, status_code=500)
        response.headers.update({'X-Request-ID': request_id, 'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY', 'Referrer-Policy': 'same-origin', 'Cache-Control': 'no-store', 'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"})
        if request.url.path in {'/docs', '/redoc'}:
            # FastAPI's standard documentation UI uses pinned CDN assets and an inline bootstrap.
            # The merchant workspace retains the stricter self-only policy above.
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; img-src 'self' data: https://fastapi.tiangolo.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        if settings.secure_cookies:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        log.info('request id=%s method=%s path=%s status=%s duration_ms=%d', request_id, request.method, request.url.path, response.status_code, (time.monotonic() - started) * 1000)
        return response

    def db_session():
        with sessions() as db:
            yield db

    def origin_check(request):
        if request.headers.get('origin') and request.headers['origin'] != settings.origin:
            raise HTTPException(403, 'Untrusted origin')

    def principal(request: Request, db=Depends(db_session)):
        token = request.cookies.get('pg_session', '')
        login = db.get(LoginSession, digest(token)) if token else None
        if not login or login.expires < int(time.time()):
            raise HTTPException(401, 'Sign in required')
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin_check(request)
            if not hmac.compare_digest(request.headers.get('x-csrf-token', ''), login.csrf):
                raise HTTPException(403, 'Invalid CSRF token')
        return db.get(User, login.user_id), login

    def rate_limit(db, key, maximum, window=60):
        now = int(time.time())
        db.execute(delete(RateBucket).where(RateBucket.expires < now))
        bucket_key = digest(key + ':' + str(now // window))
        try:
            db.add(RateBucket(key=bucket_key, expires=now + window))
            db.commit()
            count = 1
        except IntegrityError:
            db.rollback()
            count = db.execute(update(RateBucket).where(RateBucket.key == bucket_key).values(count=RateBucket.count + 1).returning(RateBucket.count)).scalar_one()
            db.commit()
        if count > maximum:
            raise HTTPException(429, 'Too many requests; try again later', headers={'Retry-After': str(window)})

    def login_response(db, user, response):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        db.execute(delete(LoginSession).where(LoginSession.expires < int(time.time())))
        db.add(LoginSession(token_hash=digest(token), user_id=user.id, csrf=csrf, expires=int(time.time()) + 28800))
        db.commit()
        response.set_cookie('pg_session', token, httponly=True, secure=settings.secure_cookies, samesite='strict', max_age=28800, path='/')
        return {'email': user.email, 'tenant_id': user.tenant_id, 'csrf': csrf, 'demo': settings.demo}

    @app.get('/health/live')
    def live():
        return {'status': 'ok'}

    @app.get('/health/ready')
    def ready(db=Depends(db_session)):
        db.execute(select(Tenant.id).limit(1))
        return {'status': 'ready'}

    @app.get('/api/v1/config')
    def config():
        return {'demo': settings.demo, 'paypal_environment': settings.paypal_environment}

    @app.post('/api/v1/auth/register', status_code=201)
    def register(body: Registration, request: Request, response: Response, db=Depends(db_session)):
        origin_check(request)
        rate_limit(db, 'auth:' + request.client.host, 10, 600)
        tenant = Tenant(name=body.company)
        db.add(tenant)
        db.flush()
        user = User(tenant_id=tenant.id, email=body.email, password_hash=hash_password(body.password))
        db.add(user)
        try:
            db.flush()
            audit(db, tenant.id, user.email, 'ACCOUNT_CREATED', user.id)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'Unable to create account with these details')
        return login_response(db, user, response)

    @app.post('/api/v1/auth/login')
    def login(body: Credentials, request: Request, response: Response, db=Depends(db_session)):
        origin_check(request)
        rate_limit(db, 'auth:' + request.client.host, 10, 600)
        user = db.scalar(select(User).where(User.email == body.email))
        # Constant-work verification for unknown users avoids trivial timing enumeration.
        stored = user.password_hash if user else '0' * 32 + ':' + '0' * 128
        valid = verify_password(body.password, stored)
        if not user or not valid:
            raise HTTPException(401, 'Invalid email or password')
        return login_response(db, user, response)

    @app.post('/api/v1/auth/demo')
    def demo(request: Request, response: Response, db=Depends(db_session)):
        if not settings.demo:
            raise HTTPException(404, 'Not found')
        origin_check(request)
        rate_limit(db, 'demo:' + request.client.host, 10, 600)
        tenant = Tenant(name='Northstar Studio · Demo')
        db.add(tenant)
        db.flush()
        user = User(tenant_id=tenant.id, email=secrets.token_hex(12) + '@demo.invalid', password_hash=hash_password(secrets.token_urlsafe(32)))
        db.add(user)
        db.flush()
        demo_seed(db, tenant.id)
        return login_response(db, user, response)

    @app.get('/api/v1/auth/me')
    def me(who=Depends(principal)):
        user, session = who
        return {'email': user.email, 'tenant_id': user.tenant_id, 'csrf': session.csrf, 'demo': settings.demo}

    @app.post('/api/v1/auth/logout', status_code=204)
    def logout(response: Response, who=Depends(principal), db=Depends(db_session)):
        db.delete(who[1])
        db.commit()
        response.delete_cookie('pg_session', path='/')

    @app.get('/api/v1/disputes')
    def disputes(q: str = Query('', max_length=100), status: str = Query('', max_length=24), page: int = Query(1, ge=1, le=10000), limit: int = Query(25, ge=1, le=100), who=Depends(principal), db=Depends(db_session)):
        filters = [Dispute.tenant_id == who[0].tenant_id]
        if status:
            filters.append(Dispute.status == status)
        if q:
            escaped = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            filters.append(or_(Dispute.customer.ilike('%' + escaped + '%', escape='\\'), Dispute.paypal_id.ilike('%' + escaped + '%', escape='\\')))
        total = db.scalar(select(func.count()).select_from(Dispute).where(*filters))
        rows = db.scalars(select(Dispute).where(*filters).order_by(Dispute.due_at, Dispute.id).offset((page - 1) * limit).limit(limit))
        return {'items': [serialize(d) for d in rows], 'total': total, 'page': page, 'limit': limit}

    @app.get('/api/v1/overview')
    def overview(who=Depends(principal), db=Depends(db_session)):
        rows = db.execute(select(Dispute.currency, Dispute.status, func.count(), func.sum(Dispute.amount_cents)).where(Dispute.tenant_id == who[0].tenant_id).group_by(Dispute.currency, Dispute.status)).all()
        return {'groups': [{'currency': c, 'status': s, 'count': n, 'amount_cents': a} for c, s, n, a in rows]}

    @app.post('/api/v1/disputes', status_code=201)
    def create_dispute(body: NewDispute, who=Depends(principal), db=Depends(db_session)):
        item = Dispute(tenant_id=who[0].tenant_id, **body.model_dump())
        db.add(item)
        try:
            db.flush()
            audit(db, who[0].tenant_id, who[0].email, 'DISPUTE_CREATED', item.id)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'Dispute already exists')
        return serialize(item)

    @app.get('/api/v1/disputes/{identity}')
    def detail(identity: str, who=Depends(principal), db=Depends(db_session)):
        item = get_dispute(db, who[0].tenant_id, identity)
        return {**serialize(item), 'evidence': [serialize(e) for e in evidence_for(db, who[0].tenant_id, identity)]}

    @app.post('/api/v1/disputes/{identity}/evidence', status_code=201)
    def evidence(identity: str, body: NewEvidence, who=Depends(principal), db=Depends(db_session)):
        item = get_dispute(db, who[0].tenant_id, identity)
        return serialize(add_evidence(db, who[0].tenant_id, who[0].email, item, body.title, body.kind, body.content, body.version))

    @app.post('/api/v1/disputes/{identity}/upload', status_code=201)
    def upload(identity: str, version: int = Form(..., gt=0), file: UploadFile = File(...), who=Depends(principal), db=Depends(db_session)):
        item = get_dispute(db, who[0].tenant_id, identity)
        editable(item)
        data = file.file.read(5 * 1024 * 1024 + 1)
        if len(data) > 5 * 1024 * 1024:
            raise HTTPException(413, 'PDF exceeds 5 MB')
        if not data.startswith(b'%PDF-'):
            raise HTTPException(422, 'Only PDF documents are accepted')
        try:
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted or len(reader.pages) > 20:
                raise ValueError('Encrypted or too many pages')
            text = '\n'.join(p.extract_text() or '' for p in reader.pages)
            if len(text.strip()) < 5:
                raise ValueError('Image-only PDFs require OCR, which is not enabled')
            if len(text) > 8000:
                raise ValueError('Extracted text exceeds 8000 characters')
        except Exception as exc:
            raise HTTPException(422, 'PDF could not be extracted. Use a text PDF of at most 20 pages / 8000 characters, or paste evidence manually.') from exc
        return serialize(add_evidence(db, who[0].tenant_id, who[0].email, item, (Path(file.filename or 'Document.pdf').name)[:160], 'OTHER', text, version))

    @app.post('/api/v1/disputes/{identity}/draft')
    def draft(identity: str, body: Version, who=Depends(principal), db=Depends(db_session)):
        item = get_dispute(db, who[0].tenant_id, identity)
        editable(item)
        if item.version != body.version:
            raise HTTPException(409, 'Refresh this dispute before drafting')
        records = evidence_for(db, who[0].tenant_id, identity)
        if not records:
            raise HTTPException(422, 'Add evidence before generating a draft')
        rate_limit(db, 'draft:' + who[0].tenant_id, 10, 60)
        try:
            text, source = app.state.drafter(settings, item, records)
        except ProviderError as exc:
            raise HTTPException(502, str(exc))
        transition(db, item, body.version, draft=text, draft_source=source, status='REVIEW')
        audit(db, who[0].tenant_id, who[0].email, 'DRAFT_GENERATED_' + source, identity)
        db.commit()
        db.refresh(item)
        return serialize(item)

    @app.put('/api/v1/disputes/{identity}/draft')
    def edit(identity: str, body: DraftEdit, who=Depends(principal), db=Depends(db_session)):
        item = get_dispute(db, who[0].tenant_id, identity)
        editable(item)
        if not evidence_for(db, who[0].tenant_id, identity):
            raise HTTPException(422, 'Add evidence before writing a defense')
        transition(db, item, body.version, draft=body.text, draft_source='MERCHANT', status='REVIEW')
        audit(db, who[0].tenant_id, who[0].email, 'DRAFT_EDITED', identity)
        db.commit()
        db.refresh(item)
        return serialize(item)

    @app.post('/api/v1/disputes/{identity}/approve')
    def approve(identity: str, body: Approval, who=Depends(principal), db=Depends(db_session)):
        item = get_dispute(db, who[0].tenant_id, identity)
        if item.status != 'REVIEW' or not item.draft:
            raise HTTPException(409, 'A draft must be reviewed first')
        transition(db, item, body.version, status='APPROVED')
        audit(db, who[0].tenant_id, who[0].email, 'DRAFT_APPROVED', identity)
        db.commit()
        db.refresh(item)
        return serialize(item)

    @app.post('/api/v1/disputes/{identity}/submit')
    def submit(identity: str, body: SubmissionInput, idempotency_key: str = Header(..., min_length=8, max_length=128), who=Depends(principal), db=Depends(db_session)):
        tenant = who[0].tenant_id
        item = get_dispute(db, tenant, identity)
        existing = db.scalar(select(Submission).where(Submission.tenant_id == tenant, Submission.request_key == idempotency_key))
        if existing:
            if existing.dispute_id != identity or existing.draft_version != body.version:
                raise HTTPException(409, 'Idempotency key already belongs to a different request')
            return serialize(existing)
        if item.status != 'APPROVED' or not item.draft:
            raise HTTPException(409, 'Approve the current draft before submission')
        if item.due_at < int(time.time()):
            raise HTTPException(409, 'Response deadline has passed; check PayPal before proceeding')
        if not settings.demo and tenant != settings.paypal_tenant_id:
            raise HTTPException(409, 'This workspace has no connected PayPal account')
        records = evidence_for(db, tenant, identity)
        transition(db, item, body.version, status='SUBMITTING')
        submission = Submission(tenant_id=tenant, dispute_id=identity, request_key=idempotency_key, draft_version=body.version)
        db.add(submission)
        audit(db, tenant, who[0].email, 'SUBMISSION_STARTED', identity)
        try:
            db.commit()  # Durable intent BEFORE contacting PayPal. Never auto-retry an ambiguous write.
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'A submission is already in progress')
        try:
            if settings.demo:
                reference = 'SIMULATED-' + submission.id
            else:
                app.state.paypal.submit(item.paypal_id, item.draft, records)
                reference = 'PAYPAL-' + item.paypal_id
            submission.state, submission.provider_reference = ('SIMULATED' if settings.demo else 'SENT'), reference
            final_status = 'SUBMITTED'
        except ProviderError:
            submission.state = 'UNKNOWN'
            final_status = 'SUBMISSION_UNKNOWN'
        db.execute(update(Dispute).where(Dispute.id == identity, Dispute.tenant_id == tenant, Dispute.status == 'SUBMITTING').values(status=final_status, version=Dispute.version + 1))
        audit(db, tenant, who[0].email, 'SUBMISSION_' + submission.state, identity)
        db.commit()
        return serialize(submission)

    @app.get('/api/v1/submissions')
    def submissions(who=Depends(principal), db=Depends(db_session)):
        return {'items': [serialize(s) for s in db.scalars(select(Submission).where(Submission.tenant_id == who[0].tenant_id).limit(100))]}

    @app.get('/api/v1/audit')
    def audits(page: int = Query(1, ge=1, le=10000), who=Depends(principal), db=Depends(db_session)):
        rows = db.scalars(select(Audit).where(Audit.tenant_id == who[0].tenant_id).order_by(Audit.created_at.desc(), Audit.id).offset((page - 1) * 50).limit(50))
        return {'items': [serialize(x) for x in rows]}

    @app.get('/api/v1/integrations')
    def integrations(who=Depends(principal)):
        return {'mode': 'demo' if settings.demo else 'live', 'paypal_environment': settings.paypal_environment, 'paypal_configured': bool(settings.paypal_client_id and settings.paypal_secret and who[0].tenant_id == settings.paypal_tenant_id), 'webhook_configured': bool(settings.paypal_webhook_id), 'ai_configured': bool(settings.openai_key and settings.openai_model), 'carrier_verification': False, 'ocr': False}

    @app.post('/api/v1/webhooks/paypal', status_code=202)
    def webhook(body: dict, request: Request, db=Depends(db_session)):
        # Demo never accepts unsigned external webhooks.
        if not settings.paypal_tenant_id:
            raise HTTPException(503, 'Configure a merchant workspace before enabling webhooks')
        try:
            verified = app.state.paypal.verify(request.headers, body)
        except ProviderError:
            raise HTTPException(503, 'Webhook verification unavailable; retry later')
        if not verified:
            raise HTTPException(401, 'Invalid webhook signature')
        if body.get('event_type') not in {'CUSTOMER.DISPUTE.CREATED', 'CUSTOMER.DISPUTE.UPDATED', 'CUSTOMER.DISPUTE.RESOLVED'}:
            return {'status': 'ignored'}
        if not isinstance(body.get('id'), str) or not 1 <= len(body['id']) <= 255 or not isinstance(body.get('resource'), dict) or not isinstance(body['resource'].get('dispute_id'), str):
            raise HTTPException(422, 'Malformed dispute event')
        record = Webhook(tenant_id=settings.paypal_tenant_id, event_id=body['id'], payload=json.dumps(body))
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            if not db.scalar(select(Webhook.id).where(Webhook.tenant_id == settings.paypal_tenant_id, Webhook.event_id == body['id'])):
                raise HTTPException(503, 'Merchant workspace is unavailable')
            return {'status': 'duplicate'}
        return {'status': 'accepted'}

    @app.get('/')
    def index():
        return FileResponse(STATIC / 'index.html')

    app.mount('/static', StaticFiles(directory=STATIC), name='static')
    return app


app = create_app()
