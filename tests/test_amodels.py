import asyncio
from uuid import uuid4

import asyncpgsa
import pytest
import sqlalchemy as sa

from dvhb_hybrid import exceptions
from dvhb_hybrid.amodels import Model


class Model1(Model):
    table = sa.table(
        'test',
        sa.column('id', sa.Integer),
        sa.column('text', sa.Text),
        sa.column('data', sa.JSON),
    )


@pytest.fixture
def new_object():
    return dict(text='123', data={'1': 2, '3': {'4': '5'}})


@pytest.fixture
def model(app):
    return Model1.factory(app)


async def test_create(model, app, aiohttp_client):
    await aiohttp_client(app)
    obj = await model.create(text='123', data={'1': 2, '3': '4'})
    assert isinstance(obj.pk, int)


async def test_get_one(app, model, aiohttp_client):
    await aiohttp_client(app)
    obj = await model.create(text='123')
    obj2 = await model.get_one(obj.pk, fields=['id', 'text'])
    assert obj.pk == obj2.pk
    with pytest.raises(exceptions.NotFound):
        await model.get_one(None)


async def test_count(app, mocker, model, aiohttp_client):
    await aiohttp_client(app)
    await model.create(text='123')
    assert await model.get_count(
        redis=mocker.Mock(
            get=asyncio.coroutine(lambda x: None),
            set=asyncio.coroutine(lambda x, v: None),
            expire=asyncio.coroutine(lambda x, v: None),
        )
    )


async def test_save(app, model, aiohttp_client):
    await aiohttp_client(app)
    obj = model(text='123')
    obj.text = '321'
    await obj.save()
    assert obj.pk
    obj2 = await model.get_one(obj.pk, fields=['id', 'text'])
    await obj2.save(fields=['text'])
    assert obj.text == obj2.text


async def test_get_or_create(app, model, aiohttp_client):
    await aiohttp_client(app)
    t = str(uuid4())
    obj, created = await model.get_or_create(
        model.table.c.text == t,
        defaults={'text': t})
    assert created
    obj, created = await model.get_or_create(
        model.table.c.text == t,
        defaults={'text': t})
    assert not created


async def test_list(app, model, aiohttp_client):
    await aiohttp_client(app)
    l = await model.get_list(
        limit=1, offset=1, fields=['id', 'text'], sort='id')
    assert isinstance(l, list)
    l = await model.get_list(sort=['id'])
    assert isinstance(l, list)


async def test_dict(app, model, aiohttp_client):
    await aiohttp_client(app)
    ids = [o.pk for o in await model.get_list(fields=['id'])]
    l = await model.get_dict(ids, fields=['id', 'text'])
    assert isinstance(l, dict)


async def test_update_json(app, model, aiohttp_client):
    await aiohttp_client(app)
    obj = await model.create(text='123', data={'1': 2, '3': {'4': '5'}})
    await obj.update_json(data={'3': {'4': '8', '5': '9'}, '5': '6'})
    r = await model.get_one(obj.pk)
    assert r['data'] == {'1': 2, '3': {'4': '8', '5': '9'}, '5': '6'}

    await r.update_json('data', '9', '10', 11)
    r = await model.get_one(obj.pk)
    assert r['data']['9']['10'] == 11


async def test_create_many(app, model, aiohttp_client):
    await aiohttp_client(app)
    result = await model.create_many([
        {'text': '123', 'data': {'1': 2, '3': {'4': '5'}}},
        {'text': '222', 'data': {'1': 2, '3': {'4': '5'}}},
    ])
    assert len(result) == 2
    assert all('id' in i for i in result)


async def test_create_delete(app, model, new_object, aiohttp_client):
    await aiohttp_client(app)
    obj = await model.create(**new_object)
    obj_id = obj.pk
    r = await model.get_one(obj_id, silent=True)
    assert r

    await obj.delete()

    r = await model.get_one(obj_id, silent=True)
    assert not r


async def test_validate_and_save(app, model, new_object, aiohttp_client):
    await aiohttp_client(app)

    def validator(obj, data):
        if data:
            if len(obj.text) > len(data['text']):
                raise Exception()
            else:
                data['text'] = 2 * data['text']
        return data

    m = model
    m.update_validators = (validator,)
    o = await m.create(**new_object)

    # Update object with invalid data
    with pytest.raises(Exception):
        await o.validate_and_save({'text': '12'})
    assert (await m.get_one(o.pk))['text'] == '123'

    # Valid update
    await o.validate_and_save({'text': '1234'})
    assert (await m.get_one(o.pk))['text'] == '12341234'

    # Valid update
    o = await m.get_one(o.pk, fields=['id'])
    await o.validate_and_save({})
