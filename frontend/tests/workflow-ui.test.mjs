import test from 'node:test';
import assert from 'node:assert/strict';
import {renderWorkflow} from '../public/static/workflow-ui.js';

test('workflow escapes provider and evidence content; action names are descriptive, not execution controls',()=>{
  const attack='<img src=x onerror=alert(1)>';
  const html=renderWorkflow({connected:true,demo:true,stale:true,next_step:attack,notice:attack,
    provider:{stage:attack,provider_status:attack,observed_at:1,due_at:0,actions:['provide-evidence']},
    checks:[{label:attack,state:'REVIEW',detail:attack,evidence_ids:['e1']}]},[{id:'e1',title:attack}]);
  assert.ok(!html.includes('<img'));
  assert.ok(html.includes('&lt;img'));
  assert.ok(html.includes('submissions are simulated'));
  assert.ok(html.includes('data-evidence-ref="e1"'));
  assert.ok(html.includes('id="refresh-paypal-status"'));
  assert.ok(html.includes('A listed action does not guarantee acceptance'));
});

test('unconnected older cases do not invent provider stage or actions',()=>{
  const html=renderWorkflow({connected:false,demo:true,provider:null,next_step:'Prepare locally',notice:'Guidance only',checks:[]},[]);
  assert.ok(html.includes('No provider observation yet'));
  assert.ok(!html.includes('id="refresh-paypal-status"'));
  assert.ok(!html.includes('Provider status'));
});
