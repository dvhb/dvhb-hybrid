from aiohttp_apiset.exceptions import ValidationError
from django.contrib.auth.hashers import check_password, make_password
from dvhb_hybrid import exceptions
from dvhb_hybrid.amodels import method_redis_once, method_connect_once
from dvhb_hybrid.decorators import recaptcha
from dvhb_hybrid.permissions import permissions, gen_api_key
from dvhb_hybrid.redis import redis_key


@method_connect_once
async def login(request, email, password, connection=None):
    user = await request.app.models.user.get_user_by_email(email)
    if user:
        if not user.is_active:
            raise exceptions.HTTPConflict(reason="User disabled")
        elif check_password(password, user.password):
            await gen_api_key(user.id, request=request, auth='email')
            request.user = user
            await user.on_login(connection=connection)
            await request.app.m.user_action_log_entry.create_login(request, connection=connection)
            raise exceptions.HTTPOk(
                uid=user.id,
                headers={'Authorization': request.api_key},
                content_type='application/json'
            )
    raise exceptions.HTTPUnauthorized(reason="Login incorrect")


@method_redis_once('sessions')
@permissions
async def logout(request, sessions):
    key = redis_key(request.app.name, request.api_key, 'session')
    await sessions.delete(key)
    await request.app.m.user_action_log_entry.create_logout(request)
    raise exceptions.HTTPOk(content_type='application/json')


@method_connect_once
@recaptcha
async def create_user(request, user, connection=None):
    user_exists = await request.app.models.user.get_user_by_email(user['email'], connection=connection)
    if user_exists:
        raise exceptions.HTTPConflict(reason='User with this email already exists.')
    lang_code = user.get('lang_code', 'en')
    user = await request.app.models.user.create(
        email=user['email'], password=make_password(user['password']), connection=connection)
    activation_request = await request.app.models.user_activation_request.send(
        user, lang_code=lang_code, connection=connection)
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
    # Add log entry
    await request.app.m.user_action_log_entry.create_user_registration(request, connection=connection)
    raise exceptions.HTTPOk(
        uid=user.id,
        headers={'Authorization': request.api_key},
        content_type='application/json'
    )


@method_connect_once
@permissions
async def change_password(request, old_password, new_password, connection=None):
    if not check_password(old_password, request.user.password):
        raise ValidationError(old_password=['Wrong password'])
    request.user['password'] = make_password(new_password)
    await request.user.save(fields=['password'], connection=connection)
    await request.app.m.user_action_log_entry.create_change_password(request, connection=connection)


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
    # Add log entry
    await request.app.m.user_action_log_entry.create_user_deletion(request, connection=connection)


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


@method_connect_once
@permissions
async def patch_profile(request, profile_data, connection=None):
    user = request.user
    await user.patch_profile(profile_data, connection=connection)
    # Add log entry
    await request.app.m.user_action_log_entry.create_user_profile_update(request, connection=connection)
    return await user.get_profile(connection=connection)


@method_connect_once
@permissions
async def post_profile_picture(request, picture_file, connection=None):
    user = request.user
    Image = request.app.m.image
    new_picture = await Image.from_field(picture_file, user=user, connection=connection)
    old_picture = user.picture
    user['picture'] = new_picture.image
    await user.save(fields=['picture'], connection=connection)
    # Add log entry
    await request.app.m.user_action_log_entry.create_user_profile_update(request, connection=connection)
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
    # Add log entry
    await request.app.m.user_action_log_entry.create_user_profile_update(request, connection=connection)
    await Image.delete_name(old_picture, connection=connection)


@method_connect_once
@permissions
async def send_email_change_request(request, new_email_address, lang_code, connection=None):
    user = request.user
    orig_m = request.app.m.user_change_email_original_address_request
    new_m = request.app.m.user_change_email_new_address_request

    # Same email specified
    if user.email == new_email_address:
        raise ValidationError(new_email_address=["User's existing email specified"])

    orig_address_request = await orig_m.get_by_new_email(
        new_email_address=new_email_address, user_id=user.pk, connection=connection)
    new_address_request = await new_m.get_by_new_email(
        new_email_address=new_email_address, user_id=user.pk, connection=connection)

    # Change to this address has been requested already
    if orig_address_request is not None and orig_address_request.user_id == user.pk:
        raise exceptions.HTTPConflict(reason="Email change to this address requested already")
    if new_address_request is not None and new_address_request.user_id == user.pk:
        raise exceptions.HTTPConflict(reason="Email change to this address requested already")

    # Create and send confirmation request for both original and new email addresses
    await orig_m.send(user, new_email_address, lang_code, connection=connection)
    await new_m.send(user, new_email_address, lang_code, connection=connection)
    raise exceptions.HTTPOk(content_type='application/json')


@method_connect_once
async def approve_email_change_request(request, confirmation_code, connection=None):
    orig_m = request.app.m.user_change_email_original_address_request
    new_m = request.app.m.user_change_email_new_address_request

    # Change to this address has been requested already
    orig_address_request = await orig_m.get_one(confirmation_code, connection=connection, silent=True)
    new_address_request = await new_m.get_one(confirmation_code, connection=connection, silent=True)

    confirmation_request = orig_address_request or new_address_request

    # Confirmation code not found for both addresses
    if confirmation_request is None:
        raise exceptions.HTTPNotFound(reason="No such confirmation code")
    else:
        # It is confirmed already
        if confirmation_request.is_confirmed():
            raise exceptions.HTTPConflict(reason="Confirmation already obtained")
        # Change confirmation request status
        await confirmation_request.confirm(connection=connection)

        orig_address_request = await orig_m.get_by_new_email(
            confirmation_request.new_email, user_id=confirmation_request.user_id, connection=connection)
        new_address_request = await new_m.get_by_new_email(
            confirmation_request.new_email, user_id=confirmation_request.user_id, connection=connection)

        # Check whether second request confirmed already
        if orig_address_request and new_address_request \
                and orig_address_request.is_confirmed() and new_address_request.is_confirmed():
            await request.app.m.user.change_email(
                confirmation_request.user_id, confirmation_request.new_email, connection=connection)

        raise exceptions.HTTPOk(content_type='application/json')
