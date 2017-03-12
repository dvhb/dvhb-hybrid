import aiopg.sa
import pytest
import sqlalchemy as sa

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
    )


async def test_create(db_factory):
    app = {}
    model = Model1.factory(app)
    async with db_factory as db:
        app['db'] = db
        obj = await model.create(text='123')
    assert isinstance(obj.pk, int)


async def test_get_one(db_factory):
    app = {}
    model = Model1.factory(app)
    async with db_factory as db:
        app['db'] = db
        obj = await model.create(text='123')
        obj2 = await model.get_one(obj.pk, fields=['id', 'text'])
    assert obj.pk == obj2.pk


async def test_get_or_create(db_factory):
    app = {}
    model = Model1.factory(app)
    async with db_factory as db:
        app['db'] = db
        obj, created = await model.get_or_create(model.table.c.text=='123')
    assert isinstance(created, bool)


async def test_list(db_factory):
    app = {}
    model = Model1.factory(app)
    async with db_factory as db:
        app['db'] = db
        l = await model.get_list(limit=1, offset=1, fields=['id', 'text'])
    assert isinstance(l, list)
