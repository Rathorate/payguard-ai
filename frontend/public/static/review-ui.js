const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const sourceButton = (id, evidence) => `<button type="button" class="source-link" data-evidence-ref="${escape(id)}">${escape(evidence.find(e=>e.id===id)?.title || id)}</button>`;

export function renderReview(d, review, locked) {
  const analysis = review.analysis;
  const findings = analysis?.report.findings || [];
  const groups = [['RECORDED','What the records say'],['MISSING','What remains missing'],['CONFLICT','Statements to reconcile']];
  const checks = findings.length ? groups.map(([category,title])=>`<div class="review-group"><h4>${title}</h4>${findings.filter(f=>f.category===category).map(f=>`<article class="finding ${category}"><p>${escape(f.statement)}</p>${f.sources.map(s=>`<blockquote>${escape(s.quote)}</blockquote>${sourceButton(s.evidence_id,d.evidence)}`).join('')}</article>`).join('') || '<p class="muted">No finding returned in this category. This does not establish completeness.</p>'}</div>`).join('') : '<p class="muted">Run evidence checks to identify recorded facts, gaps and conflicting statements. Nothing is approved by this check.</p>';
  const paragraphs = review.citations.paragraphs.map(p=>`<article class="citation-paragraph"><p>${escape(p.text)}</p><div>${p.evidence_ids.map(id=>sourceButton(id,d.evidence)).join(' ')}${p.unknown_ids.length?`<span class="reference-warning">Unknown references: ${escape(p.unknown_ids.join(', '))}</span>`:!p.evidence_ids.length?'<span class="small muted">No linked source in this paragraph</span>':''}</div></article>`).join('');
  const baseline=review.latest_generated;
  return `<section class="section-box" aria-label="Evidence review"><div class="section-top"><h3>Evidence checks</h3>${!locked?`<button type="button" class="secondary compact" id="analyze-evidence">${analysis?'Refresh AI checks':'Check evidence with AI'}</button>`:''}</div><p class="muted">AI suggestions for your review. Source excerpts are checked against recorded text; their meaning and accuracy still need your judgment. Refresh makes a new AI request; a failed refresh keeps the saved report.</p>${analysis?`<p class="small muted">${escape(analysis.source)} · Saved case version ${analysis.case_version} · ${escape(new Date(analysis.created_at*1000).toLocaleString())}</p>`:''}${checks}</section>
  <section class="section-box" aria-label="Citation inspector"><h3>Inspect draft citations</h3><p class="muted">${escape(review.citations.notice)} This panel describes the saved draft; save edits to refresh it.</p>${paragraphs || '<p class="muted">Save or generate a draft to inspect its references.</p>'}</section>
  <section class="section-box" aria-label="Human review history"><h3>AI output and human decisions</h3><p class="muted">Saved versions show who generated, edited and approved a response. Earlier builds did not retain draft revisions.</p>${baseline?`<details class="evidence-item"><summary>Compare latest generated draft with current saved response</summary><div class="draft-comparison"><div><h4>${escape(baseline.source)} output · v${baseline.case_version}</h4><pre>${escape(baseline.text)}</pre></div><div><h4>Current saved response · v${d.version}</h4><pre>${escape(d.draft)}</pre></div></div></details>`:''}${review.history.map(r=>`<details class="evidence-item"><summary>${escape(r.action)} · v${r.case_version} · ${escape(r.source)}</summary><p class="small muted">${escape(r.actor)} · ${escape(new Date(r.created_at*1000).toLocaleString())}</p><pre>${escape(r.text)}</pre></details>`).join('') || '<p class="muted">No retained revisions yet. Generate or save a response to begin.</p>'}</section>`;
}

export function revealEvidence(root, identity) {
  const target=[...root.querySelectorAll('[data-evidence-id]')].find(e=>e.dataset.evidenceId===identity);
  if(!target)return false;
  target.open=true;
  target.scrollIntoView({block:'center',behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
  target.focus({preventScroll:true});
  return true;
}
