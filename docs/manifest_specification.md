# Manifest specification

> See [Glossary](./glossary.md) for definitions.

## Basic syntax

### Scene(s) 

Required.

```yaml
scene:
  method: ...
  url: ...
  data: ...
  directives:
  - status_code: ...
  - redirect_url: ...
```
or 

```yaml
scenes:
- method: ...
  url: ...
  data: ...
  directives:
  - status_code: ...
  - redirect_url: ...
  ...
```

An HTTP scene is defined by:
- a method (`GET`, `POST`, ...)
- an url
- some data (optional)
- some url parameters (optional)
- some query parameters (optional)


An HTTP directive may be related to:
- the response status code
- the redirect url
- some DOM element of the returned html
- the state of the database (e.g. counting the instances of a model)

See [??]() for more details


### Case(s)

Optional.
```yaml
case:
  item_1:
    foo: ...
  item_2:
    bar: ...

```
or
```yaml
cases:
  CASE_A:
    item_1:
        foo: ...
    item_2:
      bar: ...
  CASE_B:
    item_1:
        foo: ...
    item_2:
      bar: ...
```

### Set up

Two optional keys:
- `set_up_test_data`
- `set_up`

They contain lists of instructions executed the tests contained in the manifest.  Some instructions require keyword arguments that need to be passed as a dictionary. 

Instructions in `set_up_test_data` are executed be once before for all tests. `setup` instructions are executed before each test contained in the manifest. This is the exact same syntax and commands as for `set_up_test_data`.

```yaml
set_up_test_data:
  - reset_db
  - create_testuser:
      first_name : Jane
      last_name : Doe
      ...
```

The functions name and args should correspond to what is defined in the module attached to `SCENERY_SET_UP_INSTRUCTIONS` in [`scenery_settings.py`](./settings.md)


### Substituable fields

To indicate that a field is substituable, use the `!case` tag with one of the following syntax:

1. Whole item

```yaml
case:
  item: ...
scene:
  - ...
    data:
      item: !case "item"
```

2. Single field

```yaml
case:
  item:
    foo: ...
    bar: ...
scene:
  - ...
    data:
      item_foo: !case "item:foo"
```


### Common items

Common items allow you to use one single YAML file to store some data that you can refer to in your manifest. This helps you keeping the code base more readable. For instance, it can help store the information of your test user.
HERE

The path to the `.yml` file is defined under `SCENERY_COMMON_ITEMS` in [`scenery_settings.py`](./settings.md)

```yaml
ITEM_ID1:
  foo: 0
ITEM_ID2:
  bar: "a" 
```

In the manifest, two possible syntax can be used with the `!common-item` tag

1. access directly the item
```yaml
set_up_test_data:
	- reset_db
	- create_testuser: !common-item TESTUSER
```


2. access the item and add/overwrite a given (key, value) pair of the item
```yaml
set_up_test_data:
  - reset_db
  - create_testuser: !common-item 
    ID: TESTUSER # this is the ID as it appears in the common items YAML file
    foo: 42 # overwrites the foo attribute
```
### YAML aliases

>[!danger] Aliases do not work as expected, especially when interacting with `!case` and `!common-items` tages, so don't use them. It's because YAML aliases are resolved before tags which are not "transported" in the alias.


## Last thoughts

The manifest specification provide different ways to avoid the repetition of information. As a consequence, there is not a unique manifest resulting in a given set of tests. Below are still some guidelines to choose how to write a manifest:

- Scene vs. Case: 
	- Information describing the state/behavior of the app should be hard-coded in the scene. 
	- Information coming from the user's input should coded as a substituable field using `!case`.
	- Information about content from the database may be coded as one or the other. Readability and maintainability should be your priority, then conciseness.

