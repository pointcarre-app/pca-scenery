# Settings

Settings are stored in a specific module, by default at the root of the directory you are calling `scenery` from in a file called `scenery_settings.py`.

If you prefer to use another naming convention or locate the file somewhere else, simply use the `--scenery_settings` option from the CLI.

```bash
python -m scenery --scenery_settings=path/to/scenery_settings.py --django_settings=your.dango.settings
 ```

 The file should look like this:

```python
# scenery_settings.py
SCENERY_MANIFESTS_FOLDER = "path/to/your/manifests"
SCENERY_COMMON_ITEMS = "path/to/shared/data.yml"
SCENERY_SET_UP_INSTRUCTIONS = "path/to/your/set_up_tear_down_functions"
SCENERY_TESTED_APP_NAME = "your_app_name"
```
