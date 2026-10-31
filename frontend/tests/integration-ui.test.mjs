import test from 'node:test';
import assert from 'node:assert/strict';
import {paypalPresentation} from '../public/static/integration-ui.js';

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
