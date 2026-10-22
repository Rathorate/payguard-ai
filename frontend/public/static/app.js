import {renderReview, revealEvidence} from './review-ui.js';
import {questionPanel,renderConversation} from './questions-ui.js';
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const state = {csrf: '', user: null, demo: false, status: '', page: 1, q: '', detail: null, view: 'disputes', loadId: 0, ai: null};
const labels = {OPEN: 'Needs evidence', REVIEW: 'In review', APPROVED: 'Ready to send', SUBMITTED: 'Submitted', RESOLVED: 'Resolved', SUBMITTING: 'Sending', SUBMISSION_UNKNOWN: 'Needs reconciliation'};
const reasons = {MERCHANDISE_OR_SERVICE_NOT_RECEIVED: 'Item not received', MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED: 'Not as described', UNAUTHORIZED_TRANSACTION: 'Unauthorized transaction', UNAUTHORISED: 'Unauthorized transaction', NOT_RECOGNISED: 'Not recognized', NOT_RECOGNIZED: 'Not recognized', INQUIRY: 'Customer inquiry'};
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = (cents, currency = 'USD') => {try {return new Intl.NumberFormat('en-US', {style:'currency',currency}).format(cents / 100);} catch {return `${(cents / 100).toFixed(2)} ${currency}`;}};
const date = seconds => seconds ? new Date(seconds * 1000).toLocaleDateString(undefined, {month:'short',day:'numeric',year:'numeric'}) : 'Check PayPal';
const badge = status => `<span class="badge ${escape(status)}">${escape(labels[status] || status)}</span>`;
let toastTimer;
let casePending=false;
let caseRequest=0;
const caseLocks=new Map();
const caseConversations=new Map();
function lockCaseControls(){
  for(const control of $$('button,input,textarea,select',$('#case-dialog'))){
    if(!caseLocks.has(control))caseLocks.set(control,control.disabled);
    control.disabled=true;
  }
}
function unlockCaseControls(){
  for(const [control,disabled] of caseLocks)if(control.isConnected)control.disabled=disabled;
  caseLocks.clear();
}
function unsavedDraft(){return $('#case-dialog').open && state.detail && $('#draft-text')?.value!==state.detail.draft;}
function finishCloseCase(){caseRequest++;$('#case-dialog').close();state.detail=null;}
function closeCase(){
  if(casePending){toast('Please wait for the current case action to finish.');return;}
  if(unsavedDraft()){$('#discard-dialog').showModal();return;}
  finishCloseCase();
}
function toast(message) {const feedback=$('#case-feedback');if(feedback && $('#case-dialog').open){feedback.textContent=message;feedback.hidden=false;}$('#toast').textContent = message; $('#toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').hidden = true, 6500);}

async function api(path, options = {}) {
  const headers = {'X-CSRF-Token': state.csrf, ...options.headers};
  if (options.body && !(options.body instanceof FormData)) {headers['Content-Type'] = 'application/json'; options.body = JSON.stringify(options.body);}
  // Vercel (or the local frontend server) forwards this path to the separate API.
  let response;
  try {response = await fetch('/api/v1' + path, {...options, headers, credentials:'same-origin'});}
  catch {throw new Error('Connection lost. Keep both local servers running, then refresh this case before retrying.');}
  if (response.status === 204) return null;
  let data;
  try {data = await response.json();}
  catch {throw new Error(`The server returned an unexpected response (${response.status}). Check the backend connection.`);}
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith('/auth/')) {caseConversations.clear();state.user = null; $('#workspace').hidden = true; $('#login-view').hidden = false;}
    throw new Error(typeof data.detail === 'string' ? data.detail : data.detail?.map(e => `${e.loc.slice(1).join('.')}: ${e.msg}`).join('; ') || 'Request failed');
  }
  return data;
}

async function busy(button, task) {
  if (button.disabled) return;
  const inCase=!!button.closest('#case-dialog');
  if(inCase && casePending)return;
  if(inCase){casePending=true;lockCaseControls();}
  button.disabled = true;
  const text = button.textContent;
  button.textContent = 'Working…';
  try {await task();} catch(error) {toast(error.message);} finally {if(inCase){casePending=false;unlockCaseControls();}if (button.isConnected) {button.disabled = false; button.textContent = text;}}
}

