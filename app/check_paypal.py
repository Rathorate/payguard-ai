"""Read-only sandbox diagnostic. Never prints credentials or access tokens."""
import argparse
from .config import Settings
from .providers import PayPal, ProviderError
from .paypal_import import snapshot


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dispute-id',help='Optionally verify read access to your own sandbox dispute')
    parser.add_argument('--list-disputes',action='store_true',help='List at most ten sandbox dispute IDs/statuses to diagnose merchant ownership')
    args=parser.parse_args()
    settings=Settings()
    print('PayPal environment:',settings.paypal_environment, '| Client ID present:',bool(settings.paypal_client_id),'| Secret present:',bool(settings.paypal_secret),flush=True)
    provider=PayPal(settings)
    try:
        result=provider.check_sandbox_auth()
        print(result['notice'],flush=True)
        print('Client ID fingerprint:',result['client_id_fingerprint'],flush=True)
        print('Token includes seller dispute-read scope:',result['dispute_read_scope_present'],flush=True)
        if args.list_disputes:
            rows=provider.list_sandbox_disputes()
            print('Sandbox dispute list read verified. First page only; an empty page does not prove a case belongs to this merchant.',flush=True)
            for row in rows:print(row['dispute_id'],row['status'],flush=True)
        if args.dispute_id:
            snapshot(provider.details(args.dispute_id),args.dispute_id)
            print('Sandbox dispute read verified. No local case was imported and no evidence was submitted.')
    except ProviderError as exc:
        parser.exit(1,str(exc)+'\n')


if __name__=='__main__': main()
