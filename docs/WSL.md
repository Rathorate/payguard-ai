# Ubuntu / WSL development

After publication, run in Ubuntu (do not overwrite an existing checkout):

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/Rathorate/payguard-ai.git
cd payguard-ai
bash scripts/bootstrap.sh
bash scripts/test.sh
bash scripts/dev.sh
```

Python 3.12+, its venv module and Git are required. Set PYTHON_BIN to an existing suitable interpreter if necessary. Use your Ubuntu release's official packages. Bootstrap creates a Linux virtual environment and a local .env only if absent. The development script loads that file as trusted shell configuration. Never source an untrusted .env or commit credentials.

Open http://127.0.0.1:8000 in Windows and select **Open interactive demo**. The server binds to loopback and relies on WSL localhost forwarding. Keep the Windows source until Linux tests pass. Do not copy the Windows virtual environment, database, sessions or test caches into WSL.

## Add the AI aspect independently

The adapter boundary is app/providers.py, function generate_draft. Preserve the (text, source) return shape and ProviderError failure behavior. Case version checks and mandatory merchant review remain outside that adapter. Tests are in tests/test_providers.py.

The optional adapter accepts OPENAI_API_KEY and OPENAI_MODEL in .env. Without a key, drafting uses the clearly labeled template. Real model quality requires separate credentialed evaluation.

## Continue without PayPal access

Keep DEMO_MODE=true. Manual disputes, evidence, drafting, approval, simulated submission and audit history work without PayPal credentials. Simulations are labeled, and no unsigned-webhook bypass is enabled.

When sandbox credentials become available, follow OPERATIONS.md. Server OAuth needs the client ID and matching secret, plus the webhook and merchant workspace configuration. API eligibility, scopes and evidence acceptance need account-specific validation. Do not enable live requests to work around sandbox access problems.

Before committing, inspect git status and the staged diff. Configure GitHub authentication normally in Ubuntu with CLI or SSH; never put tokens in remote URLs.