async function enter(user) {
  caseConversations.clear();
  state.user = user; state.csrf = user.csrf; state.demo = user.demo;
  state.q='';state.status='';state.page=1;state.view='disputes';state.detail=null;state.ai=null;
  $('#search').value='';$$('.tab').forEach(x=>x.classList.toggle('active',x.dataset.status===''));
  $('#login-view').hidden = true; $('#workspace').hidden = false;
  $('#profile-label').textContent = user.sample_workspace ? 'Sample workspace' : user.email;
  $('#mode-badge').textContent = user.demo ? 'Demo · simulated submissions' : 'Merchant workspace';
  await loadView();
}

let registration = false;
$('#auth-toggle').addEventListener('click', () => {
  registration = !registration;
  $('#company-label').hidden = !registration;
  $('[name=company]').required = registration;
  $('#auth-title').textContent = registration ? 'Make room for clarity.' : 'Welcome back.';
  $('#auth-intro').textContent = registration ? 'Create your merchant workspace.' : 'Your next response starts here.';
  $('#auth-submit').textContent = registration ? 'Create workspace →' : 'Sign in →';
  $('[name=password]').autocomplete = registration ? 'new-password' : 'current-password';
  $('#auth-toggle').textContent = registration ? 'Already have a workspace? Sign in' : 'New here? Create a workspace';
});
$('#auth-form').addEventListener('submit', async event => {
  event.preventDefault(); $('#auth-error').textContent = '';
  const form = Object.fromEntries(new FormData(event.target));
  if (!registration) delete form.company;
  await busy($('#auth-submit'), async () => {
    try {await enter(await api(registration ? '/auth/register' : '/auth/login', {method:'POST',body:form})); event.target.reset();}
    catch(error) {$('#auth-error').textContent = error.message;}
  });
});
$('#demo-login').addEventListener('click', event => busy(event.currentTarget, async () => enter(await api('/auth/demo', {method:'POST'}))));
$('#logout').addEventListener('click', event => busy(event.currentTarget, async () => {await api('/auth/logout', {method:'POST'}); caseConversations.clear();state.user = null; state.csrf = ''; $('#workspace').hidden = true; $('#login-view').hidden = false;}));

async function loadView() {
  const views = ['disputes', 'audit', 'integrations'];
  for (const view of views) $(`#${view}-view`).hidden = view !== state.view;
  $$('.nav').forEach(button => button.classList.toggle('active', button.dataset.view === state.view));
  const title = {disputes:'Dispute inbox',audit:'Activity log',integrations:'Integrations'}[state.view];
  $('#page-title').textContent = title + '.'; $('#breadcrumb').textContent = title;
  $('#page-subtitle').textContent = {disputes:'A clear path from open case to a considered response.',audit:'A record of every meaningful step in your workspace.',integrations:'The services behind a more connected workflow.'}[state.view];
  $('#new-case').hidden = state.view !== 'disputes';
  if (state.view === 'disputes') return loadCases();
  if (state.view === 'audit') {
    const data = await api('/audit');
    $('#audit-list').innerHTML = data.items.length ? data.items.map(x => `<div class="audit-row"><div>${escape(x.action.replaceAll('_',' ').toLowerCase())}<small>${escape(x.actor)} · ${escape(x.resource_id)}</small></div><time>${escape(new Date(x.created_at*1000).toLocaleString())}</time></div>`).join('') : '<div class="empty">Your workspace activity will appear here.</div>';
  } else {
    const data = await api('/integrations');
    $('#paypal-workspace').textContent=state.user.tenant_id;
    const cards = [
      ['PayPal',data.paypal_configured,`Dispute ingestion and merchant evidence submission. Environment: ${data.paypal_environment}. ${state.demo ? 'Submission is simulated in demo mode.' : ''}`],
      ['AI drafting',data.ai_configured,`Selected provider: ${data.ai_provider}. ${data.ai_message || ''} ${data.ai_model ? 'Model: '+data.ai_model : ''}`],
      ['Carrier verification',false,'Tracking statements can be recorded manually. No independent carrier verification is connected.'],
      ['Document extraction',true,'Text PDFs are supported. Scanned documents and images require a separate OCR service.']
    ];
    $('#integration-cards').innerHTML = cards.map(([name,configured,description]) => `<div class="integration-card"><span class="badge ${configured?'APPROVED':''}">${configured?'Configured':'Not connected'}</span><h2>${escape(name)}</h2><p>${escape(description)}</p></div>`).join('');
  }
}

