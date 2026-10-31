import test from 'node:test';
import assert from 'node:assert/strict';
import {caseChatPicker} from '../public/static/case-chat-ui.js';

test('dashboard chat prefers a reviewable case and retains the merchant selection',()=>{
  const cases=[{id:'done',status:'SUBMITTED',paypal_id:'PP-D-1',customer:'Done'},{id:'review',status:'REVIEW',paypal_id:'PP-D-2',customer:'Review'}];
  assert.equal(caseChatPicker(cases).selectedId,'review');
  assert.equal(caseChatPicker(cases,'done').selectedId,'done');
  assert.equal(caseChatPicker(cases,'removed').selectedId,'review');
});
test('case identifiers and customer text cannot inject dashboard markup',()=>{
  const attack='"><img src=x onerror=alert(1)>';
  const view=caseChatPicker([{id:attack,status:'OPEN',paypal_id:attack,customer:attack}]);
  assert.ok(!view.options.includes('<img'));
  assert.ok(view.options.includes('&lt;img'));
});
test('an empty workspace has an explicit disabled chat state without invented cases',()=>{
  const view=caseChatPicker([]);
  assert.equal(view.empty,true);
  assert.equal(view.selectedId,'');
  assert.match(view.options,/Add a case/);
});
