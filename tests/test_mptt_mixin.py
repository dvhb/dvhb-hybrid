import pytest
from dvhb_hybrid import utils
from dvhb_hybrid.amodels import Model, MPTTMixin, derive_from_django

from . import models


@derive_from_django(models.MPTTTestModel)
class MPTTTestModel(MPTTMixin, Model):
    order_insertion_by = ['created_at']

    @classmethod
    def set_defaults(cls, data: dict):
        data.setdefault('created_at', utils.now())


@pytest.fixture
def create_test_model_instance(app):
    async def wrapper(**kwargs):
        nonlocal app
        model = MPTTTestModel.factory(app)
        return await model.create(**kwargs)
    return wrapper


@pytest.fixture
def get_test_model_instance(app):
    async def wrapper(name):
        nonlocal app
        model = MPTTTestModel.factory(app)
        return await model.get_one(model.table.c.name == name)
    return wrapper


def assert_mptt_valid(node, **kwargs):
    for k in kwargs:
        assert node[k] == kwargs[k], "wrong {}: expected {}, got {}".format(k, kwargs[k], node[k])


def assert_nodes_ids(items, ids, pk='id'):
    assert sorted(map(lambda i: i[pk], items)) == sorted(ids)


@pytest.mark.skip
@pytest.mark.django_db(transaction=True)
async def test_create_one_top(create_test_model_instance):
    top1 = await create_test_model_instance(name="Top1")
    assert top1['id']
    assert_mptt_valid(top1, parent_id=None, level=0, tree_id=0, lft=1, rght=2)


@pytest.mark.skip
@pytest.mark.django_db(transaction=True)
async def test_create_two_tops(create_test_model_instance):
    top1 = await create_test_model_instance(name="Top1")
    top2 = await create_test_model_instance(name="Top2")
    assert_mptt_valid(top1, parent_id=None, level=0, tree_id=0, lft=1, rght=2)
    assert_mptt_valid(top2, parent_id=None, level=0, tree_id=1, lft=3, rght=4)


@pytest.mark.skip
@pytest.mark.django_db(transaction=True)
async def test_create_parent_and_child(create_test_model_instance, get_test_model_instance):
    parent = await create_test_model_instance(name="Parent")
    child = await create_test_model_instance(parent_id=parent.pk, name="Child")
    parent = await get_test_model_instance(parent.name)
    assert_mptt_valid(parent, parent_id=None, level=0, tree_id=0, lft=1, rght=4)
    assert_mptt_valid(child, parent_id=parent.pk, level=1, tree_id=0, lft=2, rght=3)


@pytest.mark.skip
@pytest.mark.django_db(transaction=True)
async def test_create_complex_tree(create_test_model_instance, get_test_model_instance):
    # Create tree
    food = await create_test_model_instance(name="Food")
    drinks = await create_test_model_instance(name="Drinks")
    fruit = await create_test_model_instance(parent_id=food.pk, name="Fruit")
    meat = await create_test_model_instance(parent_id=food.pk, name="Meat")
    cola = await create_test_model_instance(parent_id=drinks.pk, name="Cola")
    beef = await create_test_model_instance(parent_id=meat.pk, name="Beef")
    pork = await create_test_model_instance(parent_id=meat.pk, name="Pork")
    red = await create_test_model_instance(parent_id=fruit.pk, name="Red")
    yellow = await create_test_model_instance(parent_id=fruit.pk, name="Yellow")
    cherry = await create_test_model_instance(parent_id=red.pk, name="Cherry")
    banana = await create_test_model_instance(parent_id=yellow.pk, name="Banana")

    # Refetch nodes
    food = await get_test_model_instance(food.name)
    fruit = await get_test_model_instance(fruit.name)
    meat = await get_test_model_instance(meat.name)
    banana = await get_test_model_instance(banana.name)
    drinks = await get_test_model_instance(drinks.name)
    cola = await get_test_model_instance(cola.name)

    # Make index checks
    assert_mptt_valid(food, parent_id=None, level=0, tree_id=0, lft=1, rght=18)
    assert_mptt_valid(banana, parent_id=yellow.pk, level=3, tree_id=food.tree_id, lft=8, rght=9)
    assert_mptt_valid(drinks, parent_id=None, level=0, tree_id=1, lft=19, rght=22)
    assert_mptt_valid(cola, parent_id=drinks.pk, level=1, tree_id=drinks.tree_id, lft=20, rght=21)

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
    assert_nodes_ids(
        await food.get_children(), [fruit.pk, meat.pk])

    # get_descendants
    assert_nodes_ids(
        await cola.get_descendants(), [])
    assert_nodes_ids(
        await cola.get_descendants(include_self=True), [cola.pk])
    assert_nodes_ids(
        await food.get_descendants(),
        [fruit.pk, meat.pk, beef.pk, pork.pk, red.pk, yellow.pk, banana.pk, cherry.pk])

    # get_ancestors
    assert_nodes_ids(
        await food.get_ancestors(), [])
    assert_nodes_ids(
        await food.get_ancestors(include_self=True), [food.pk])
    assert_nodes_ids(
        await banana.get_ancestors(), [food.pk, fruit.pk, yellow.pk])

    # get_family
    assert_nodes_ids(
        await drinks.get_family(), [drinks.pk, cola.pk])
    assert_nodes_ids(
        await fruit.get_family(),
        [food.pk, fruit.pk, red.pk, yellow.pk, banana.pk, cherry.pk])

    # get_next_sibling
    sibling = await food.get_next_sibling()
    assert sibling.pk == drinks.pk
    sibling = await fruit.get_next_sibling()
    assert sibling.pk == meat.pk
    sibling = await drinks.get_next_sibling()
    assert sibling is None
    sibling = await cola.get_next_sibling()
    assert sibling is None

    # get_previous_sibling
    sibling = await drinks.get_previous_sibling()
    assert sibling.pk == food.pk
    sibling = await food.get_previous_sibling()
    assert sibling is None
    sibling = await cola.get_previous_sibling()
    assert sibling is None
    sibling = await meat.get_previous_sibling()
    assert sibling.pk == fruit.pk
    sibling = await fruit.get_previous_sibling()
    assert sibling is None

    # get_siblings
    assert_nodes_ids(
        await cola.get_siblings(), [])
    assert_nodes_ids(
        await cola.get_siblings(include_self=True), [cola.pk])
    assert_nodes_ids(
        await food.get_siblings(), [drinks.pk])
    assert_nodes_ids(
        await fruit.get_siblings(), [meat.pk])
    assert_nodes_ids(
        await fruit.get_siblings(include_self=True), [meat.pk, fruit.pk])