async function loadCases() {
  const loadId = ++state.loadId;
  const [data, overview, integration] = await Promise.all([api('/disputes?' + new URLSearchParams({q:state.q,status:state.status,page:state.page,limit:10})),api('/overview'),api('/integrations')]);
  if (loadId !== state.loadId) return;
  state.ai=integration;
  $('#ai-provider-label').textContent=integration.ai_configured ? `${integration.ai_provider.toUpperCase()} · ${integration.ai_model}` : 'AI is not enabled · offline templates available';
  $('#ai-status').textContent=integration.ai_message || 'Restart your backend after changing its AI environment settings.';
  const groups = overview.groups;
  const count = groups.reduce((sum,g)=>sum+g.count,0);
  $('#seed-cases').hidden=!state.demo || count>0;
  const openGroups = groups.filter(g=>!['SUBMITTED','RESOLVED'].includes(g.status));
  const atRisk = Object.entries(openGroups.reduce((totals,g)=>({...totals,[g.currency]:(totals[g.currency]||0)+g.amount_cents}),{})).map(([c,a])=>money(a,c));
  const stats = [
    ['Active disputes', openGroups.reduce((n,g)=>n+g.count,0), 'Cases awaiting your next step', '◇'],
    ['Amount at stake', atRisk.join(' + ') || money(0), atRisk.length>1 ? 'Amounts shown separately by currency' : 'Across active disputes', '↗'],
    ['Ready to send', groups.filter(g=>g.status==='APPROVED').reduce((n,g)=>n+g.count,0), 'Reviewed and approved by you', '✓'],
    ['Responses submitted', groups.filter(g=>g.status==='SUBMITTED').reduce((n,g)=>n+g.count,0), state.demo ? 'Simulated in this demo' : 'Sent for provider review', '↗']
  ];
  $('#stats').innerHTML = stats.map(([label,value,foot,icon],i)=>`<div class="stat ${i===1?'highlight':''}"><span class="stat-label">${label}<span class="stat-icon">${icon}</span></span><b class="stat-value">${escape(value)}</b><span class="stat-foot">${foot}</span></div>`).join('');
  $('#nav-count').textContent = count; $('#result-count').textContent = data.total;
  $('#case-rows').innerHTML = data.items.map(d => {
    const days = Math.ceil((d.due_at*1000-Date.now())/86400000);
    const initials = d.customer.split(' ').map(x=>x[0]).slice(0,2).join('');
    return `<tr><td><div class="customer-cell"><span class="customer-avatar">${escape(initials)}</span><div><span class="case-name">${escape(d.customer)}</span><span class="case-id">${escape(d.paypal_id)}</span></div></div></td><td><span class="reason-label">${escape(reasons[d.reason]||d.reason)}</span></td><td><span class="money">${escape(money(d.amount_cents,d.currency))}</span></td><td><span class="deadline ${days<=2?'urgent':''}">${escape(date(d.due_at))}<small>${d.due_at ? (days<0?'Deadline passed':days===0?'Due today':`${days} day${days===1?'':'s'} remaining`) : 'Deadline unavailable'}</small></span></td><td>${badge(d.status)}</td><td><button class="row-open" data-id="${escape(d.id)}" aria-label="Open case for ${escape(d.customer)}">↗</button></td></tr>`;
  }).join('');
  $('#empty-state').hidden = data.items.length > 0;
  $('#pagination-label').textContent = data.total ? `Showing ${(state.page-1)*10+1}–${Math.min(state.page*10,data.total)} of ${data.total} cases` : '0 cases';
  $('#prev-page').disabled = state.page <= 1; $('#next-page').disabled = state.page*10 >= data.total;
}

