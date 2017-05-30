import yaml
from django.core import serializers
from django.core.management.commands import loaddata


class FindFixture(loaddata.Command):
    """Command to search fixtures"""
    def __init__(self, stdout=None, stderr=None, no_color=False, *, app_label):
        super().__init__(stdout, stderr, no_color)
        self.compression_formats = {
            None: (open, 'rb'),
        }
        self.serialization_formats = serializers.get_public_serializer_formats()
        self.using = None
        self.verbosity = 0
        self.app_label = app_label


def get_fixture(app_label, fixture_label, model_name, pk, *, fields=(), ids_fields=(), exclude_fields=()):
    """Creates an object from fixture"""
    fixtures = FindFixture(app_label=app_label).find_fixtures(fixture_label)
    if len(fixtures) > 1:
        raise ValueError('Found more that ')
    fixture_file, _, _ = fixtures[0]
    object_list = yaml.load(open(fixture_file, 'rb'))
    if not object_list:
        raise ValueError('Empty fixture')
    model = ('%s.%s' % (app_label, model_name)).lower()
    for obj in object_list:
        if obj['model'] == model and obj['pk'] == pk:
            fields = fields or obj['fields'].keys()
            fixture = {field: obj['fields'][field] for field in fields}
            fixture['id'] = obj['pk']
            for f in ids_fields:
                if f in fixture:
                    fixture[f + '_id'] = fixture.pop(f)
            for f in exclude_fields:
                if f in fixture:
                    del fixture[f]
            return fixture

    raise ValueError('Object %s with pk=%s not found.' % (model, pk))
