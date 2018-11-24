from collections import Mapping
from datetime import timedelta, datetime

from aiohttp import web
from aioworkers.core.base import AbstractEntity
from django.contrib.auth.hashers import check_password, make_password
from dvhb_hybrid.amodels import method_connect_once
from dvhb_hybrid.user_action_log.enums import \
    UserActionLogEntryType, UserActionLogEntrySubType, UserActionLogStatus
from jose import jwt
from yarl import URL


@method_connect_once
async def user_login(request, email, password, connection=None):
    models = request.app.models
    user = await models.user.get_user_by_email(email, connection=connection)
    if user:
        if not user.is_active:
            raise web.HTTPForbidden(reason="User disabled")
        elif check_password(password, user.password):
            await models.user_action_log_entry.create_login(
                request, user_id=user.pk, connection=connection)
            token = request.app.context.jwt.generate(uid=user.id)
            return web.json_response(
                {
                    'uid': user.id,
                    'profile': await user.get_profile(connection=connection),
                    'token': token,
                }, headers={'Authorization': 'Bearer %s' % token},
            )
    raise web.HTTPUnauthorized(reason="Login incorrect")


@method_connect_once
async def user_request_change_password(request, email, connection=None):
    m = request.app.m
    user = await m.user.get_user_by_email(email, silent=False, connection=connection)
    log = await m.user_action_log_entry.create_record(
        request,
        user_id=user.pk,
        message="User changed password",
        type=UserActionLogEntryType.password,
        subtype=UserActionLogEntrySubType.update,
        status=UserActionLogStatus.request,
        connection=connection)
    token = request.app.context.jwt.generate(
        email=user.email,
        exp=timedelta(minutes=15),
        log_id=log.pk,
    )
    ctx = request.app.context
    url = URL(ctx.config.urls.user_change_password.format(token=token))
    url = ctx.config.http.get_url('url').join(url)
    await ctx.mailer.send(
        mail_to=user.email, subject='Change email',
        body='For changes password please follow %s' % url,
        db_connection=connection,
    )


@method_connect_once
async def user_change_password_by_request(request, new_password, connection=None):
    session = request.session
    email = session.get('email')
    if not email or not session.get('log_id'):
        raise web.HTTPForbidden()
    m = request.app.m
    user = await m.user.get_user_by_email(email, silent=False, connection=connection)
    log = await m.user_action_log_entry.get_one(session.get('log_id'), connection=connection)
    if log.status == UserActionLogStatus.done.value:
        raise web.HTTPForbidden()
    user['password'] = make_password(new_password)
    await user.save(fields=['password'], connection=connection)
    log['status'] = UserActionLogStatus.done.value
    await log.save(fields=['status'], connection=connection)


class JWT(AbstractEntity):
    def generate(self, *args, **kwargs):
        cfg = self.config
        if not args:
            payload = {}
        elif not isinstance(args[0], Mapping):
            raise ValueError(args)
        else:
            payload = dict(args[0])
        payload.update(kwargs)
        now = datetime.utcnow()
        payload.setdefault('iat', now)
        exp = payload.get('exp')
        if not exp:
            payload['exp'] = now + timedelta(seconds=cfg.get_duration('life'))
        elif isinstance(exp, timedelta):
            payload['exp'] += now

        return jwt.encode(payload, cfg.secret, algorithm=cfg.algorithms[0])

    def decode(self, token, **kwargs):
        cfg = self.config
        return jwt.decode(token, cfg.secret, cfg.algorithms, **kwargs)

    @web.middleware
    async def middleware(self, request, handler):
        token = request.headers.get('Authorization')
        if token and token.startswith('Bearer'):
            token = token[7:]
        else:
            token = request.rel_url.query.get('token')
            if not token:
                token = request.headers.get('token')
        request.verified = False

        if token:
            try:
                payload = self.decode(token)
                request.verified = True
            except jwt.JWTError:
                raise web.HTTPUnauthorized()
        else:
            payload = {}
        request.session = payload
        return await handler(request)
