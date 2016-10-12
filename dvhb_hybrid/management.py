import asyncio
import time

from django.core.management.base import BaseCommand


class AsyncCommand(BaseCommand):
    class_application = NotImplemented

    async def run(self, *args, **options):
        raise NotImplementedError()

    def handle(self, *args, **options):
        start = time.time()
        loop = asyncio.get_event_loop()

        if self.class_application is not None:
            self.app = self.class_application(loop=loop)

        try:
            loop.run_until_complete(self.run(*args, **options))

        finally:
            if self.class_application is not None:
                loop.run_until_complete(self.app.cleanup())
            self.stdout.write('({}) done'.format(time.time() - start))
