from io import BytesIO

import pytest
from PIL import Image


@pytest.fixture
def generate_image():
    def wrapper(width=100, height=100, format='jpeg', filename='avatar.jpeg', color=(155, 0, 0)):
        file = BytesIO()
        image = Image.new('RGB', size=(width, height), color=color)
        image.save(file, format)
        file.name = filename
        file.seek(0)
        return file
    return wrapper


@pytest.fixture
def post_image_request(make_request, generate_image):
    async def wrapper(expected_status=None, client=None):
        return await make_request(
            'dvhb_hybrid.user:profile.picture',
            method='post',
            data=dict(picture_file=generate_image().read()),
            client=client,
            expected_status=expected_status)
    return wrapper


@pytest.fixture
def delete_image_request(make_request):
    async def wrapper(expected_status=None, client=None):
        return await make_request(
            'dvhb_hybrid.user:profile.picture',
            method='delete',
            client=client,
            expected_status=expected_status)
    return wrapper


@pytest.mark.django_db
async def test_set_picture_unauthorized(post_image_request):
    await post_image_request(expected_status=401)


@pytest.mark.django_db
async def test_set_picture_successful(app, test_client, create_new_user, post_image_request, get_profile_request):
    client = await test_client(app)
    user = await create_new_user()
    await client.authorize(email=user['email'], password=user['password'])
    await post_image_request(client=client, expected_status=200)
    # Image path should present in profile data
    profile_data = await get_profile_request(client=client, expected_status=200)
    assert profile_data['picture'] is not None
    # Try to replace existing image
    await post_image_request(client=client, expected_status=200)


@pytest.mark.django_db
async def test_delete_picture_unauthorized(delete_image_request):
    await delete_image_request(expected_status=401)


@pytest.mark.django_db
async def test_delete_picture_nonexisting(app, test_client, create_new_user, delete_image_request):
    client = await test_client(app)
    user = await create_new_user()
    await client.authorize(email=user['email'], password=user['password'])
    await delete_image_request(client=client, expected_status=409)


@pytest.mark.django_db
async def test_delete_picture_successful(app, test_client, create_new_user, post_image_request, delete_image_request):
    client = await test_client(app)
    user = await create_new_user()
    await client.authorize(email=user['email'], password=user['password'])
    await post_image_request(client=client, expected_status=200)
    await delete_image_request(client=client, expected_status=200)
