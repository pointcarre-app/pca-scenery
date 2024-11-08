# Basic example

Assume you work on the following Django application.

```plaintext

├── project_django
│   ├── db.sqlite3
│   ├── manage.py
│   ├── project_django
│   │   ├── asgi.py
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── some_app
│       ├── admin.py
│       ├── apps.py
│       ├── __init__.py
│       ├── migrations
│       │   ├── ...
│       ├── models.py
│       ├── tests.py
│       └── views.py
└── set_up_instructions.py
```

In order to use scenery, you need to add the following  files

```plaintext

├── common_items.yml
├── manifests
│   └── hello.yml
├── project_django
│   └── ...
└── set_up_instructions.py
```