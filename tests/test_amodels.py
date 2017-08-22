import asyncio
from uuid import uuid4

import aiopg.sa
import pytest
import sqlalchemy as sa

from dvhb_hybrid import exceptions
from dvhb_hybrid.amodels import Model


@pytest.fixture
def db_factory(loop):
    return aiopg.sa.create_engine(
        database='test_dvhb_hybrid', loop=loop
    )


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
def app(loop, db_factory):
    app = {
        'db': loop.run_until_complete(db_factory.__aenter__())
    }
    app['model'] = Model1.factory(app)

    yield app

    loop.run_until_complete(db_factory.__aexit__(None, None, None))


async def test_create(db_factory):
    app = {}
    model = Model1.factory(app)
    async with db_factory as db:
        app['db'] = db
        obj = await model.create(text='123', data={'1': 2, '3': '4'})
    assert isinstance(obj.pk, int)


async def test_get_one(db_factory):
    app = {}
    model = Model1.factory(app)
    async with db_factory as db:
        app['db'] = db
        obj = await model.create(text='123')
        obj2 = await model.get_one(obj.pk, fields=['id', 'text'])
        assert obj.pk == obj2.pk
        with pytest.raises(exceptions.NotFound):
            await model.get_one(None)


async def test_count(db_factory, mocker):
    app = {}
    model = Model1.factory(app)
    async with db_factory as db:
        app['db'] = db
        await model.create(text='123')
        assert await model.get_count(
            redis=mocker.Mock(
                get=asyncio.coroutine(lambda x: None),
                set=asyncio.coroutine(lambda x, v: None),
                expire=asyncio.coroutine(lambda x, v: None),
            )
        )


async def test_save(db_factory):
    app = {}
    model = Model1.factory(app)
    async with db_factory as db:
        app['db'] = db
        obj = model(text='123')
        obj.text = '321'
        await obj.save()
        assert obj.pk
        obj2 = await model.get_one(obj.pk, fields=['id', 'text'])
        await obj2.save(fields=['text'])
    assert obj.text == obj2.text


async def test_get_or_create(db_factory):
    app = {}
    model = Model1.factory(app)
    async with db_factory as db:
        app['db'] = db
        t = str(uuid4())
        obj, created = await model.get_or_create(
            model.table.c.text == t,
            defaults={'text': t})
        assert created
        obj, created = await model.get_or_create(
            model.table.c.text == t,
            defaults={'text': t})
        assert not created


async def test_list(db_factory):
    app = {}
    model = Model1.factory(app)
    async with db_factory as db:
        app['db'] = db
        l = await model.get_list(
            limit=1, offset=1, fields=['id', 'text'], sort='id')
        assert isinstance(l, list)
        l = await model.get_list(sort=['id'])
        assert isinstance(l, list)


async def test_dict(db_factory):
    app = {}
    model = Model1.factory(app)
    async with db_factory as db:
        app['db'] = db
        ids = [o.pk for o in await model.get_list(fields=['id'])]
        l = await model.get_dict(ids, fields=['id', 'text'])
    assert isinstance(l, dict)


async def test_update_json(db_factory):
    app = {}
    model = Model1.factory(app)
    async with db_factory as db:
        app['db'] = db
        obj = await model.create(text='123', data={'1': 2, '3': {'4': '5'}})
        await obj.update_json(data={'3': {'4': '8', '5': '9'}, '5': '6'})
        r = await model.get_one(obj.pk)
        assert r['data'] == {'1': 2, '3': {'4': '8', '5': '9'}, '5': '6'}

        await r.update_json('data', '9', '10', 11)
        r = await model.get_one(obj.pk)
        assert r['data']['9']['10'] == 11


async def test_create_many(app):
    result = await app['model'].create_many([
        {'text': '123', 'data': {'1': 2, '3': {'4': '5'}}},
        {'text': '222', 'data': {'1': 2, '3': {'4': '5'}}},
    ])
    assert len(result) == 2
    assert all('id' in i for i in result)


async def test_create_delete(app, new_object):
    obj = await app['model'].create(**new_object)
    obj_id = obj.pk
    r = await app['model'].get_one(obj_id, silent=True)
    assert r

    await obj.delete()

    r = await app['model'].get_one(obj_id, silent=True)
    assert not r
