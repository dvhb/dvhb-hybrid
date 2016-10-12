import functools
import itertools
import json
import logging
import uuid
from abc import ABCMeta
from typing import Iterable

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
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


def method_connect_once(func):
    @functools.wraps(func)
    async def wraper(self, *args, **kwargs):
        if kwargs.get('connection') is None:
            async with self.app.db.acquire() as connection:
                kwargs['connection'] = ConnectionLogger(connection)
                return await func(self, *args, **kwargs)
        else:
            return await func(self, *args, **kwargs)
    return wraper


def method_redis_once(arg):
    redis = 'redis'

    def with_arg(func):
        @functools.wraps(func)
        async def wraper(self, *args, **kwargs):
            if kwargs.get(redis) is None:
                async with getattr(self.app, redis).get() as connection:
                    kwargs[redis] = connection
                    return await func(self, *args, **kwargs)
            else:
                return await func(self, *args, **kwargs)
        return wraper

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
    validators = ()
    fields_permanent = ()  # Поля которые необходимо всегда сохранять
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
        if not len(args):
            raise ValueError('Where where?')
        elif isinstance(args[0], (int, str, uuid.UUID)):
            args = cls.table.c[cls.primary_key] == args[0],
        return args

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
    async def _get_one(cls, *args, connection, fields=None):
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
    async def get_one(cls, *args, connection, fields=None, silent=False):
        """
        Извлечение по id, или алхимическому условию
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
                       offset=None, limit=None, sort=None):
        """
        Извлечение списка
        """
        if fields:
            fields = cls.to_column(fields)
        elif cls.fields_list:
            fields = cls.to_column(cls.fields_list)

        if fields:
            sql = sa.select(fields).select_from(cls.table)
        else:
            sql = cls.table.select()

        if args and args[0] is not None:
            sql = sql.where(*args)

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
    async def _pg_scalar(cls, sql, connection=None):
        return await connection.scalar(sql)

    @classmethod
    @method_redis_once
    async def get_count(cls, *args, postfix=None, connection=None, redis=None):
        """
        Извлечение размера выборки
        """
        sql = cls.table.count()

        if args:
            sql = sql.where(*args)

        if not postfix:
            postfix = utils.get_hash(
                str(sql.compile(compile_kwargs={"literal_binds": True})))
        key = 'vprs:count:' + postfix

        count = await redis.get(key)
        if count is not None:
            return int(count)

        count = await cls._pg_scalar(sql=sql, connection=connection)
        await redis.set(key, count)
        await redis.expire(key, 3 * 60)

        return count

    @classmethod
    @method_connect_once
    @method_redis_once
    async def get_sum(cls, column, where, postfix=None, delay=0,
                      connection=None, redis=None):
        """
        Извлечение размера выборки
        """
        sql = sa.select([func.sum(cls.table.c[column])]).where(where)

        if not postfix:
            postfix = utils.get_hash(
                str(sql.compile(compile_kwargs={"literal_binds": True})))
        key = 'vprs:aggregate:sum:' + postfix

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
        """
        Возвращает сохраненный объект с данными
        """
        pk = cls.table.c[cls.primary_key]
        cls.set_defaults(kwargs)
        uid = await connection.scalar(
            cls.table.insert().returning(pk).values(kwargs))
        kwargs[cls.primary_key] = uid
        return cls(**kwargs)

    @method_connect_once
    async def save(self, *, fields=None, connection):
        if 'cant_save_fields' in self and self['cant_save_fields']:
            fields = [f for f in fields if f not in self['cant_save_fields']]
        pk_field = getattr(self.table.c, self.primary_key)
        self.set_defaults(self)
        if self.primary_key in self:
            saved = await self._get_one(self.pk, connection=connection)
        else:
            saved = False
        if not saved:
            pk = await connection.scalar(
                self.table.insert().returning(pk_field).values(self))
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
    async def update_json(self, connection=None, **kwargs):
        t = self.table

        # TODO сделать атомарно
        dict_update = {
            t.c[field]: sa.cast(value, JSONB)
            if field not in self or self[field] is None
            else t.c[field] + sa.cast(value, JSONB)
            for field, value in kwargs.items()
        }

        await connection.execute(
            t.update().where(
                t.c[self.primary_key] == self.pk
            ).values(dict_update))

    @classmethod
    @method_connect_once
    async def delete_where(cls, *where, connection=None):
        t = cls.table

        where = cls._where(where)

        await connection.execute(
            t.delete().where(*where))

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
    def validate(cls, data):
        """ Возвращает валидный объект или исключение
        """
        validators = cls.validators or [cls.default_validator]
        for validator in validators:
            try:
                data = validator(data)
            except voluptuous.MultipleInvalid as e:
                raise exceptions.ValidationError(
                    utils.multiple_invalid_to_errors(e))
        return cls(**data)

    @classmethod
    def default_validator(cls, data):
        return {f: data.get(f) for f in cls.table.columns.keys()}

    def data(self, fields: Iterable[str]=None) -> dict:
        """
        Возвращает данные в виде словаря
        :param fields: необязательные параметр список необходимых полей,
        если не указан, тогда будут возвращены все поля.
        :return: dict
        """
        if not fields:
            fields = self.table.columns.keys()
        return {k: self[k] for k in fields if k in self}


class AppModels:
    def __init__(self, app):
        self.app = app

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        return KeyError()

    def __getattr__(self, item):
        if item in Model.models:
            sub_class = Model.models[item].factory(self.app)
            setattr(self, item, sub_class)
            return sub_class
        raise AttributeError()

    @staticmethod
    def import_all_models(apps_path):
        """
        Импортирует все модели из приложений.
        :param apps_path: путь к директории с приложениями.
        """
        utils.import_module_from_all_apps(apps_path, 'amodels')