$('#check-paypal').addEventListener('click',event=>busy(event.currentTarget,async()=>{
  $('#paypal-feedback').textContent='Checking PayPal sandbox authentication…';
  try{const result=await api('/integrations/paypal/check',{method:'POST'});$('#paypal-feedback').textContent=`${result.notice} App fingerprint: ${result.client_id_fingerprint}. Seller dispute-read scope: ${result.dispute_read_scope_present===true?'present':result.dispute_read_scope_present===false?'missing':'not reported'}.`;}
  catch(error){$('#paypal-feedback').textContent=error.message;throw error;}
}));
$('#paypal-import-form').addEventListener('submit',event=>{
  event.preventDefault();const body=Object.fromEntries(new FormData(event.target));
  body.paypal_id=String(body.paypal_id||'').trim();
  if(!/^PP-[DR]-[A-Za-z0-9-]+$/.test(body.paypal_id)){
    $('#paypal-import-feedback').textContent='Enter the PayPal dispute ID (for example PP-R-SLL-10194090), not the app fingerprint or Client ID.';
    return;
  }
  $('#paypal-import-feedback').textContent='Importing the PayPal sandbox dispute…';
  busy($('button',event.target),async()=>{
    try{
      const item=await api('/paypal/disputes/import',{method:'POST',body});
      $('#paypal-import-feedback').textContent='Sandbox case imported. No evidence was submitted.';
      state.view='disputes';state.page=1;state.q='';state.status='';$('#search').value='';$$('.tab').forEach(x=>x.classList.toggle('active',x.dataset.status===''));
      await loadView();await openCase(item.id);toast('PayPal sandbox case imported. Check the evidence and deadline before drafting. Nothing was submitted.');
    }catch(error){$('#paypal-import-feedback').textContent=error.message;throw error;}
  });
});
$('#seed-cases').addEventListener('click',event=>busy(event.currentTarget,async()=>{await api('/demo/seed',{method:'POST'});state.q='';state.status='';state.page=1;$('#search').value='';$$('.tab').forEach(x=>x.classList.toggle('active',x.dataset.status===''));await loadCases();toast('Four synthetic cases loaded. Open a case to try AI drafting and human review.');}));
$('#check-ai').addEventListener('click',event=>busy(event.currentTarget,async()=>{
  $('#ai-feedback').textContent='Testing with synthetic text. This can take up to 45 seconds…';
  try {const result=await api('/integrations/ai/check',{method:'POST'});$('#ai-feedback').textContent=`${result.provider} connection verified (${result.model}). ${result.notice}\n\n${result.sample_draft}`;}
  catch(error){$('#ai-feedback').textContent=error.message;throw error;}
}));

$$('.nav').forEach(button => button.addEventListener('click', () => {state.view = button.dataset.view; loadView().catch(e=>toast(e.message));}));
$('#refresh').addEventListener('click', event => busy(event.currentTarget, loadView));
$$('.tab').forEach(button => button.addEventListener('click', () => {state.status = button.dataset.status; state.page=1; $$('.tab').forEach(x=>x.classList.toggle('active',x===button)); loadCases().catch(e=>toast(e.message));}));
let searchTimer;
$('#search').addEventListener('input', event => {clearTimeout(searchTimer);state.q=event.target.value;state.page=1;searchTimer=setTimeout(()=>loadCases().catch(e=>toast(e.message)),250);});
$('#prev-page').addEventListener('click', ()=>{state.page--;loadCases().catch(e=>toast(e.message));});
$('#next-page').addEventListener('click', ()=>{state.page++;loadCases().catch(e=>toast(e.message));});
$('#case-rows').addEventListener('click', event => {const button=event.target.closest('[data-id]');if(button)openCase(button.dataset.id).catch(e=>toast(e.message));});

