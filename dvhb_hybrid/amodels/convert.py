import sqlalchemy as sa

from django.contrib.postgres.fields.jsonb import JSONField
from django.db.models.fields import UUIDField
from django.db.models.fields.related import ForeignKey, ManyToManyField, OneToOneField
from django.db.models.fields.reverse_related import ManyToManyRel
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .model import Model
from .relations import ManyToManyRelationship
from ..utils import convert_class_name


DJANGO_SA_TYPES_MAP = {
    JSONField: JSONB,
    UUIDField: UUID(as_uuid=True)
    # TODO: add more fields
}


def convert_column(col):
    """
    Converts Django column to SQLAlchemy
    """
    result = []
    ctype = type(col)
    if ctype is ForeignKey or ctype is OneToOneField:
        result.append(col.column)
        ctype = type(col.target_field)
    else:
        result.append(col.name)
    if ctype in DJANGO_SA_TYPES_MAP:
        result.append(DJANGO_SA_TYPES_MAP[ctype])
    return tuple(result)


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
        raise TypeError('Unknown many to many field: %r' % field)

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

        return ManyToManyRelationship(model, target_model, source_field, target_field)

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
            fields.append((i, field_types[i]))
        elif f.is_relation:
            if f.many_to_many:
                rels[i] = convert_m2m(f)
            elif f.many_to_one:
                # TODO: Add ManyToOneRelationship to rels
                fields.append(convert_column(f))
            elif f.one_to_many:
                pass  # TODO: Add OneToManyRelationship to rels
            elif f.one_to_one:
                # TODO: Add OneToOneRelationship to rels
                if not f.auto_created:
                    fields.append(convert_column(f))
            else:
                raise ValueError('Unknown relation: {}'.format(i))
        else:
            fields.append(convert_column(f))
    table = sa.table(options.db_table, *[sa.column(*f) for f in fields])
    return table, rels


def derive_from_django(dj_model, **field_types):
    def wrapper(amodel):
        table, rels = convert_model(dj_model, **field_types)
        amodel.table = table
        amodel.relationships = rels
        return amodel
    return wrapper
