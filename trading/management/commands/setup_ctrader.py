import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from trading.models import CTraderCredentials


class Command(BaseCommand):
    help = 'Load cTrader credentials from .env into a user (dev only)'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)

    def handle(self, *args, **opts):
        User = get_user_model()
        try:
            user = User.objects.get(username=opts['username'])
        except User.DoesNotExist:
            raise CommandError(f"User {opts['username']} not found")

        client_id = os.getenv('CTRADER_CLIENT_ID')
        client_secret = os.getenv('CTRADER_CLIENT_SECRET')
        access_token = os.getenv('CTRADER_ACCESS_TOKEN')
        account_id = os.getenv('CTRADER_ACCOUNT_ID')
        is_live = os.getenv('CTRADER_IS_LIVE', 'False') == 'True'

        if not all([client_id, client_secret, access_token, account_id]):
            raise CommandError('Missing cTrader env vars in .env')

        creds, created = CTraderCredentials.objects.get_or_create(
            user=user,
            defaults={
                'client_id': client_id,
                'account_id': int(account_id),
                'is_live': is_live,
            },
        )
        creds.client_id = client_id
        creds.client_secret = client_secret
        creds.access_token = access_token
        creds.account_id = int(account_id)
        creds.is_live = is_live
        creds.save()

        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'{action} cTrader credentials for {user.username}'))
