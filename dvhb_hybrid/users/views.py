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
    user = await request.app.models.user.create(
        email=user['email'], password=make_password(user['password']), connection=connection)
    activation_request = await request.app.models.user_activation_request.send(
        user, lang_code=user.get('lang_code', 'en'), connection=connection)
    await activation_request.mark_as_sent(connection=connection)


@method_connect_once
async def activate_user(request, activation_code, connection=None):
    activation_request = await request.app.models.user_activation_request.get_one(
        activation_code, connection=connection)
    if activation_request.is_confirmed():
        raise exceptions.HTTPConflict(reason="Account have been activated already")
    # Change activation request status
    await activation_request.confirm(connection=connection)

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

    deletion_request = await request.app.models.user_profile_delete_request.send(
        user, lang_code=lang_code, connection=connection)
    await deletion_request.mark_as_sent(connection=connection)


@method_connect_once
@permissions
async def confirm_deletion(request, confirmation_code, connection=None):
    user = request.user
    deletion_request = await request.app.models.user_profile_delete_request.get_one(
        confirmation_code, connection=connection)
    if deletion_request.user_id != user.pk:
        raise exceptions.HTTPConflict(reason='Confirmation code does not match to user')
    if deletion_request.is_confirmed():
        raise exceptions.HTTPConflict(reason="Account removing have been confirmed already")
    if deletion_request.is_cancelled():
        raise exceptions.HTTPConflict(reason="Account removing have been cancelled already")

    # Change request status
    await deletion_request.confirm(connection=connection)

    # Change user status
    await user.delete_account(connection=connection)


@method_connect_once
@permissions
async def cancel_deletion(request, confirmation_code, connection=None):
    user = request.user
    deletion_request = await request.app.models.user_profile_delete_request.get_one(
        confirmation_code, connection=connection)
    if deletion_request.user_id != user.pk:
        raise exceptions.HTTPConflict(reason='Confirmation code does not match to user')
    if deletion_request.is_confirmed():
        raise exceptions.HTTPConflict(reason="Account removing have been confirmed already")
    if deletion_request.is_cancelled():
        raise exceptions.HTTPConflict(reason="Account removing have been cancelled already")

    # Change request status
    await deletion_request.cancel(connection=connection)


@permissions
async def get_profile(request):
    user = request.user
    return await user.get_profile()


@permissions
async def patch_profile(request, profile_data):
    user = request.user
    await user.patch_profile(profile_data)
    return await user.get_profile()


@method_connect_once
@permissions
async def post_profile_picture(request, picture_file, connection=None):
    user = request.user
    Image = request.app.m.image
    new_picture = await Image.from_field(picture_file, user=user, connection=connection)
    old_picture = user.picture
    user['picture'] = new_picture.image
    await user.save(fields=['picture'], connection=connection)
    if old_picture:
        await Image.delete_name(old_picture, connection=connection)
    user.prepare_image(new_picture)
    return new_picture


@method_connect_once
@permissions
async def delete_profile_picture(request, connection=None):
    user = request.user
    Image = request.app.m.image
    old_picture = user.picture
    if not old_picture:
        raise exceptions.HTTPConflict(reason="No user picture has been set")
    user['picture'] = None
    await user.save(fields=['picture'], connection=connection)
    await Image.delete_name(old_picture, connection=connection)
