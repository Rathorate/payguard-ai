export function publicDemoAvailable(config) {
  return config.demo === true && config.public_demo_enabled === true;
}

export function clearIntegrationSettings(root = document) {
  for (const id of ['integration-cards', 'paypal-workspace', 'paypal-feedback', 'paypal-import-feedback']) {
    root.querySelector('#' + id).textContent = '';
  }
  root.querySelector('#paypal-setup-controls').hidden = true;
  root.querySelector('#paypal-connection-notice').textContent = 'Loading this workspace’s integration settings…';
}

export async function loadIntegrationSettings(read, root, isCurrent) {
  clearIntegrationSettings(root);
  const data = await read();
  return isCurrent() ? data : null;
}

export function paypalPresentation(data, user) {
  if (user.sample_workspace) return {
    label: 'Sample workspace', configured: false, showSetup: false,
    message: 'This sample workspace uses synthetic cases and is separate from your PayPal merchant workspace. Sign out, then sign in with your existing PayGuard merchant account to use its PayPal connection. Demo submissions remain simulated.'
  };
  if (data.paypal_configured) return {
    label: 'Configured', configured: true, showSetup: true,
    message: `PayPal ${data.paypal_environment} credentials are configured for this workspace. Use Test sandbox authentication to verify them; configuration alone does not verify dispute permissions. ${data.mode === 'demo' ? 'Submissions remain simulated.' : ''}`
  };
  if (data.paypal_status === 'workspace_unlinked') return {
    label: 'Workspace not linked', configured: false, showSetup: false,
    message: 'This PayGuard workspace is not linked to the deployment’s PayPal merchant. Sign out and sign in with your existing merchant account. Creating another workspace does not link it automatically. The deployment administrator can review the merchant mapping if needed.'
  };
  return {
    label: 'Setup required', configured: false, showSetup: true,
    message: 'PayPal credentials are not configured for this workspace. The deployment administrator must set the sandbox Client ID and Secret on the backend. Keep credentials out of the browser and repository.'
  };
}
