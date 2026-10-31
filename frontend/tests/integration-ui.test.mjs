import test from 'node:test';
import assert from 'node:assert/strict';
import {paypalPresentation,loadIntegrationSettings,publicDemoAvailable} from '../public/static/integration-ui.js';

test('simulated submissions do not enable guest entry without an explicit opt-in', () => {
  for (const config of [{demo:true}, {demo:true,public_demo_enabled:false}, {demo:false,public_demo_enabled:true}]) assert.equal(publicDemoAvailable(config),false);
  assert.equal(publicDemoAvailable({demo:true,public_demo_enabled:true}),true);
});

function previousAccountView() {
  const elements = Object.fromEntries(['integration-cards','paypal-workspace','paypal-feedback','paypal-import-feedback','paypal-setup-controls','paypal-connection-notice'].map(id => ['#'+id,{textContent:'previous merchant details',hidden:false}]));
  return {elements, querySelector: id => elements[id]};
}

test('loading another account clears previous merchant details and hides controls immediately', async () => {
  const root=previousAccountView();
  let resolve;
  const pending=loadIntegrationSettings(()=>new Promise(done=>{resolve=done;}),root,()=>true);
  for (const id of ['integration-cards','paypal-workspace','paypal-feedback','paypal-import-feedback']) assert.equal(root.elements['#'+id].textContent,'');
  assert.equal(root.elements['#paypal-setup-controls'].hidden,true);
  resolve({paypal_status:'workspace_unlinked'});
  assert.deepEqual(await pending,{paypal_status:'workspace_unlinked'});
});

test('a delayed response from a departed account cannot repopulate the current view', async () => {
  const root=previousAccountView();
  let resolve, current=true;
  const pending=loadIntegrationSettings(()=>new Promise(done=>{resolve=done;}),root,()=>current);
  current=false;
  resolve({paypal_configured:true});
  assert.equal(await pending,null);
  assert.equal(root.elements['#integration-cards'].textContent,'');
});

test('sample users receive account guidance without merchant setup controls', () => {
  const view = paypalPresentation({paypal_configured:true}, {sample_workspace:true});
  assert.equal(view.label, 'Sample workspace');
  assert.equal(view.showSetup, false);
  assert.equal(view.configured, false);
  assert.match(view.message, /Sign out/);
});
test('linked credentials are not represented as verified authentication', () => {
  const view = paypalPresentation({paypal_configured:true,paypal_environment:'sandbox',mode:'demo'}, {});
  assert.equal(view.label, 'Configured');
  assert.equal(view.showSetup, true);
  assert.match(view.message, /configuration alone does not verify dispute permissions/);
  assert.match(view.message, /simulated/);
});
test('unlinked merchants are directed to the correct account instead of remapping a tenant', () => {
  const view = paypalPresentation({paypal_status:'workspace_unlinked'}, {});
  assert.equal(view.label, 'Workspace not linked');
  assert.equal(view.showSetup, false);
  assert.match(view.message, /Creating another workspace does not link it/);
});
test('missing credentials and legacy servers retain useful setup guidance', () => {
  for (const data of [{paypal_status:'credentials_missing'}, {}]) {
    const view = paypalPresentation(data, {});
    assert.equal(view.showSetup, true);
    assert.equal(view.label, 'Setup required');
  }
});
