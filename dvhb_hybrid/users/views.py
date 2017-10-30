from aiohttp_apiset.exceptions import ValidationError
from django.contrib.auth.hashers import check_password, make_password
from dvhb_hybrid import exceptions
from dvhb_hybrid.amodels import method_redis_once, method_connect_once
from dvhb_hybrid.decorators import recaptcha
from dvhb_hybrid.permissions import permissions, gen_api_key
from dvhb_hybrid.redis import redis_key


async def login(request, email, password):
    user = await request.app.models.user.get_user_by_email(email)
    if user:
        if not user.is_active:
            raise exceptions.HTTPConflict(reason="User disabled")
        elif check_password(password, user.password):
            await gen_api_key(user.id, request=request, auth='email')
            request.user = user
            raise exceptions.HTTPOk(
                uid=user.id, headers={'Authorization': request.session}, content_type='application/json')
    raise exceptions.HTTPUnauthorized(reason="Login incorrect")


@method_redis_once('sessions')
@permissions
async def logout(request, sessions):
    key = redis_key(request.app.name, request.session, 'session')
    await sessions.delete(key)
    raise exceptions.HTTPOk(content_type='application/json')


@method_connect_once
@recaptcha
async def create_user(request, user, connection=None):
    user_exists = await request.app.models.user.get_user_by_email(user['email'], connection=connection)
    if user_exists:
        raise exceptions.HTTPConflict(reason='User with this email already exists.')
    user['password'] = make_password(user.pop('password'))
    user['is_active'] = False
    user = await request.app.models.user.create(email=user['email'], password=user['password'], connection=connection)
    await request.app.models.user_activation_request.send(user, connection=connection)


@method_connect_once
async def activate_user(request, activation_code, connection=None):
    activation_request = await request.app.models.user_activation_request.get_one(
        activation_code, connection=connection)
    if activation_request.is_activated():
        raise exceptions.HTTPConflict(reason="Account have been activated already")
    # Change activation request status
    await activation_request.activate(connection=connection)

    # Change user status
    user = await request.app.models.user.get_one(activation_request.user_id, connection=connection)
    await user.activate(connection=connection)

    # Generate and return API key
    await gen_api_key(user.id, request=request, auth='email')
    request.user = user
    raise exceptions.HTTPOk(
        uid=user.id, headers={'Authorization': request.session}, content_type='application/json')


@permissions
async def change_password(request, old_password, new_password):
    if not check_password(old_password, request.user.password):
        raise ValidationError(old_password=['Wrong password'])
    request.user['password'] = make_password(new_password)
    await request.user.save(fields=['password'])


@method_connect_once
@permissions
async def request_deletion(request, lang_code, connection=None):
    user = request.user
    deletion_request = await request.app.models.user_profile_delete_request.get_by_email(
        user.email, connection=connection)
    if deletion_request:
        raise exceptions.HTTPConflict(reason="Account removing have been requested already")
    await request.app.models.user_profile_delete_request.send(
        user, lang_code=lang_code, connection=connection)
