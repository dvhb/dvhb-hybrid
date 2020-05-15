from collections import defaultdict

from django.db.models import (
    CASCADE,
    PROTECT,
    SET_NULL,
    ManyToManyField,
    ManyToManyRel,
    ManyToOneRel,
    OneToOneField,
    OneToOneRel,
)

from .model import Model
from .decorators import method_connect_once


def _generate_model_name(dj_model):
    return '_'.join((
        dj_model.__module__.replace('.', '_'),
        dj_model.__name__
    ))


def _generate_model(class_name, dj_model):
    from .convert import derive_from_django

    if class_name in Model.models:
        return Model.models[class_name]

    amodel = type(class_name, (Model,), {})
    amodel = derive_from_django(dj_model)(amodel)

    return amodel


def _obtain_model(app, dj_model):
    class_name = _generate_model_name(dj_model)
    if not hasattr(app.m, class_name):
        amodel = _generate_model(class_name, dj_model)
        amodel = amodel.factory(app)
        setattr(app.m, class_name, amodel)
    return getattr(app.m, class_name)


class RelationshipProperty:
    """
    Descriptor used to provide access to a relationship

    :param factory: A callable wich takes an app instance and returns a relationship instance
    """
    def __init__(self, factory):
        self._factory = factory

    def __get__(self, instance, owner=None):
        # we do not cache relationship instance
        # because app instance can be changed
        # and this will lead to some bugs such as 'pool is closed error'
        app = None
        model = instance if instance is not None else owner
        if model is not None:
            app = getattr(model, 'app', None)
        if app is None:
            raise ValueError('Could not obtain app instance from a model for the relationship')
        return self._factory(app)

    @classmethod
    def from_django(cls, field):
        """
        Creates a descriptor from then given django model field
        """
        if not getattr(field, 'is_relation', False):
            raise RelationshipException('{!r} is not a relationship'.format(field))
        if field.many_to_many:
            factory = ManyToManyFactory
        elif field.many_to_one:
            factory = ManyToOneFactory
        elif field.one_to_many:
            factory = OneToManyFactory
        elif field.one_to_one:
            factory = OneToOneFactory
        else:
            raise RelationshipException('Unknown relationship type: {!r}'.format(field))
        return cls(factory.from_django(field))


class RelationshipException(Exception):
    pass


class ManyToManyFactory:
    def __init__(self, model, target_model, source_field, target_field):
        self.model = model
        self.target_model = target_model
        self.source_field = source_field
        self.target_field = target_field

    def __call__(self, app):
        return ManyToManyRelationship(
            app=app,
            model=_obtain_model(app, self.model),
            target_model=_obtain_model(app, self.target_model),
            source_field=self.source_field,
            target_field=self.target_field
        )

    @classmethod
    def from_django(cls, field):
        if isinstance(field, ManyToManyField):
            dj_model = field.remote_field.through
            source_field = field.m2m_column_name()
            target_field = field.m2m_reverse_name()
        elif isinstance(field, ManyToManyRel):
            dj_model = field.through
            source_field = field.remote_field.m2m_reverse_name()
            target_field = field.remote_field.m2m_column_name()
        else:
            raise RelationshipException('Unknown many to many relationship: {!r}'.format(field))
        return cls(dj_model, field.related_model, source_field, target_field)


class ManyToOneFactory:
    def __init__(self):
        pass

    def __call__(self, app):
        return ManyToOneRelationship(app)

    @classmethod
    def from_django(cls, field):
        return cls()


class OneToManyFactory:
    def __init__(self, model_to, column_to, on_delete):
        self.model_to = model_to
        self.column_to = column_to
        self.on_delete = on_delete

    def __call__(self, app):
        return OneToManyRelationship(
            app=app,
            model_to=_obtain_model(app, self.model_to),
            column_to=self.column_to,
            on_delete=self.on_delete
        )

    @classmethod
    def from_django(cls, field):
        if not isinstance(field, ManyToOneRel):
            raise RelationshipException('Unknown one to many relationship: {!r}'.format(field))
        return cls(
            model_to=field.related_model,
            column_to=field.remote_field.attname,
            on_delete=field.on_delete
        )


