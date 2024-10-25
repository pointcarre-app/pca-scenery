# Usage


### Test Manifests

With `scenery`, integration tests are configured using YAML, a human-readable data serialization language, making maintenance easy for developers. A given YAML file is called a __manifest__.

In a manifest, a test is described by a __scene__ which defines the request to a given URL and the checks (called __directives__) that should be applied to the HTTP response.

#### Example 1: Simple GET request

```yaml
scene:
  method: GET
  url: "index"
  directives:
    - status_code: 200
```

This test sends a GET request to the '/index' URL and checks if the returned status code is 200.

#### Example 2: POST request with data

```yaml
cases:
  CASE_A:
    item_1:
        foo: 0
  CASE_B:
    item_1:
        foo: 1

scene:
  method: POST
  url: "item"
  data:
    item_id: !case item_1:foo
  directives:
    - status_code: 200
```

This test sends a POST request to the '/item' URL with `{item_id: 0}` and `{item_id: 1}` as data and checks if the returned status code is 200.

### Advanced Features

The full syntax of `scenery` allows you to:

- Test a given scene with different data sets
- Shared data for use across multiple tests
- Have full control over set-up <!-- and tear-down methods -->
- Use variables and templating in your YAML files
<!-- - Define custom directives for specialized checks -->

See the full [manifest specification](./manifest_specification.md) for more details.

### Settings

`scenery` relies on 4 environment variables, which can be easily provided by a `scenery_settings.py` file at the root of your project (or any location you prefer).

You also need to provide the Django settings you want to use. Here's an example `scenery_settings.py`:

```python
# scenery_settings.py
SCENERY_MANIFESTS_FOLDER = "path/to/your/manifests"
SCENERY_COMMON_ITEMS = "path/to/shared/data.yml"
SCENERY_SET_UP_INSTRUCTIONS = "path/to/your/set_up_tear_down_functions"
SCENERY_TESTED_APP_NAME = "your_app_name"
```



### Running Tests

To run your tests, use the following command:

```bash
python -m scenery --django_settings=your_project.settings.test
```

You can also add additional command-line arguments to filter tests, set verbosity, etc. Run `python -m scenery --help` for more information.