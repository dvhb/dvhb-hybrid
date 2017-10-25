import functools
import itertools
import json
import logging
import uuid
from abc import ABCMeta
from operator import and_

import sqlalchemy as sa
from aiohttp.web import Request
from functools import reduce
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.sql.elements import ClauseElement
from sqlalchemy import func

from . import utils, exceptions, aviews, sql_literals


class ConnectionLogger:
    logger = logging.getLogger('common.db')

    def __init__(self, connection):
        self._connection = connection

    def log(self, sql):
        if not self.logger.hasHandlers():
            return
        elif isinstance(sql, str):
            s = sql
        else:
            s = sql.compile(
                dialect=sql_literals.LiteralDialect(),
                compile_kwargs={"literal_binds": True},
            )
        self.logger.debug(s)

    def execute(self, sql, *args, **kwargs):
        self.log(sql)
        return self._connection.execute(sql, *args, **kwargs)

    def scalar(self, sql, *args, **kwargs):
        self.log(sql)
        return self._connection.scalar(sql, *args, **kwargs)


def get_app_from_parameters(*args, **kwargs):
    app = None
    if kwargs.get('request') is not None:
        app = kwargs['request'].app
    elif args and (isinstance(args[0], (MetaModel, Model, Request)) or hasattr(args[0], 'app')):
        app = args[0].app
    return app


def method_connect_once(arg):
    def with_arg(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if kwargs.get('connection') is None:
                app = get_app_from_parameters(*args, **kwargs)
                async with app['db'].acquire() as connection:
                    kwargs['connection'] = connection
                    return await func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)
        return wrapper

    if not callable(arg):
        return with_arg
    return with_arg(arg)


def method_redis_once(arg):
    redis = 'redis'

    def with_arg(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if kwargs.get(redis) is None:
                app = get_app_from_parameters(*args, **kwargs)
                async with app[redis].get() as connection:
                    kwargs[redis] = connection
                    return await func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)
        return wrapper

    if not callable(arg):
        redis = arg
        return with_arg

    return with_arg(arg)


class MetaModel(ABCMeta):
    def __new__(mcls, name, bases, namespace):
        cls = ABCMeta.__new__(mcls, name, bases, namespace)
        name = utils.convert_class_name(name)
        cls.models[name] = cls
        return cls


