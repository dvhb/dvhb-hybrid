from .. import utils
from .storages import image_storage


async def save_image(app, user, filename, content, content_type):
    name = await app.loop.run_in_executor(
        None, image_storage.save, filename, content)
    image_uuid = image_storage.uuid(name)
    image = app.models.image
    await image.create(
        uuid=image_uuid,
        image=name,
        mime_type=content_type,
        author_id=user.id,
        created_at=utils.now(),
    )
    return image_uuid
