import asyncio

import pytest
from django.core import mail


@pytest.mark.django_db
async def test_mailer(context, aiohttp_client):
    await aiohttp_client(context.app)
    email = 'user@example.com'
    mail.outbox = []
    await context.mailer.send(email, 'Test mailer', 'Test body')
    await asyncio.sleep(2)
    assert len(mail.outbox) == 1
