import itertools
import json
import uuid
from abc import ABCMeta
from functools import reduce
from operator import and_
from typing import Any, Dict

import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.elements import ClauseElement


try:
    from modeltranslation import translator as dtrans
except ImportError:
    dtrans = None


from .. import aviews, exceptions, utils
from .decorators import method_connect_once


CACHE_CATEGORY_COUNT = 'count'
CACHE_CATEGORY_SUM = 'aggregate:sum'


class MetaModel(ABCMeta):
    def __new__(mcls, name, bases, namespace):
        cls = ABCMeta.__new__(mcls, name, bases, namespace)
        name = utils.convert_class_name(name)
        cls.models[name] = cls
        return cls


class Model(dict, metaclass=MetaModel):
    models: Dict[str, Any] = {}
    app = None
    primary_key = 'id'
    validators = ()  # Validators for data
    update_validators = ()  # Validators to validate object and data before update
    fields_permanent = ()  # Fields need to be saved
    fields_readonly = ()
    fields_list = ()
    fields_one = None
    fields_localized = None

    @classmethod
    def factory(cls, app):
        return type(cls.__name__, (cls,), {'app': app})

    @classmethod
    def get_cache_key(cls, *args):
        parts = []
        if hasattr(cls.app, 'name'):
            parts.append(cls.app.name)
        else:
            parts.append(cls.app.__class__.__module__)
        parts.append(cls.__name__)
        parts.extend(args)
        return ':'.join(parts)

    def copy_object(self):
        cls = type(self)
        obj = cls(
            (n, v)
            for n, v in dict.items(self)
            if not isinstance(v, ClauseElement))
        return obj

    def pretty(self):
        return json.dumps(self, indent=3, cls=aviews.JsonEncoder)

    @property
    def pk(self):
        return self.get(self.primary_key)

    @pk.setter
    def pk(self, value):
        self[self.primary_key] = value

    def __getattr__(self, item):
        if item in self:
            return self[item]
        return getattr(super(), item)

    def __setattr__(self, key, value):
        if key == 'pk':
            key = self.primary_key
        self[key] = value

    @classmethod
    def _where(cls, args, kwargs=None):
        c = cls.table.c
        if not args and not kwargs:
            raise ValueError('Where where?')
        elif args and isinstance(args[0], (int, str, uuid.UUID)):
            first, *tail = args
            args = [c[cls.primary_key] == first]
            args.extend(tail)
        if kwargs:
            args = args or []
            for k, v in kwargs.items():
                if k == 'pk':
                    k = cls.primary_key
                args.append(c[k] == v)
        return reduce(and_, args),

    @classmethod
    def to_column(cls, fields):
        t = cls.table.c
        result = []
        for f in fields:
            if isinstance(f, str):
                # table.c returns an instance of ColumnCollection
                # and it has __getitem__ method to get column by it name.
                f = t[f]
            result.append(f)
        return result

    @classmethod
    def set_defaults(cls, data: dict):
        pass

    @classmethod
    async def _get_one(cls, *args, connection=None, fields=None, **kwargs):
        if args or kwargs:
            args = cls._where(args, kwargs)

        if fields:
            fields = cls.to_column(fields)
        elif cls.fields_one:
            fields = cls.to_column(cls.fields_one)

        if fields:
            sql = sa.select(fields).select_from(cls.table)
        else:
            sql = cls.table.select()

        if args:
            sql = sql.where(*args)

        return await connection.fetchrow(sql)

    @classmethod
    @method_connect_once
    async def get_one(cls, *args, connection=None, fields=None, silent=False, **kwargs):
        """
        Extract by id
        """
        r = await cls._get_one(*args, connection=connection, fields=fields, **kwargs)
        if r:
            return cls(**r)
        elif not silent:
            raise exceptions.NotFound()

    @method_connect_once
    async def load_fields(self, *fields, connection, force_update=False):
        fields = set(fields)
        if force_update is False:
            fields = fields - set(self)
        elif isinstance(force_update, (list, tuple)):
            fields = fields.union(force_update)

        if fields:
            r = await self._get_one(
                self.pk,
                connection=connection,
                fields=fields)
            dict.update(self, r)

    @classmethod
    @method_connect_once
    async def get_list(cls, *args, connection, fields=None,
                       offset=None, limit=None, sort=None,
                       select_from=None):
        """Extract list"""
        if fields:
            fields = cls.to_column(fields)
        elif cls.fields_list:
            fields = cls.to_column(cls.fields_list)

        if fields:
            sql = sa.select(fields).select_from(cls.table)
        else:
            sql = cls.table.select()

        for i in select_from or ():
            sql = sql.select_from(i)

        if args and args[0] is not None:
            sql = sql.where(reduce(and_, args))

        if offset is not None:
            sql = sql.offset(offset)

        if limit is not None:
            sql = sql.limit(limit)

        if isinstance(sort, str):
            sql = sql.order_by(sort)
        elif sort:
            sql = sql.order_by(*sort)

        result = await connection.fetch(sql)
        return [cls(**row) for row in result]

    @classmethod
    @method_connect_once
    async def get_dict(cls, *where_and, connection=None,
                       fields=None, sort=None, **kwargs):
        where = []
        if where_and:
            if isinstance(where_and[0], (list, tuple, str, int)):
                v, *where_and = where_and
                kwargs[cls.primary_key] = v
        for k, v in kwargs.items():
            if isinstance(v, (list, tuple)):
                if v:
                    where.append(cls.table.c[k].in_(v))
            else:
                where.append(cls.table.c[k] == v)

        where.extend(where_and)
        if where:
            where = (reduce(and_, where),)
        else:
            where = ()
        if not fields:
            fields = None
        elif cls.primary_key not in fields:
            fields.append(cls.primary_key)
        items = await cls.get_list(*where, connection=connection, sort=sort, fields=fields)
        return {i.pk: i for i in items}

    @classmethod
    def get_table_from_django(cls, model, *jsonb, **field_type):
        """Deprecated, use @derive_from_django instead"""
        from .convert import convert_model
        for i in jsonb:
            field_type[i] = JSONB
        table, _ = convert_model(model, **field_type)
        return table

    @classmethod
    @method_connect_once
    async def _pg_scalar(cls, sql, connection=None):
        return await connection.fetchval(sql)

    @classmethod
    async def get_count(cls, *args, postfix=None, connection=None, expire=180):
        """
        Extract query size
        """
        sql = cls.table.count()

        if args:
            sql = sql.where(reduce(and_, args))

        async def real_count():
            return await cls._pg_scalar(sql=sql, connection=connection)

        if expire == 0:
            return await real_count()

        if not postfix:
            postfix = _hash_stmt(sql)

        key = cls.get_cache_key(CACHE_CATEGORY_COUNT, postfix)

        redis = cls.app.redis
        count = await redis.get(key)
        if count is not None:
            return int(count)

        count = await real_count()
        await redis.set(key, count)
        await redis.expire(key, expire)

        return count

    @classmethod
    @method_connect_once
    async def get_sum(cls, column, where, postfix=None, delay=0, connection=None):
        """Calculates sum"""
        sql = sa.select([func.sum(cls.table.c[column])]).where(where)

        if not postfix:
            postfix = _hash_stmt(sql)

        key = cls.get_cache_key(CACHE_CATEGORY_SUM, postfix)

        redis = cls.app.redis
        if delay:
            count = await redis.get(key)
            if count is not None:
                return int(count)

        count = await cls._pg_scalar(sql=sql, connection=connection)

        if count is None:
            count = 0
        elif delay:
            await redis.set(key, count)
            await redis.expire(key, delay)

        return count

    @classmethod
    @method_connect_once
    async def create(cls, *, connection, **kwargs):
        """Inserts new object"""
        pk = cls.table.c[cls.primary_key]
        cls.set_defaults(kwargs)
        uid = await connection.fetchval(
            cls.table.insert().returning(pk).values(kwargs))
        kwargs[cls.primary_key] = uid
        return cls(**kwargs)

    @classmethod
    @method_connect_once
    async def create_many(cls, objects, connection=None, returning=True):
        """Inserts many objects"""
        pk = cls.table.c[cls.primary_key]
        sql = cls.table.insert()
        if returning:
            sql = sql.returning(pk)
        for obj in objects:
            cls.set_defaults(obj)
        sql = sql.values(objects)
        if returning:
            result = await connection.fetch(sql)
            for pk, obj in zip(result, objects):
                obj[cls.primary_key] = pk[cls.primary_key]
            return [cls(**obj) for obj in objects]
        else:
            await connection.execute(sql)

    @method_connect_once
    async def save(self, *, fields=None, connection):
        pk_field = self.table.c[self.primary_key]
        self.set_defaults(self)
        if self.primary_key in self:
            saved = await self._get_one(self.pk, connection=connection)
        else:
            saved = False
        if not saved:
            pk = await connection.fetchval(
                self.table.insert().returning(pk_field).values(self))
            self[self.primary_key] = pk
            return pk
        if fields:
            fields = list(itertools.chain(fields, self.fields_permanent))
            values = {k: v for k, v in self.items()
                      if k in fields}
        elif self.fields_readonly:
            values = {k: v for k, v in self.items()
                      if k not in self.fields_readonly}
        else:
            values = self
        pk = await connection.fetchval(
            self.table.update()
            .where(pk_field == self.pk)
            .returning(pk_field)
            .values(values)
        )
        assert self.pk == pk

        return pk

    @method_connect_once
    async def update_increment(self, connection=None, **kwargs):
        t = self.table

        dict_update = {
            t.c[field]: t.c[field] + value
            for field, value in kwargs.items()
        }

        await connection.execute(
            t.update().where(
                t.c[self.primary_key] == self.pk
            ).values(dict_update))

    @classmethod
    @method_connect_once
    async def update_fields(cls, where, connection=None, **kwargs):
        t = cls.table

        dict_update = {
            t.c[field]: value
            for field, value in kwargs.items()
        }

        await connection.execute(
            t.update().
            where(where).
            values(dict_update))

    @method_connect_once
    async def update_json(self, *args, connection=None, **kwargs):
        t = self.table
        if args:
            if len(args) > 1 and not kwargs:
                field, *path, value = args
            else:
                field, *path = args
                value = kwargs
            for p in reversed(path):
                value = {p: value}
            kwargs = {field: value}
        elif not kwargs:
            raise ValueError('Need args or kwargs')

        await connection.fetchval(
            t.update().where(
                t.c[self.primary_key] == self.pk
            ).values(
                {
                    t.c[field]: sa.func.coalesce(
                        t.c[field], sa.cast({}, JSONB)
                    ) + sa.cast(value, JSONB)
                    for field, value in kwargs.items()
                }
            ).returning(t.c[self.primary_key]))

    @classmethod
    @method_connect_once
    async def delete_where(cls, *where, connection=None):
        t = cls.table

        where = cls._where(where)

        await connection.fetchval(
            t.delete().where(*where))

    @method_connect_once
    async def delete(self, connection=None):
        async with connection.transaction():
            await self._delete_relationships(connection=connection)
            pk_field = self.table.c[self.primary_key]
            await connection.fetchval(self.table.delete().where(pk_field == self.pk))

    @method_connect_once
    async def _delete_relationships(self, connection=None):
        if not hasattr(self, 'relationships'):
            return
        for k in self.relationships:
            relation = getattr(self, k, None)
            if relation is None:
                raise AttributeError('Relationship {} for {} is not found'.format(
                    k,
                    type(self).__name__
                ))
            if relation.is_many_to_many:
                await relation.delete_by_source(self.pk, connection=connection)
            elif relation.is_one_to_many:
                await relation.delete_related(self.pk, connection=connection)
            elif relation.is_one_to_one:
                await relation.delete_related(self.pk, connection=connection)

    @classmethod
    @method_connect_once
    async def get_or_create(cls, *args, defaults=None, connection, **kwargs):
        if args or kwargs:
            pass
        elif cls.primary_key in defaults:
            args = (defaults[cls.primary_key],)

        if args or kwargs:
            saved = await cls._get_one(
                *args, connection=connection, **kwargs)
            if saved:
                return cls(**saved), False

        if defaults:
            kwargs.update(defaults)
        cls.set_defaults(kwargs)

        pk = await connection.fetchval(
            cls.table.insert().returning(
                cls.table.c[cls.primary_key]
            ).values(kwargs))
        obj = cls(**kwargs)
        obj.pk = pk
        return obj, True

    @classmethod
    def validate(cls, data, to_class=True, default_validator=True):
        """Returns valid object or exception"""
        validators = cls.validators
        if not validators and default_validator:
            validators = [cls.default_validator]
        for validator in validators:
            data = validator(data)
        return cls(**data) if to_class else data

    @classmethod
    def default_validator(cls, data):
        return {f: data.get(f) for f in cls.table.columns.keys()}

    @method_connect_once
    async def validate_and_save(self, data, connection=None):
        """
        Method performs default validations, update validations and save object.
        """
        # Validate data using user defined validators
        data = self.validate(data, to_class=False, default_validator=False)
        for v in self.update_validators:
            data = v(self, data)
        # Do not allow object update for empty data to avoid extra save.
        if data:
            self.update(data)
            return await self.save(fields=data.keys(), connection=connection)

    @staticmethod
    def get_fields_localized_from_django(django_model):
        if dtrans:
            try:
                return list(dtrans.translator.get_options_for_model(django_model).fields.keys())
            except dtrans.NotRegistered:
                pass

    @classmethod
    def localize(cls, obj, locale):
        if not cls.fields_localized:
            return
        for field in cls.fields_localized:
            if field not in obj:
                continue
            value = obj.get('{}_{}'.format(field, locale))
            if value:
                obj[field] = value


def _hash_stmt(stmt):
    compiled = stmt.compile()
    msg = compiled.string + repr(compiled.params)
    return utils.get_hash(msg)
