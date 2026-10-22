import test from 'node:test';
import assert from 'node:assert/strict';
import {renderReview} from '../public/static/review-ui.js';

test('untrusted model findings, quotes, drafts and identities render as text',()=>{
  const attack='<img src=x onerror=alert(1)>';
  const d={version:3,draft:attack,evidence:[{id:'e1',title:attack}]};
  const review={analysis:{source:'GROQ',case_version:3,created_at:1,report:{findings:[{category:'RECORDED',statement:attack,sources:[{evidence_id:'e1',quote:attack}]}]}},citations:{notice:'References are not verification.',paragraphs:[{text:attack,evidence_ids:['e1'],unknown_ids:[attack]}]},latest_generated:{source:'GROQ',case_version:2,text:attack},history:[{action:'APPROVED',case_version:3,source:'MERCHANT',actor:attack,created_at:1,text:attack}]};
  const html=renderReview(d,review,false);
  assert.ok(!html.includes('<img'));
  assert.ok(html.includes('&lt;img'));
  assert.ok(html.includes('data-evidence-ref="e1"'));
  assert.ok(html.includes('Unknown references:'));
  assert.ok(html.includes('Compare latest generated draft'));
});

test('older cases and missing analyses have honest empty states; locked cases cannot analyze',()=>{
  const html=renderReview({version:1,draft:'',evidence:[]},{analysis:null,latest_generated:null,history:[],citations:{notice:'References are not verification.',paragraphs:[]}},true);
  assert.ok(!html.includes('id="analyze-evidence"'));
  assert.ok(html.includes('No retained revisions yet'));
  assert.ok(html.includes('Nothing is approved'));
  assert.ok(html.includes('Save or generate a draft'));
});
