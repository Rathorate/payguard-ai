import hmac
import io
import json
import logging
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile, File, Form, Query, Header
from sqlalchemy import select, update, delete, func, or_
from sqlalchemy.exc import IntegrityError
from pypdf import PdfReader

from .config import Settings
from .models import Base, Tenant, User, LoginSession, Dispute, Evidence, Audit, Webhook, Submission, RateBucket, DraftRevision, EvidenceAnalysis, database
from .security import digest, hash_password, verify_password
from .providers import PayPal, ProviderError, ProviderHTTPError, generate_draft
from .schemas import Credentials, Registration, NewDispute, NewEvidence, Version, DraftEdit, Approval, SubmissionInput, PayPalImport, CaseQuestion, AnalysisRequest
from .paypal_import import snapshot as paypal_snapshot
from .review import analyze_evidence, citation_report, validate_analysis
from .questions import answer_question, validate_answer
from .service import audit, get_dispute, evidence_for, transition, editable, add_evidence, serialize, demo_seed

log = logging.getLogger('payguard')
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
    app.state.reviewer = analyze_evidence
    app.state.answerer = answer_question

    def ai_failure(task, exc):
        diagnostic=getattr(exc,'diagnostic',{})
        # Log protocol metadata only, never evidence, questions, generated text or keys.
        log.warning('AI failure task=%s provider=%s status=%s code=%s',task,settings.drafting_provider,
                    diagnostic.get('status','unknown'),diagnostic.get('code','unknown'))
        headers={}
        status=502
        if isinstance(exc,ProviderHTTPError) and diagnostic.get('status')==429:
            status=503
            seconds=diagnostic.get('retry_after_seconds')
            if isinstance(seconds,int) and 0<=seconds<=86400:
                headers['Retry-After']=str(seconds)
        elif isinstance(exc,ProviderHTTPError) and diagnostic.get('status') in {500,502,503,504}:
            status=503
        return HTTPException(status,str(exc),headers=headers)

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
        return {'email': user.email, 'tenant_id': user.tenant_id, 'csrf': csrf, 'demo': settings.demo, 'sample_workspace': user.email.endswith('@demo.invalid')}

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
        return {'email': user.email, 'tenant_id': user.tenant_id, 'csrf': session.csrf, 'demo': settings.demo, 'sample_workspace': user.email.endswith('@demo.invalid')}

    @app.post('/api/v1/demo/seed')
    def seed_empty_workspace(who=Depends(principal), db=Depends(db_session)):
        if not settings.demo:
            raise HTTPException(404, 'Not found')
        tenant = who[0].tenant_id
        db.scalar(select(Tenant).where(Tenant.id == tenant).with_for_update())
        if db.scalar(select(func.count()).select_from(Dispute).where(Dispute.tenant_id == tenant)):
            raise HTTPException(409, 'This workspace already has cases. Existing records were preserved.')
        try:
            demo_seed(db, tenant)
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'Sample cases were already loaded. Refresh the inbox.')
        return {'status': 'seeded', 'count': 4}

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

    @app.get('/api/v1/disputes/{identity}/review')
    def review_details(identity: str, who=Depends(principal), db=Depends(db_session)):
        item = get_dispute(db, who[0].tenant_id, identity)
        tenant = who[0].tenant_id
        records = evidence_for(db, tenant, identity)
        analysis = db.scalar(select(EvidenceAnalysis).where(EvidenceAnalysis.tenant_id==tenant, EvidenceAnalysis.dispute_id==identity, EvidenceAnalysis.case_version==item.version))
        history = list(db.scalars(select(DraftRevision).where(DraftRevision.tenant_id==tenant, DraftRevision.dispute_id==identity, DraftRevision.case_version<=item.version).order_by(DraftRevision.case_version.desc()).limit(20)))
        baseline = db.scalar(select(DraftRevision).where(DraftRevision.tenant_id==tenant, DraftRevision.dispute_id==identity, DraftRevision.case_version<=item.version, DraftRevision.action=='GENERATED').order_by(DraftRevision.case_version.desc()).limit(1))
        return {'case_version': item.version, 'citations': citation_report(item.draft, records),
                'analysis': {**serialize(analysis), 'report': json.loads(analysis.report)} if analysis else None,
                'history': [serialize(r) for r in history], 'latest_generated': serialize(baseline) if baseline else None}

    @app.post('/api/v1/disputes/{identity}/analyze')
    def analyze(identity: str, body: AnalysisRequest, who=Depends(principal), db=Depends(db_session)):
        item = get_dispute(db, who[0].tenant_id, identity)
        editable(item)
        if item.version != body.version:
            raise HTTPException(409, 'This case changed. Refresh before analyzing evidence.')
        records = evidence_for(db, who[0].tenant_id, identity)
        if not records:
            raise HTTPException(422, 'Add evidence before analyzing it')
        existing = db.scalar(select(EvidenceAnalysis).where(EvidenceAnalysis.tenant_id==who[0].tenant_id, EvidenceAnalysis.dispute_id==identity, EvidenceAnalysis.case_version==body.version))
        if existing and not body.refresh:
            return {**serialize(existing), 'report': json.loads(existing.report)}
        rate_limit(db, 'analyze:'+who[0].tenant_id, 5, 60)
        try:
            report, source = app.state.reviewer(settings, item, records)
            report = validate_analysis(json.dumps(report), records)
        except ProviderError as exc:
            raise ai_failure('analysis',exc)
        # Conditional write serializes with edits; stale results cannot describe a newer case.
        result = db.execute(update(Dispute).where(Dispute.id==identity, Dispute.tenant_id==who[0].tenant_id, Dispute.version==body.version).values(version=body.version))
        if result.rowcount != 1:
            raise HTTPException(409, 'The case changed during analysis. Refresh; nothing was approved.')
        if existing:
            record=existing
            record.source=source;record.report=json.dumps(report);record.created_at=int(time.time())
        else:
            record = EvidenceAnalysis(tenant_id=who[0].tenant_id, dispute_id=identity, case_version=body.version, source=source, report=json.dumps(report))
            db.add(record)
        audit(db, who[0].tenant_id, who[0].email, 'EVIDENCE_ANALYZED_'+source, identity)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'Another review was saved. Refresh this case.')
        return {**serialize(record), 'report': report}

    @app.post('/api/v1/disputes/{identity}/questions')
    def case_question(identity: str, body: CaseQuestion, who=Depends(principal), db=Depends(db_session)):
        tenant=who[0].tenant_id
        item=get_dispute(db,tenant,identity)
        if item.version!=body.version:
            raise HTTPException(409,'This case changed. Refresh before asking a question.')
        records=evidence_for(db,tenant,identity)
        if not records:
            raise HTTPException(422,'Add evidence before asking a case question')
        rate_limit(db,'questions:'+tenant,5,60)
        try:
            report,source=app.state.answerer(settings,item,records,body.question,[turn.model_dump() for turn in body.history],include_draft=body.include_draft)
            report=validate_answer(report,records)
        except ProviderError as exc:
            raise ai_failure('question',exc)
        result=db.execute(update(Dispute).where(Dispute.id==identity,Dispute.tenant_id==tenant,
            Dispute.version==body.version).values(version=body.version))
        if result.rowcount!=1:
            raise HTTPException(409,'The case changed while answering. Refresh; the answer was discarded.')
        audit(db,tenant,who[0].email,'CASE_QUESTION_ANSWERED_'+source,identity)
        db.commit()
        return {'case_version':body.version,'source':source,'report':report,
                'notice':'AI guidance only. Check the sources. The draft, approval and submission were not changed.'}

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
            raise ai_failure('draft',exc)
        transition(db, item, body.version, draft=text, draft_source=source, status='REVIEW')
        db.add(DraftRevision(tenant_id=who[0].tenant_id, dispute_id=identity, case_version=body.version+1, action='GENERATED', source=source, text=text, actor=who[0].email))
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
        db.add(DraftRevision(tenant_id=who[0].tenant_id, dispute_id=identity, case_version=body.version+1, action='EDITED', source='MERCHANT', text=body.text, actor=who[0].email))
        audit(db, who[0].tenant_id, who[0].email, 'DRAFT_EDITED', identity)
        db.commit()
        db.refresh(item)
        return serialize(item)

    @app.post('/api/v1/disputes/{identity}/approve')
    def approve(identity: str, body: Approval, who=Depends(principal), db=Depends(db_session)):
        item = get_dispute(db, who[0].tenant_id, identity)
        if item.status != 'REVIEW' or not item.draft:
            raise HTTPException(409, 'A draft must be reviewed first')
        if citation_report(item.draft, evidence_for(db, who[0].tenant_id, identity))['unknown_ids']:
            raise HTTPException(422, 'Correct unknown evidence references in the saved response before approval')
        transition(db, item, body.version, status='APPROVED')
        db.add(DraftRevision(tenant_id=who[0].tenant_id, dispute_id=identity, case_version=body.version+1, action='APPROVED', source=item.draft_source, text=item.draft, actor=who[0].email))
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
        if item.due_at <= int(time.time()):
            raise HTTPException(409, 'Response deadline has passed; check PayPal before proceeding')
        if not settings.demo and tenant != settings.paypal_tenant_id:
            raise HTTPException(409, 'This workspace has no connected PayPal account')
        records = evidence_for(db, tenant, identity)
        if citation_report(item.draft, records)['unknown_ids']:
            raise HTTPException(422, 'Correct unknown evidence references and approve the response again before submission')
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

    @app.post('/api/v1/disputes/{identity}/request-changes')
    def request_changes(identity: str, body: Version, who=Depends(principal), db=Depends(db_session)):
        item = get_dispute(db, who[0].tenant_id, identity)
        if item.status != 'APPROVED':
            raise HTTPException(409, 'Only an approved response can be returned for review')
        transition(db, item, body.version, status='REVIEW')
        db.add(DraftRevision(tenant_id=who[0].tenant_id, dispute_id=identity, case_version=body.version+1, action='WITHDRAWN', source=item.draft_source, text=item.draft, actor=who[0].email))
        audit(db, who[0].tenant_id, who[0].email, 'APPROVAL_WITHDRAWN', identity)
        db.commit()
        db.refresh(item)
        return serialize(item)

    @app.get('/api/v1/disputes/{identity}/export')
    def export_packet(identity: str, version: int = Query(..., gt=0), who=Depends(principal), db=Depends(db_session)):
        item = get_dispute(db, who[0].tenant_id, identity)
        if item.status != 'APPROVED' or item.version != version:
            raise HTTPException(409, 'Approve the current saved response before exporting')
        packet = {'format': 'payguard.reviewed-packet.v1', 'mode': 'demo' if settings.demo else 'live',
                  'notice': 'Prepared for human review/manual use. This export does not submit anything to PayPal.' + (' Demo seed cases and evidence are synthetic.' if settings.demo else ''),
                  'case': serialize(item), 'evidence': [serialize(e) for e in evidence_for(db, who[0].tenant_id, identity)]}
        packet['review'] = review_details(identity, who, db)
        current = db.execute(select(Dispute.version, Dispute.status).where(Dispute.id==identity, Dispute.tenant_id==who[0].tenant_id)).one()
        if current.version != version or current.status != 'APPROVED' or packet['review']['case_version'] != version:
            raise HTTPException(409, 'This case changed during export. Refresh and approve the latest response.')
        packet['sha256'] = digest(json.dumps(packet, sort_keys=True))
        return Response(json.dumps(packet, indent=2), media_type='application/json', headers={'Content-Disposition': f'attachment; filename="payguard-{item.paypal_id}-v{item.version}.json"'})

    @app.get('/api/v1/submissions')
    def submissions(who=Depends(principal), db=Depends(db_session)):
        return {'items': [serialize(s) for s in db.scalars(select(Submission).where(Submission.tenant_id == who[0].tenant_id).limit(100))]}

    @app.get('/api/v1/audit')
    def audits(page: int = Query(1, ge=1, le=10000), who=Depends(principal), db=Depends(db_session)):
        rows = db.scalars(select(Audit).where(Audit.tenant_id == who[0].tenant_id).order_by(Audit.created_at.desc(), Audit.id).offset((page - 1) * 50).limit(50))
        return {'items': [serialize(x) for x in rows]}

    @app.get('/api/v1/integrations')
    def integrations(who=Depends(principal)):
        return {'mode': 'demo' if settings.demo else 'live', 'paypal_environment': settings.paypal_environment, 'paypal_configured': bool(settings.paypal_client_id and settings.paypal_secret and who[0].tenant_id == settings.paypal_tenant_id), 'webhook_configured': bool(settings.paypal_webhook_id), **settings.ai_status(), 'carrier_verification': False, 'ocr': False}

    def sandbox_merchant(who):
        if settings.paypal_environment != 'sandbox':
            raise HTTPException(409, 'This hackathon connection/import flow is sandbox-only')
        if not settings.paypal_client_id or not settings.paypal_secret:
            raise HTTPException(409, 'Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in the backend environment and restart it')
        if who[0].tenant_id != settings.paypal_tenant_id:
            raise HTTPException(409, 'Set PAYPAL_TENANT_ID to your workspace ID shown in Integrations, then restart the backend')

    @app.post('/api/v1/integrations/paypal/check')
    def check_paypal(who=Depends(principal), db=Depends(db_session)):
        sandbox_merchant(who)
        rate_limit(db, 'paypal-check:' + who[0].tenant_id, 3, 60)
        try:
            result = app.state.paypal.check_sandbox_auth()
        except ProviderError as exc:
            raise HTTPException(502, str(exc))
        audit(db, who[0].tenant_id, who[0].email, 'PAYPAL_SANDBOX_AUTH_VERIFIED', 'sandbox-auth-check')
        db.commit()
        return result

    @app.post('/api/v1/paypal/disputes/import', status_code=201)
    def import_paypal(body: PayPalImport, who=Depends(principal), db=Depends(db_session)):
        sandbox_merchant(who)
        tenant = who[0].tenant_id
        if db.scalar(select(Dispute.id).where(Dispute.tenant_id==tenant, Dispute.paypal_id==body.paypal_id)):
            raise HTTPException(409, 'This case already exists. Import does not overwrite existing evidence or approvals.')
        rate_limit(db, 'paypal-import:' + tenant, 10, 60)
        try:
            fields, content = paypal_snapshot(app.state.paypal.details(body.paypal_id), body.paypal_id)
        except ProviderError as exc:
            status=404 if isinstance(exc,ProviderHTTPError) and exc.diagnostic.get('status')==404 else 502
            raise HTTPException(status, str(exc))
        item = Dispute(tenant_id=tenant, **fields)
        db.add(item)
        try:
            db.flush()
            db.add(Evidence(tenant_id=tenant,dispute_id=item.id,title='PayPal sandbox dispute snapshot',kind='OTHER',content=content,sha256=digest(content)))
            audit(db,tenant,who[0].email,'PAYPAL_SANDBOX_DISPUTE_IMPORTED',item.id)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'This case was already imported. Refresh the inbox.')
        return serialize(item)

    @app.post('/api/v1/integrations/ai/check')
    def check_ai(who=Depends(principal), db=Depends(db_session)):
        status = settings.ai_status()
        if not status['ai_configured']:
            raise HTTPException(409, status['ai_message'])
        rate_limit(db, 'ai-check:' + who[0].tenant_id, 3, 60)
        sample = SimpleNamespace(paypal_id='PP-D-CONNECTION-TEST', reason='INQUIRY', amount_cents=1000, currency='USD')
        evidence = [SimpleNamespace(id='SAMPLE-RECEIPT', title='Synthetic receipt', content='SYNTHETIC CONNECTION TEST. Merchant records payment of 10.00 USD. Delivery and authorization are unverified.')]
        try:
            text, source = app.state.drafter(settings, sample, evidence)
        except ProviderError as exc:
            raise ai_failure('connection-check',exc)
        audit(db, who[0].tenant_id, who[0].email, 'AI_CONNECTION_VERIFIED_' + source, 'synthetic-connection-test')
        db.commit()
        return {'status': 'ok', 'provider': source, 'model': status['ai_model'], 'sample_draft': text, 'notice': 'Synthetic text only. No case was changed, approved or submitted.'}

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
        return {'service': 'PayGuard API', 'docs': '/docs', 'health': '/health/ready'}

    return app


app = create_app()