class OneToOneFactory:
    def __init__(self, model_from, model_to, column_from, column_to, on_delete):
        self.model_from = model_from
        self.model_to = model_to
        self.column_from = column_from
        self.column_to = column_to
        self.on_delete = on_delete

    def __call__(self, app):
        return OneToOneRelationship(
            app=app,
            model_from=_obtain_model(app, self.model_from),
            model_to=_obtain_model(app, self.model_to),
            column_from=self.column_from,
            column_to=self.column_to,
            on_delete=self.on_delete
        )

    @classmethod
    def from_django(cls, field):
        model_from = field.model
        model_to = field.related_model
        if isinstance(field, OneToOneField):
            column_from = field.attname
            column_to = model_to._meta.pk.attname
            on_delete = None
        elif isinstance(field, OneToOneRel):
            column_from = model_from._meta.pk.attname
            column_to = field.remote_field.attname
            on_delete = field.on_delete
        else:
            raise RelationshipException('Unknown one to one relationship: {!r}'.format(field))
        return cls(model_from, model_to, column_from, column_to, on_delete)


class BaseRelationship:
    @property
    def is_many_to_many(self):
        raise NotImplementedError()

    @property
    def is_many_to_one(self):
        raise NotImplementedError()

    @property
    def is_one_to_many(self):
        raise NotImplementedError()

    @property
    def is_one_to_one(self):
        raise NotImplementedError()


class ManyToManyRelationship(BaseRelationship):
    def __init__(self, app, model, target_model, source_field, target_field):
        self.app = app  # required for method_connect_once
        # Model for link (not source) table
        self.model = model
        self.target_model = target_model
        # Name of the FK to source model in the link model
        self.source_field = source_field
        # Name of the FK to target model in the link model
        self.target_field = target_field

    @property
    def is_many_to_many(self):
        return True

    @property
    def is_many_to_one(self):
        return False

    @property
    def is_one_to_many(self):
        return False

    @property
    def is_one_to_one(self):
        return False

    def _get_where_condition(self, field_name, field_id):
        col = self.model.table.c[field_name]
        if isinstance(field_id, (list, tuple, set)):
            where = col.in_(field_id)
        else:
            where = col == field_id
        return where

    def _get_source_where_condition(self, source):
        return self._get_where_condition(self.source_field, source)

    def _get_target_where_condition(self, target):
        return self._get_where_condition(self.target_field, target)

    @method_connect_once
    async def get_links_by_source(self, source, *, connection=None):
        """
        Returns links given source model ID/IDs
        :param source: Single or list of source model ID/IDs
        :param connection: DB connection to perform operation with
        """
        where = self._get_source_where_condition(source)
        return await self.model.get_list(where, connection=connection)

    @method_connect_once
    async def get_links_by_target(self, target, *, connection=None):
        """
        Returns links given target model ID/IDs
        :param target: Single or list of target model ID/IDs
        :param connection: DB connection to perform operation with
        """
        where = self._get_target_where_condition(target)
        return await self.model.get_list(where, connection=connection)

    @method_connect_once
    async def _get_targets(self, links, *, as_dict=False, connection=None):
        target_ids = [i[self.target_field] for i in links]
        pk_name = self.target_model.primary_key
        pk = self.target_model.table.c[pk_name]
        targets = await self.target_model.get_list(pk.in_(target_ids), connection=connection)
        if as_dict:
            targets = {i[pk_name]: i for i in targets}
        return targets

    @method_connect_once
    async def get_for_one(self, source, *, connection=None):
        links = await self.get_links_by_source(source, connection=connection)
        return await self._get_targets(links, connection=connection)

    @method_connect_once
    async def get_for_list(self, source, *, connection=None):
        links = await self.get_links_by_source(source, connection=connection)
        targets = await self._get_targets(links, as_dict=True, connection=connection)
        result = defaultdict(list)
        for i in links:
            source_key = i[self.source_field]
            target_key = i[self.target_field]
            result[source_key].append(targets[target_key])
        return dict(result)

    async def delete(self, source, *, connection=None):
        """
        For backward compatibility
        """

        await self.delete_by_source(source, connection=connection)

    @method_connect_once
    async def delete_by_source(self, source, *, connection=None):
        """
        Deletes links given source model ID/IDs
        :param source: Single or list of source model ID/IDs
        :param connection: DB connection to perform operation with
        """

        where = self._get_source_where_condition(source)
        await self.model.delete_where(where, connection=connection)

    @method_connect_once
    async def delete_by_target(self, target, *, connection=None):
        """
        Deletes links given target model ID/IDs
        :param target: Single or list of target model ID/IDs
        :param connection: DB connection to perform operation with
        """

        where = self._get_target_where_condition(target)
        await self.model.delete_where(where, connection=connection)


