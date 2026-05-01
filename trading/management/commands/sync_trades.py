from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from twisted.internet import reactor

from trading.models import CTraderCredentials
from trading.services.ctrader_client import CTraderSync


class Command(BaseCommand):
    help = 'Sync cTrader trades for a user'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)

    def handle(self, *args, **opts):
        User = get_user_model()
        try:
            user = User.objects.get(username=opts['username'])
        except User.DoesNotExist:
            raise CommandError(f"User {opts['username']} not found")

        try:
            creds = user.ctrader_credentials
        except CTraderCredentials.DoesNotExist:
            raise CommandError('No cTrader credentials for this user. Run setup_ctrader first.')

        sync = CTraderSync(user, creds)

        def on_done(_):
            self.stdout.write(self.style.SUCCESS('Sync complete'))
            reactor.stop()

        def on_fail(failure):
            self.stdout.write(self.style.ERROR(f'Sync failed: {failure}'))
            reactor.stop()

        d = sync.run()
        d.addCallbacks(on_done, on_fail)
        reactor.run()
