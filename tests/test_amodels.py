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

        await r.update_json('data', '3', '4', 1)
        r = await model.get_one(obj.pk)
        assert r['data']['3']['4'] == 1
