#!/usr/bin/env python

import shutil
import sys

import django
import pytest
from django.core.management import call_command

django.setup()

# Re-create migrations each time since they depend on python and django versions
shutil.rmtree('tests/migrations', True)
call_command('makemigrations', 'tests', verbosity=2 if '-v' in sys.argv else 0)
call_command('migrate')
raise SystemExit(pytest.main())
