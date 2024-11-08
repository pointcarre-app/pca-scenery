# Basic example

Assume you work on the following Django application.

```plaintext
└── project_django
    ├── db.sqlite3
    ├── manage.py
    ├── project_django
    │   ├── asgi.py
    │   ├── __init__.py
    │   ├── settings.py
    │   ├── urls.py
    │   └── wsgi.py
    └── some_app
        ├── admin.py
        ├── apps.py
        ├── __init__.py
        ├── migrations
        │   └── ...
        ├── models.py
        ├── tests
        │   └──  ...
        └── views.py
```

## Scenery files

In order to use scenery, you could update your repo structure as below:

```plaintext
├── project_django
│   ├── ...
│   └── some_app
│       ├── tests
│       │   ├── ...
│       │   ├── common_items.yml
│       │   ├── set_up_instructions.py
│       │   └── manifests
│       │       └── ...
│       └── ...
└── scenery_settings.py
```

### Scenery settings

The files gives you full control on any other folder structure you would prefer.

```python
# scenery_settings.py
SCENERY_COMMON_ITEMS = "projet_django/some_app/tests/common_items.yml"
SCENERY_SET_UP_INSTRUCTIONS = "project_django.some_app.tests.set_up_instructions"
SCENERY_MANIFESTS_FOLDER = "projet_django/some_app/tests/manifests"
SCENERY_TESTED_APP_NAME = "some_app"
```

### Set up instructions

This file contains all actions you may want to execute in the `setUpTestData` or `setUp` testcase function. All functions shoul take `django_testcase: django.test.TestCase` as their first argument.

```python
# project_django/some_app/tests/set_up_instructions.py

def reset_db(django_testcase):
    """Reset your database."""
    ...

def create_test_user(
        django_testcase, 
        *, 
        username, 
        field, 
        first_name, 
        last_name, 
        foo):
    """Create a new user in your database"""
    ...
```

### Common items

This file allows you to store data you want to use accross many tests. In this file, you can take full adavantage of the yaml syntax.

```yaml
# project_django/some_app/tests/common_items.yml

EMAIL: &email some@mail.com
PASSWORD: &password somepassword

CREDENTIALS: &credentials
  username : *email
  password : *password

SOMEONE: &someone
  first_name : John
  last_name : Doe

TESTUSER:
  <<: *credentials
  <<: *someone
  foo : bar

```

## Adding your first Manifest


Assume you want to test your login view

```python
# project_django/some_app/views.py
def login(request):
    ...

```

You can now write a basic manifest that will check your view accepts an existing user and block if the provided credentials do not match what is in the database.


```yaml
# project_django/some_app/tests/manifests/login.yml
set_up:
  # Reset the database
  - reset_db
  # Create a test user based on credentials defined in 
  # project_django/some_app/tests/common_items.yml
  - create_testuser: 
      !common-item TESTUSER

cases:
  # Case 1: correct credentials, we expect the 200 code status
  success:
    credentials: 
        !common-item CREDENTIALS # this is the ID as it appears in the common items YAML file
    status_code: 200
  # Case 2: wrong credentials, we expect the 401 code status
  failure:
    credentials: 
        !common-item # this syntax allows to add/overwrite attributes
        ID: CREDENTIALS
        password: wrongpassword
    status_code: 401

scene: 
  method: POST
  url: app:login
  data: !case credentials
  directives:
    - status_code: !case status_code
```


> [!WARNING] Only a subset of YAML syntax is supported in the manifests. Please read [the full manifest specification](../manifest_specification.md)


## Run your tests

You are now all set up to launch scenery!

```bash
python -m scenery --django_settings=project_dango.project_django.settings
```

Or add it in your CI workflow.