class ManyToOneRelationship(BaseRelationship):  # TODO: implement many to one relationship
    def __init__(self, app):
        self.app = app

    @property
    def is_many_to_many(self):
        return False

    @property
    def is_many_to_one(self):
        return True

    @property
    def is_one_to_many(self):
        return False

    @property
    def is_one_to_one(self):
        return False


class OneToManyRelationship(BaseRelationship):
    def __init__(self, app, model_to, column_to, on_delete):
        self.app = app
        self.model_to = model_to
        self._column_to = model_to.table.c[column_to]
        self._on_delete = on_delete

    @property
    def is_many_to_many(self):
        return False

    @property
    def is_many_to_one(self):
        return False

    @property
    def is_one_to_many(self):
        return True

    @property
    def is_one_to_one(self):
        return False

    @method_connect_once
    async def delete_related(self, object_id, connection=None):
        if self._on_delete is CASCADE:
            items = await self.model_to.get_list(self._column_to == object_id, connection=connection)
            for item in items:
                await item.delete(connection=connection)
        elif self._on_delete is PROTECT:
            if await self.model_to.get_count(
                self._column_to == object_id,
                expire=0,
                connection=connection
            ):
                raise RelationshipException('Could not delete {} where {}={}'.format(
                    self.model_to.__name__,
                    self._column_to.name,
                    object_id
                ))
        elif self._on_delete is SET_NULL:
            await self.model_to.update_fields(
                self._column_to == object_id,
                connection=connection,
                **{self._column_to.name: None}
            )


class OneToOneRelationship(BaseRelationship):
    def __init__(self, app, model_from, model_to, column_from, column_to, on_delete):
        self.app = app
        self.model_from = model_from
        self.model_to = model_to
        self._column_from = model_from.table.c[column_from]
        self._column_to = model_to.table.c[column_to]
        self._on_delete = on_delete

    @property
    def is_many_to_many(self):
        return False

    @property
    def is_many_to_one(self):
        return False

    @property
    def is_one_to_many(self):
        return False

    @property
    def is_one_to_one(self):
        return True

    @method_connect_once
    async def delete_related(self, object_id, connection):
        if self._on_delete is CASCADE:
            items = await self.model_to.get_list(self._column_to == object_id, connection=connection)
            for item in items:
                await item.delete(connection=connection)
        elif self._on_delete is SET_NULL:
            await self.model_to.update_fields(
                self._column_to == object_id,
                connection=connection,
                **{self.column_to.name: None},
            )
        elif self._on_delete is PROTECT:
            if await self.model_to.get_count(
                self._column_to == object_id,
                expire=0,
                connection=connection
            ):
                raise RelationshipException('Could not delete {} where {}={}'.format(
                    self.model_to.__name__,
                    self._column_to.name,
                    object_id
                ))
