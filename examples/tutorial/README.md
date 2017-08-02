# dvhb-hybrid example application from tutorial

Configure project:

```bash
python3 -m venv venv
source venv/bin/activate
createdb tutorial
python manage.py migrate
python manage.py createsuperuser --username admin --email admin@example.com
```

Run admin:

```bash
python manage.py runserver
```

Open `http://localhost:8000/admin/`.


Run aioworkers application:

```bash
python -m aioworkers -c config.yaml
```

Open `http://localhost:8080/apidoc/`.