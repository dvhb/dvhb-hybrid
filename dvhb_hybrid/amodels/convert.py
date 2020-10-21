import logging

import sqlalchemy as sa
import sqlalchemy.types as sa_types
from django.db.models import ForeignKey, OneToOneField
from sqlalchemy.dialects.postgresql import ARRAY as SA_ARRAY, JSONB as SA_JSONB, UUID as SA_UUID

from .. import utils
from .relations import RelationshipProperty

logger = logging.getLogger(__name__)


def Geometry(*args, **kwargs):
    return sa_types.NullType()


class FieldConverter:
    """
    Converts Django field to SQLAlchemy column clause

    .. code-block::python

        converter = FieldConverter()
        sa_column = converter.convert(field)

    """
    def __init__(self):
        self._types = {
            # Django internal type => SQLAlchemy type
            'ArrayField': SA_ARRAY,
            'AutoField': sa_types.Integer,
            'BigAutoField': sa_types.BigInteger,
            'BigIntegerField': sa_types.BigInteger,
            'BooleanField': sa_types.Boolean,
            'CharField': sa_types.String,
            'DateField': sa_types.Date,
            'DateTimeField': sa_types.DateTime,
            'DecimalField': sa_types.Numeric,
            'DurationField': sa_types.Interval,
            'FileField': sa_types.String,
            'FilePathField': sa_types.String,
            'FloatField': sa_types.Float,
            'GenericIPAddressField': sa_types.String,
            'IntegerField': sa_types.Integer,
            'JSONField': SA_JSONB,
            'NullBooleanField': sa_types.Boolean,
            'PointField': Geometry,
            'PositiveIntegerField': sa_types.Integer,
            'PositiveSmallIntegerField': sa_types.SmallInteger,
            'SlugField': sa_types.String,
            'SmallIntegerField': sa_types.SmallInteger,
            'TextField': sa_types.Text,
            'TimeField': sa_types.Time,
            'UUIDField': SA_UUID,
            # TODO: Add missing GIS fields
        }

    def _convert_type(self, dj_field, sa_type):
        kwargs = {}
        if sa_type is SA_ARRAY:
            internal_type = dj_field.base_field.get_internal_type()
            kwargs['item_type'] = self._types.get(internal_type)
            if kwargs['item_type'] is None:
                raise ConversionError(
                    'Unable convert array: '
                    'item type "%s" not found' % internal_type
                )
        elif sa_type is Geometry:
            kwargs['geometry_type'] = 'POINT'
            kwargs['srid'] = dj_field.srid
        elif sa_type is sa_types.Numeric:
            kwargs['scale'] = dj_field.decimal_places,
            kwargs['precision'] = dj_field.max_digits
        elif sa_type in (sa_types.String, sa_types.Text):
            kwargs['length'] = dj_field.max_length
        elif sa_type is SA_UUID:
            kwargs['as_uuid'] = True
        return sa_type(**kwargs)

    def convert(self, dj_field):
        result = []
        if isinstance(dj_field, (ForeignKey, OneToOneField)):
            result.append(dj_field.column)
            convert_from = dj_field.target_field
        else:
            result.append(dj_field.name)
            convert_from = dj_field
        internal_type = convert_from.get_internal_type()
        convert_to = self._types.get(internal_type)
        if convert_to is not None:
            result.append(self._convert_type(convert_from, convert_to))
        else:
            logger.info(
                'Not found corresponding '
                'SQLAlchemy type for "%s"(%r)',
                internal_type,
                dj_field
            )
        return sa.column(*result)


FIELD_CONVERTER = FieldConverter()


def convert_model(model, **field_types):
    """
    Converts Django model to SQLAlchemy table
    """
    options = model._meta
    fields = []
    rels = {}
    for f in options.get_fields(include_hidden=True):
        i = f.name
        if i in field_types:
            fields.append(sa.column(i, field_types[i]))
        elif f.is_relation:
            rel_name = _get_rel_name(f)
            rels[rel_name] = RelationshipProperty.from_django(f)
            if f.many_to_one:
                fields.append(FIELD_CONVERTER.convert(f))
            elif f.one_to_one and not f.auto_created:
                fields.append(FIELD_CONVERTER.convert(f))
        else:
            fields.append(FIELD_CONVERTER.convert(f))
    return sa.table(options.db_table, *fields), rels


def derive_from_django(dj_model, **field_types):
    def wrapper(amodel):
        table, rels = convert_model(dj_model, **field_types)
        amodel.table = table
        amodel.relationships = tuple(rels.keys())
        for k, v in rels.items():
            setattr(amodel, k, v)
        amodel.primary_key = dj_model._meta.pk.attname
        return amodel
    return wrapper


class ConversionError(Exception):
    pass


def _get_rel_name(field):
    name = field.name.replace('+', '')
    if not name:
        module_name = field.related_model.__module__.replace('.', '_')
        class_name = utils.convert_class_name(field.related_model.__name__)
        field_name = field.remote_field.name
        name = '_{}_{}_{}'.format(module_name, class_name, field_name)
    return name
