import pytest

from dvhb_hybrid import utils
from dvhb_hybrid.amodels import (
    Model,
    MPTTMixin,
    derive_from_django,
    method_connect_once,
)

from . import models


@derive_from_django(models.MPTTTestModel)
class MptttTestModel(MPTTMixin, Model):
    order_insertion_by = ['name']

    @classmethod
    def set_defaults(cls, data: dict):
        data.setdefault('created_at', utils.now())

    @classmethod
    @method_connect_once
    async def delete_all(cls, connection=None):
        await connection.execute(cls.table.delete())


async def assert_mptt_valid(node, **kwargs):
    # Refetch data
    node = await node.get_one(node.id)
    for k in kwargs:
        assert node[k] == kwargs[k], "wrong {}: expected {}, got {}".format(k, kwargs[k], node[k])


def assert_nodes_ids(items, ids, pk='id'):
    assert sorted(map(lambda i: i[pk], items)) == sorted(ids)


@pytest.mark.django_db
async def test_create_several_tops(app, aiohttp_client):
    await aiohttp_client(app)
    await app.m.mpttt_test_model.delete_all()
    top1 = await app.m.mpttt_test_model.create(name="Top1")
    top2 = await app.m.mpttt_test_model.create(name="Top2")
    # top3 = await app.m.mpttt_test_model.create(name="Top3")
    await assert_mptt_valid(top1, parent_id=None, level=0, tree_id=1, lft=1, rght=2)
    await assert_mptt_valid(top2, parent_id=None, level=0, tree_id=2, lft=1, rght=2)
    # FIXME: tree_id = 2, 3 expected
    # await assert_mptt_valid(top3, parent_id=None, level=0, tree_id=3, lft=1, rght=2)


@pytest.mark.django_db
async def test_create_parent_and_child(app, aiohttp_client):
    await aiohttp_client(app)
    await app.m.mpttt_test_model.delete_all()
    parent = await app.m.mpttt_test_model.create(name="Parent")
    child = await app.m.mpttt_test_model.create(parent_id=parent.pk, name="Child")
    await assert_mptt_valid(parent, parent_id=None, level=0, tree_id=1, lft=1, rght=4)
    await assert_mptt_valid(child, parent_id=parent.pk, level=1, tree_id=1, lft=2, rght=3)


@pytest.mark.django_db
async def test_create_parent_and_child_and_grandchild(app, aiohttp_client):
    await aiohttp_client(app)
    model = app.m.mpttt_test_model

    await model.delete_all()

    parent = await model.create(name="Parent")
    child = await model.create(parent_id=parent.pk, name="Child")
    grandchild = await model.create(parent_id=child.pk, name="GrandChild")

    await assert_mptt_valid(grandchild, parent_id=child.pk, level=2, tree_id=1, lft=3, rght=4)
    await assert_mptt_valid(child, parent_id=parent.pk, level=1, tree_id=1, lft=2, rght=5)
    await assert_mptt_valid(parent, parent_id=None, level=0, tree_id=1, lft=1, rght=6)


