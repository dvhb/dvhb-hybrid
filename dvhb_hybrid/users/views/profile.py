from aiohttp.web import HTTPConflict

from dvhb_hybrid.amodels import method_connect_once
from dvhb_hybrid.permissions import permissions


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
        raise HTTPConflict(reason="No user picture has been set")
    user['picture'] = None
    await user.save(fields=['picture'], connection=connection)
    # Add log entry
    await request.app.m.user_action_log_entry.create_user_profile_update(request, connection=connection)
    await Image.delete_name(old_picture, connection=connection)
