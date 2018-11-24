import logging

import sqlalchemy as sa
import sqlalchemy.types as sa_types
from django.db.models import ForeignKey, ManyToManyField, ManyToManyRel, OneToOneField
from sqlalchemy.dialects.postgresql import ARRAY as SA_ARRAY, JSONB as SA_JSONB, UUID as SA_UUID

from .model import Model
from .relations import ManyToManyRelationship
from ..utils import convert_class_name

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


def convert_m2m(field):
    if isinstance(field, ManyToManyField):
        dj_model = field.remote_field.through
        source_field = field.m2m_column_name()
        target_field = field.m2m_reverse_name()
    elif isinstance(field, ManyToManyRel):
        dj_model = field.through
        source_field = field.remote_field.m2m_reverse_name()
        target_field = field.remote_field.m2m_column_name()
    else:
        raise ConversionError('Unknown many to many field: %r' % field)

    def m2m_factory(app):
        model_name = convert_class_name(dj_model.__name__)
        if hasattr(app.m, model_name):
            # Get existing relationship model
            model = getattr(app.m, model_name)
        else:
            # Create new relationship model
            model = type(dj_model.__name__, (Model,), {})
            model.table = model.get_table_from_django(dj_model)
            model = model.factory(app)

        # Note that async model's name should equal to corresponding django model's name
        target_model_name = convert_class_name(field.related_model.__name__)
        target_model = getattr(app.m, target_model_name)

        return ManyToManyRelationship(app, model, target_model, source_field, target_field)

    return m2m_factory


def convert_model(model, **field_types):
    """
    Converts Django model to SQLAlchemy table
    """
    options = model._meta
    fields = []
    rels = {}
    for f in options.get_fields():
        i = f.name
        if i in field_types:
            fields.append(sa.column(i, field_types[i]))
        elif f.is_relation:
            if f.many_to_many:
                rels[i] = convert_m2m(f)
            elif f.many_to_one:
                # TODO: Add ManyToOneRelationship to rels
                fields.append(FIELD_CONVERTER.convert(f))
            elif f.one_to_many:
                pass  # TODO: Add OneToManyRelationship to rels
            elif f.one_to_one:
                # TODO: Add OneToOneRelationship to rels
                if not f.auto_created:
                    fields.append(FIELD_CONVERTER.convert(f))
            else:
                raise ConversionError('Unknown relation: {}'.format(i))
        else:
            fields.append(FIELD_CONVERTER.convert(f))
    return sa.table(options.db_table, *fields), rels


def derive_from_django(dj_model, **field_types):
    def wrapper(amodel):
        table, rels = convert_model(dj_model, **field_types)
        amodel.table = table
        amodel.relationships = rels
        return amodel
    return wrapper


class ConversionError(Exception):
    pass