@pytest.mark.django_db
async def test_create_complex_tree(app, aiohttp_client):
    await aiohttp_client(app)
    model = app.m.mpttt_test_model

    await model.delete_all()

    # Create tree
    food = await model.create(name="Food")
    drinks = await model.create(name="Drinks")
    fruit = await model.create(parent_id=food.pk, name="Fruit")
    meat = await model.create(parent_id=food.pk, name="Meat")
    cola = await model.create(parent_id=drinks.pk, name="Cola")
    beef = await model.create(parent_id=meat.pk, name="Beef")
    pork = await model.create(parent_id=meat.pk, name="Pork")
    red = await model.create(parent_id=fruit.pk, name="Red")
    yellow = await model.create(parent_id=fruit.pk, name="Yellow")
    cherry = await model.create(parent_id=red.pk, name="Cherry")
    banana = await model.create(parent_id=yellow.pk, name="Banana")

    # Make index checks
    await assert_mptt_valid(drinks, parent_id=None, level=0, tree_id=2, lft=1, rght=4)
    await assert_mptt_valid(cola, parent_id=drinks.pk, level=1, tree_id=drinks.tree_id, lft=2, rght=3)
    await assert_mptt_valid(banana, parent_id=yellow.pk, level=3, tree_id=food.tree_id, lft=8, rght=9)
    await assert_mptt_valid(fruit, parent_id=food.pk, level=1, tree_id=food.tree_id, lft=2, rght=11)
    await assert_mptt_valid(food, parent_id=None, level=0, tree_id=1, lft=1, rght=18)

    # Refetch nodes
    food = await model.get_one(model.table.c.name == food.name)
    fruit = await model.get_one(model.table.c.name == fruit.name)
    meat = await model.get_one(model.table.c.name == meat.name)
    banana = await model.get_one(model.table.c.name == banana.name)
    drinks = await model.get_one(model.table.c.name == drinks.name)
    cola = await model.get_one(model.table.c.name == cola.name)

    # Make relation checks

    # is_root_node
    assert not cola.is_root_node()
    assert food.is_root_node()

    # is_child_node
    assert cola.is_child_node()
    assert not food.is_child_node()

    # is_leaf_node
    assert cola.is_leaf_node()
    assert not food.is_leaf_node()

    # get_root()
    node = await cola.get_root()
    assert node.pk == drinks.pk
    node = await banana.get_root()
    assert node.pk == food.pk

    # get_descendant_count
    assert cola.get_descendant_count() == 0
    assert drinks.get_descendant_count() == 1
    assert food.get_descendant_count() == 8

    # get_children
    assert (await cola.get_children()) == []
    assert_nodes_ids(await food.get_children(), [fruit.pk, meat.pk])

    # get_descendants
    assert_nodes_ids(await cola.get_descendants(), [])
    assert_nodes_ids(await cola.get_descendants(include_self=True), [cola.pk])
    assert_nodes_ids(
        await food.get_descendants(),
        [fruit.pk, meat.pk, beef.pk, pork.pk, red.pk, yellow.pk, banana.pk, cherry.pk]
    )

    # get_ancestors
    assert_nodes_ids(await food.get_ancestors(), [])
    assert_nodes_ids(await food.get_ancestors(include_self=True), [food.pk])
    assert_nodes_ids(await banana.get_ancestors(), [food.pk, fruit.pk, yellow.pk])

    # get_family
    assert_nodes_ids(
        await drinks.get_family(), [drinks.pk, cola.pk])
    assert_nodes_ids(await fruit.get_family(), [food.pk, fruit.pk, red.pk, yellow.pk, banana.pk, cherry.pk])

    # get_next_sibling
    sibling = await drinks.get_next_sibling()
    assert sibling is None
    sibling = await food.get_next_sibling()
    assert sibling is None
    sibling = await fruit.get_next_sibling()
    assert sibling.pk == meat.pk
    sibling = await food.get_next_sibling()
    assert sibling is None
    sibling = await cola.get_next_sibling()
    assert sibling is None

    # get_previous_sibling
    sibling = await drinks.get_previous_sibling()
    assert sibling is None
    sibling = await food.get_previous_sibling()
    assert sibling is None
    sibling = await drinks.get_previous_sibling()
    assert sibling is None
    sibling = await cola.get_previous_sibling()
    assert sibling is None
    sibling = await meat.get_previous_sibling()
    assert sibling.pk == fruit.pk
    sibling = await fruit.get_previous_sibling()
    assert sibling is None

    # get_siblings
    assert_nodes_ids(await cola.get_siblings(), [])
    assert_nodes_ids(await cola.get_siblings(include_self=True), [cola.pk])
    assert_nodes_ids(await drinks.get_siblings(), [])
    assert_nodes_ids(await food.get_siblings(), [])
    assert_nodes_ids(await fruit.get_siblings(), [meat.pk])
    assert_nodes_ids(await fruit.get_siblings(include_self=True), [meat.pk, fruit.pk])
