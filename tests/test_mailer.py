import asyncio

import pytest
from django.core import mail


@pytest.mark.django_db
async def test_mailer(app,  cli):
    # Запускаем приложение
    await cli()
    email = 'user@example.com'
    mail.outbox = []
    await app.mailer.send(email, 'Test mailer', 'Test body')
    await asyncio.sleep(1, loop=app.loop)
    assert app.mailer.running()
    assert len(mail.outbox) == 1