class Model(dict, metaclass=MetaModel):
    models = {}
    app = None
    primary_key = 'id'
    validators = ()  # Validators for data
    update_validators = ()  # Validators to validate object and data before update
    fields_permanent = ()  # Fields need to be saved
    fields_readonly = ()
    fields_list = ()
    fields_one = None

    @classmethod
    def factory(cls, app):
        return type(cls.__name__, (cls,), {'app': app})

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
    def _where(cls, args):
        if not args:
            raise ValueError('Where where?')
        elif isinstance(args[0], (int, str, uuid.UUID)):
            first, *tail = args
            args = [cls.table.c[cls.primary_key] == first]
            args.extend(tail)
        return reduce(and_, args),

    @classmethod
    def to_column(cls, fields):
        t = cls.table.c
        result = []
        for f in fields:
            if isinstance(f, str):
                f = getattr(t, f)
            result.append(f)
        return result

    @classmethod
    def set_defaults(cls, data: dict):
        pass

    @classmethod
    async def _get_one(cls, *args, connection=None, fields=None):
        args = cls._where(args)
        if fields:
            fields = cls.to_column(fields)
        elif cls.fields_one:
            fields = cls.to_column(cls.fields_one)

        if fields:
            sql = sa.select(fields).select_from(cls.table)
        else:
            sql = cls.table.select()

        result = await connection.execute(sql.where(*args))
        return await result.first()

    @classmethod
    @method_connect_once
    async def get_one(cls, *args, connection=None, fields=None, silent=False):
        """
        Extract by id
        """
        r = await cls._get_one(*args, connection=connection, fields=fields)
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
                *self._where([self.pk]),
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

        result = await connection.execute(sql)
        l = []
        async for row in result:
            l.append(cls(**row))
        return l

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
        l = await cls.get_list(
            *where, connection=connection,
            sort=sort, fields=fields)
        return {i.pk: i for i in l}

    @classmethod
    def get_table_from_django(cls, model, *jsonb, **field_type):
        options = model._meta
        fields = []
        for f in options.get_fields():
            i = f.name
            if i in jsonb:
                fields.append((i, JSONB))
            elif i in field_type:
                fields.append((i, field_type[i]))
            elif f.many_to_one:
                fields.append((f.column,))
            elif f.related_model is not None:
                continue
            else:
                fields.append((i,))
        return sa.table(options.db_table, *[sa.column(*f) for f in fields])

    @classmethod
    @method_connect_once
    async def _pg_scalar(cls, sql, connection=None):
        return await connection.scalar(sql)

    @classmethod
    @method_redis_once
    async def get_count(cls, *args, postfix=None, connection=None, redis=None, expire=180):
        """
        Extract query size
        """
        sql = cls.table.count()

        if args:
            sql = sql.where(reduce(and_, args))

        if not postfix:
            postfix = utils.get_hash(
                str(sql.compile(compile_kwargs={"literal_binds": True})))

        key = cls.app.name + ':count:' if cls.app and hasattr(cls.app, 'name') else 'count:'
        key += postfix

        count = await redis.get(key)
        if count is not None:
            return int(count)

        count = await cls._pg_scalar(sql=sql, connection=connection)
        await redis.set(key, count)
        await redis.expire(key, expire)

        return count

    @classmethod
    @method_connect_once
    @method_redis_once
    async def get_sum(cls, column, where, postfix=None, delay=0,
                      connection=None, redis=None):
        """Calculates sum"""
        sql = sa.select([func.sum(cls.table.c[column])]).where(where)

        if not postfix:
            postfix = utils.get_hash(
                str(sql.compile(compile_kwargs={"literal_binds": True})))

        key = cls.app.name + ':aggregate:sum:' if cls.app and hasattr(cls.app, 'name') else 'aggregate:sum:'
        key += postfix

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
        uid = await connection.scalar(
            cls.table.insert().returning(pk).values(kwargs))
        kwargs[cls.primary_key] = uid
        return cls(**kwargs)

    @classmethod
    @method_connect_once
    async def create_many(cls, objects, connection=None):
        """Inserts many objects"""
        # aiopg doesn't support executemany so create object via cycle
        result = []
        for obj in objects:
            cls.set_defaults(obj)
            result.append(
                await cls.create(**obj, connection=connection)
            )
        return result

    @method_connect_once
    async def save(self, *, fields=None, connection):
        pk_field = self.table.c[self.primary_key]
        self.set_defaults(self)
        if self.primary_key in self:
            saved = await self._get_one(self.pk, connection=connection)
        else:
            saved = False
        if not saved:
            pk = await connection.scalar(
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
        pk = await connection.scalar(
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

        await connection.scalar(
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

        await connection.execute(
            t.delete().where(*where))

    @method_connect_once
    async def delete(self, connection=None):
        pk_field = self.table.c[self.primary_key]
        await connection.execute(self.table.delete().where(pk_field == self.pk))

    @classmethod
    @method_connect_once
    async def get_or_create(cls, *args, defaults=None, connection):
        pk_field = getattr(cls.table.c, cls.primary_key)
        if args:
            pass
        elif cls.primary_key in defaults:
            args = (defaults[cls.primary_key],)

        if args:
            saved = await cls._get_one(*args, connection=connection)
            if saved:
                return saved, False

        pk = await connection.scalar(
            cls.table.insert().returning(pk_field).values(defaults))
        obj = cls(**defaults)
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


class AppModels:
    """
    Class to managing all models of application
    """
    def __init__(self, app):
        self.app = app

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        return KeyError(item)

    def __getattr__(self, item):
        if item in Model.models:
            sub_class = Model.models[item].factory(self.app)
            setattr(self, item, sub_class)
            return sub_class
        raise AttributeError(item)

    @staticmethod
    def import_all_models(apps_path):
        """Imports all the models from apps_path"""
        utils.import_module_from_all_apps(apps_path, 'amodels')

    @staticmethod
    def import_all_models_from_packages(package):
        """Import all the models from package"""
        utils.import_modules_from_packages(package, 'amodels')