async function openCase(id) {
  const requestId=++caseRequest;
  const [d, review] = await Promise.all([api(`/disputes/${id}`),api(`/disputes/${id}/review`)]);
  if(requestId!==caseRequest)return;
  if(d.version!==review.case_version)throw new Error('The case changed while loading. Open it again to review the latest version.');
  state.detail=d;
  $('#detail-title').textContent = d.paypal_id;
  const locked = ['SUBMITTED','RESOLVED','SUBMITTING','SUBMISSION_UNKNOWN'].includes(d.status);
  $('#detail-content').innerHTML = `<div class="detail-body"><p id="case-feedback" class="notice" role="status" hidden></p>${badge(d.status)}<div class="detail-meta"><div><span>Customer</span><b>${escape(d.customer)}</b></div><div><span>Disputed amount</span><b>${escape(money(d.amount_cents,d.currency))}</b></div><div><span>Response deadline</span><b>${escape(date(d.due_at))}</b></div></div><p class="small muted">${escape(reasons[d.reason]||d.reason)}</p>
    <section class="section-box"><div class="section-top"><h3><span class="step">1</span> Evidence collection</h3><span class="count">${d.evidence.length} items</span></div><p class="muted">Recorded merchant statements. Delivery and eligibility have not been independently verified.</p>${d.evidence.map(e=>`<details class="evidence-item"><summary>${escape(e.title)} <span class="badge">${escape(e.kind)}</span></summary><p>${escape(e.content)}</p><small>Evidence ID: ${escape(e.id)}</small></details>`).join('') || '<p class="muted">No evidence yet. Add your first record below.</p>'}
    ${!locked?`<details class="evidence-item"><summary>+ Add a record</summary><form id="evidence-form"><label>Title<input name="title" required minlength="2" maxlength="160" placeholder="Order invoice or delivery statement"></label><label>Type<select name="kind"><option>INVOICE</option><option>TRACKING</option><option>COMMUNICATION</option><option>OTHER</option></select></label><label>Facts / source text<textarea name="content" required minlength="5" maxlength="8000" placeholder="Paste the relevant facts and source details. Do not include unnecessary personal information."></textarea></label><button class="secondary">Save evidence</button></form></details><form id="upload-form"><label class="upload-label">Or extract text from a PDF<input name="file" type="file" accept="application/pdf" required><small>Up to 5 MB / 20 pages. Image-only documents need OCR.</small></label><button class="secondary compact">Extract & add</button></form>`:''}</section>
    <section class="section-box"><div class="section-top"><h3><span class="step">2</span> Response draft</h3>${!locked?`<button class="secondary compact" id="generate-draft">${state.ai?.ai_configured?'✦ Generate AI draft':'Generate template draft'}</button>`:''}</div><p class="muted">${['OPENAI','GROQ'].includes(d.draft_source)?`${escape(d.draft_source)} draft. Verify every assertion and evidence reference.`:d.draft_source==='MERCHANT'?'Edited by merchant. Review before approval.':'Template drafting works without an API key. AI drafting is optional.'}</p><label for="draft-text" class="sr-only">Defense draft</label><textarea id="draft-text" rows="10" maxlength="12000" placeholder="Add evidence, then generate or write your response." ${locked?'readonly':''}>${escape(d.draft)}</textarea><p class="small muted" id="draft-save-status" role="status">${locked?'Response locked after submission.':'You are reviewing the saved response shown above.'}</p>${!locked?'<div class="actions"><button class="secondary" id="save-draft">Save edits</button></div>':''}</section>
    <section class="section-box"><h3><span class="step">3</span> Review & respond</h3><p class="muted">Approval applies to the current version. Changing evidence or the draft requires a new review.</p>${d.status==='REVIEW'?'<label class="check-label"><input type="checkbox" id="review-check">I checked the facts, evidence references, and response deadline.</label><button class="primary" id="approve-draft">Approve response →</button>':''}${d.status==='APPROVED'?`<label class="check-label"><input type="checkbox" id="submit-check">${state.demo?'I understand this simulates submission.':'I confirm this response should be sent to PayPal.'}</label><button class="primary" id="submit-case">${state.demo?'Simulate submission':'Send response to PayPal'} →</button>`:''}${d.status==='OPEN'?'<p class="notice">Add evidence and save a draft to start your review.</p>':''}${d.status==='SUBMITTED'?`<p class="notice">${state.demo?'Demo submission complete. Nothing was sent to PayPal.':'Response sent to PayPal for review. Submission does not mean the dispute is won.'}</p>`:''}${['SUBMISSION_UNKNOWN','SUBMITTING'].includes(d.status)?'<p class="notice">This case needs reconciliation. Check PayPal and the submission record before taking further action. Automatic retries are disabled.</p>':''}${d.status==='RESOLVED'?'<p class="notice">PayPal reports this case is resolved.</p>':''}</section><p class="small muted">Case version ${d.version} · No automated eligibility or win-rate assessment.</p></div>`;
  const reviewPanel=document.createElement('div');reviewPanel.innerHTML=renderReview(d,review,locked);
  const sections=$$('.section-box', $('.detail-body'));
  const [checks,citations,history]=[...reviewPanel.children];
  sections[0].after(checks);sections[1].after(citations);sections[2].after(history);
  const questionContainer=document.createElement('div');questionContainer.innerHTML=questionPanel();
  const questions=questionContainer.firstElementChild;checks.after(questions);
  const conversationKey=`${id}:${d.version}`;
  for(const key of caseConversations.keys())if(key.startsWith(id+':')&&key!==conversationKey)caseConversations.delete(key);
  if(!caseConversations.has(conversationKey))caseConversations.set(conversationKey,[]);
  if(caseConversations.size>20)caseConversations.delete(caseConversations.keys().next().value);
  const showConversation=()=>{$('#question-log').innerHTML=renderConversation(caseConversations.get(conversationKey)||[],d.evidence);};
  showConversation();
  questions.addEventListener('click',event=>{
    const prompt=event.target.closest('[data-question]');
    if(prompt){$('#case-question').value=prompt.dataset.question;$('#case-question').focus();}
    const link=event.target.closest('[data-evidence-ref]');if(link)revealEvidence($('#detail-content'),link.dataset.evidenceRef);
  });
  $('#clear-questions').addEventListener('click',()=>{caseConversations.set(conversationKey,[]);showConversation();$('#question-status').textContent='Conversation cleared from this page.';});
  $$('.evidence-item', $('.detail-body')).forEach(element=>{
    const record=d.evidence.find(e=>$('small',element)?.textContent===`Evidence ID: ${e.id}`);
    if(record){element.dataset.evidenceId=record.id;element.tabIndex=-1;}
  });
  for(const panel of [checks,citations])panel.addEventListener('click',event=>{const link=event.target.closest('[data-evidence-ref]');if(link)revealEvidence($('#detail-content'),link.dataset.evidenceRef);});
  const dialog=$('#case-dialog'); if(!dialog.open)dialog.showModal();
  const rerender = async message => {await openCase(id);await loadCases();toast(message);};
  const version=()=>d.version;
  const assertSaved=()=>{if($('#draft-text').value!==d.draft)throw new Error('Save your draft edits before continuing. Saving clears any previous approval.');};
  $('#question-form').addEventListener('submit',event=>{
    event.preventDefault();busy($('button[type="submit"]',event.target),async()=>{
      try{
        assertSaved();
        const question=$('#case-question').value.trim();
        const turns=caseConversations.get(conversationKey)||[];
        const history=turns.slice(-6).map(turn=>({role:turn.role,content:turn.content}));
        $('#question-status').textContent='Asking the AI using this saved case. No case action will be taken…';
        const answer=await api(`/disputes/${id}/questions`,{method:'POST',body:{version:version(),question,history}});
        if(answer.case_version!==version())throw new Error('The answer belongs to an older case version. Refresh and ask again.');
        const content=answer.report.findings.map(f=>f.statement).join('\n').slice(0,3000);
        caseConversations.set(conversationKey,[...turns,{role:'user',content:question},{role:'assistant',content,report:answer.report,source:answer.source}].slice(-6));
        showConversation();$('#case-question').value='';$('#question-status').textContent=answer.notice;
      }catch(error){$('#question-status').textContent=error.message;throw error;}
    });
  });
  $('#analyze-evidence')?.addEventListener('click',event=>busy(event.currentTarget,async()=>{assertSaved();await api(`/disputes/${id}/analyze`,{method:'POST',body:{version:version()}});await rerender('Evidence checks saved. Review the excerpts and gaps; nothing was approved.');}));
  $('#draft-text').addEventListener('input',()=>{
    const dirty=$('#draft-text').value!==d.draft;
    $('#draft-save-status').textContent=dirty?'Unsaved edits. Save and review again before approval, export or submission.':'You are reviewing the saved response shown above.';
    for(const selector of ['#review-check','#submit-check']){const box=$(selector);if(box)box.checked=false;}
    for(const selector of ['#approve-draft','#submit-case','#export-packet']){const button=$(selector);if(button)button.disabled=dirty;}
  });
  if(d.status==='APPROVED'){
    const actions=document.createElement('div');actions.className='actions';
    actions.innerHTML='<button class="secondary" id="request-changes">Withdraw approval</button><button class="secondary" id="export-packet">Download approved packet</button>';
    $('#submit-case').after(actions);
    $('#request-changes').addEventListener('click',event=>busy(event.currentTarget,async()=>{assertSaved();await api(`/disputes/${id}/request-changes`,{method:'POST',body:{version:version()}});await rerender('Approval withdrawn. Review the response again before submission.');}));
    $('#export-packet').addEventListener('click',event=>busy(event.currentTarget,async()=>{
      assertSaved();await api(`/disputes/${id}/export?version=${version()}`);
      const link=document.createElement('a');link.href=`/api/v1/disputes/${id}/export?version=${version()}`;link.download=`payguard-${d.paypal_id}-v${d.version}.json`;document.body.append(link);link.click();link.remove();
      toast('Packet download requested. Nothing was sent to PayPal.');
    }));
  }
  $('#evidence-form')?.addEventListener('submit',event=>{event.preventDefault();const data=Object.fromEntries(new FormData(event.target));busy($('button',event.target),async()=>{assertSaved();await api(`/disputes/${id}/evidence`,{method:'POST',body:{...data,version:version()}});await rerender('Evidence added. Any previous approval has been cleared.');});});
  $('#upload-form')?.addEventListener('submit',event=>{event.preventDefault();const data=new FormData(event.target);busy($('button',event.target),async()=>{assertSaved();data.set('version',version());await api(`/disputes/${id}/upload`,{method:'POST',body:data});await rerender('PDF text added as evidence.');});});
  $('#generate-draft')?.addEventListener('click',event=>busy(event.currentTarget,async()=>{if($('#draft-text').value!==state.detail.draft){toast('Save your edits before generating another draft.');return;}await api(`/disputes/${id}/draft`,{method:'POST',body:{version:version()}});await rerender('Draft created. Review it before approving.');}));
  $('#save-draft')?.addEventListener('click',event=>busy(event.currentTarget,async()=>{await api(`/disputes/${id}/draft`,{method:'PUT',body:{version:version(),text:$('#draft-text').value}});await rerender('Draft edits saved.');}));
  $('#approve-draft')?.addEventListener('click',event=>busy(event.currentTarget,async()=>{if(!$('#review-check').checked)throw new Error('Confirm that you have reviewed the response.');if($('#draft-text').value!==state.detail.draft)throw new Error('Save your draft edits before approving.');await api(`/disputes/${id}/approve`,{method:'POST',body:{version:version(),reviewed:true}});await rerender('Response approved. Ready for your submission.');}));
  $('#submit-case')?.addEventListener('click',event=>busy(event.currentTarget,async()=>{if(!$('#submit-check').checked)throw new Error('Confirm submission using the checkbox.');if($('#draft-text').value!==state.detail.draft)throw new Error('Save and approve your latest edits before submission.');const result=await api(`/disputes/${id}/submit`,{method:'POST',headers:{'Idempotency-Key':`submit-${id}-${version()}`},body:{version:version(),confirmed:true}});await rerender(result.state==='UNKNOWN'?'Provider result is unknown. Reconcile in PayPal before retrying.':state.demo?'Submission simulated successfully.':'Response sent for provider review.');}));
  if(casePending)lockCaseControls();
}
$('#close-case').addEventListener('click',closeCase);
$('#case-dialog').addEventListener('cancel',event=>{event.preventDefault();closeCase();});
$('#keep-editing').addEventListener('click',()=>$('#discard-dialog').close());
$('#discard-edits').addEventListener('click',()=>{$('#discard-dialog').close();finishCloseCase();});
window.addEventListener('beforeunload',event=>{if(unsavedDraft()||casePending){event.preventDefault();event.returnValue='';}});
$('#new-case').addEventListener('click',()=>{$('#new-error').textContent='';$('#new-dialog').showModal();});
$('#close-new').addEventListener('click',()=>$('#new-dialog').close());
$('#new-form').addEventListener('submit',event=>{event.preventDefault();busy($('button',event.target),async()=>{
  const data=Object.fromEntries(new FormData(event.target));
  const body={paypal_id:data.paypal_id,customer:data.customer,reason:data.reason,amount_cents:Math.round(Number(data.amount)*100),currency:'USD',due_at:Math.floor(new Date(data.due).getTime()/1000)};
  try {const d=await api('/disputes',{method:'POST',body});$('#new-dialog').close();event.target.reset();state.page=1;state.status='';$$('.tab').forEach(x=>x.classList.toggle('active',x.dataset.status===''));await loadCases();await openCase(d.id);}catch(error){$('#new-error').textContent=error.message;}
});});

try {
  const config=await api('/config');$('#demo-option').hidden=!config.demo;
  try {await enter(await api('/auth/me'));} catch(error) {if(error.message!=='Sign in required')toast(error.message);}
} catch(error) {$('#auth-error').textContent='Unable to reach the server. '+error.message;}
