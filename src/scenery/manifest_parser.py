import os

import scenery.common
import scenery.manifest

import yaml
from yaml.constructor import ConstructorError


class ManifestParser:
    """
    A class responsible for parsing test manifest files in YAML format.

    This class provides methods to validate, format, and parse manifest files
    into Python objects that can be used by the testing framework.

    Attributes:
        common_items (dict): Common items loaded from a YAML file specified by the SCENERY_COMMON_ITEMS environment variable.
    """

    common_items = scenery.common.read_yaml(os.getenv("SCENERY_COMMON_ITEMS"))

    ################
    # FORMATTED DICT
    ################

    @staticmethod
    def parse_formatted_dict(d: dict):
        """
        Parse a dictionary with all expected keys into a Manifest object.

        Args:
            d (dict): A dictionary containing the manifest data with all expected keys.
                - set_up_test_data
                - set_up
                - cases
                - scenes
                - manifest_origin

        Returns:
            scenery.manifest.Manifest: A Manifest object created from the input dictionary.
        """

        d = {key: d[key.value] for key in scenery.manifest.ManifestFormattedDictKeys}
        return scenery.manifest.Manifest.from_formatted_dict(d)

    ##########
    # ANY DICT
    ##########

    @staticmethod
    def validate_dict(d: dict):
        """
        Validate the top-level keys of a manifest dictionary.

        This method checks if only valid keys are present at the top level and ensures
        that either singular or plural forms of 'case' and 'scene' are provided, but not both.

        Args:
            d (dict): The manifest dictionary to validate.

        Raises:
            ValueError: If invalid keys are present or if the case/scene keys are not correctly specified.
        """

        if not all(key in [x.value for x in scenery.manifest.ManifestDictKeys] for key in d.keys()):
            raise ValueError(
                f"Invalid key(s) in {d.keys()} ({d.get('manifest_origin', 'No origin found.')})."
            )

        for key in ["case", "scene"]:
            has_one = key in d
            has_many = f"{key}s" in d

            if has_one and has_many:
                raise ValueError(
                    f"Both `{key}` and `{key}s` keys are present at top level.",
                )

            if key == "scene" and not (has_one or has_many):
                raise ValueError(
                    f"Neither `{key}` and `{key}s` keys are present at top level.",
                )

    @staticmethod
    def format_dict(manifest: dict) -> dict:
        """
        Reformat the manifest dictionary to ensure it has all expected keys and provide default values if needed.

        Args:
            manifest (dict): The original manifest dictionary.

        Returns:
            dict: A formatted dictionary with all expected keys.
        """
        return {
            "set_up_test_data": manifest.get("set_up_test_data", []),
            "set_up": manifest.get("set_up", []),
            "scenes": ManifestParser._format_dict_scenes(manifest),
            "cases": ManifestParser._format_dict_cases(manifest),
            "manifest_origin": manifest["manifest_origin"],
        }

    @staticmethod
    def _format_dict_cases(d: dict) -> dict[str, dict]:
        has_one = "case" in d
        has_many = "cases" in d
        if has_one:
            return {"CASE": d["case"]}
        elif has_many:
            return d["cases"]
        else:
            return {"NO_CASE": {}}

    @staticmethod
    def _format_dict_scenes(d: dict) -> list[dict]:
        has_one = "scene" in d
        has_many = "scenes" in d
        if has_one:
            return [d["scene"]]
        elif has_many:
            return d["scenes"]

    @staticmethod
    def parse_dict(d: dict):
        """
        Parse a manifest dictionary into a Manifest object.

        This method validates the dictionary, formats it, and then parses it into a Manifest object.

        Args:
            d (dict): The manifest dictionary to parse.

        Returns:
            scenery.manifest.Manifest: A Manifest object created from the input dictionary.
        """
        ManifestParser.validate_dict(d)
        d = ManifestParser.format_dict(d)
        return ManifestParser.parse_formatted_dict(d)

    ##########
    # YAML
    ##########

    @staticmethod
    def validate_yaml(yaml):
        """
        Validate the structure of a YAML-loaded manifest.

        This method checks if the YAML content is a dictionary and if it contains only expected keys.

        Args:
            yaml: The YAML content to validate.

        Raises:
            TypeError: If the YAML content is not a dictionary.
            ValueError: If the YAML content contains unexpected keys.
        """

        if type(yaml) is not dict:
            raise TypeError(f"Manifest need to be a dict not a '{type(yaml)}'")

        if not all(
            key in [x.value for x in scenery.manifest.ManifestYAMLKeys] for key in yaml.keys()
        ):
            raise ValueError(
                f"Invalid key(s) in {yaml.keys()} ({yaml.get('origin', 'No origin found.')})"
            )

    @staticmethod
    def _yaml_constructor_case(loader: yaml.SafeLoader, node: yaml.nodes.Node):
        if isinstance(node, yaml.nodes.ScalarNode):
            return scenery.manifest.Substituable(loader.construct_scalar(node))
        else:
            raise ConstructorError

    @staticmethod
    def _yaml_constructor_common_item(loader: yaml.SafeLoader, node: yaml.nodes.Node):
        if isinstance(node, yaml.nodes.ScalarNode):
            return ManifestParser.common_items[loader.construct_scalar(node)]
        if isinstance(node, yaml.nodes.MappingNode):
            d = loader.construct_mapping(node)
            case = ManifestParser.common_items[d["ID"]] | {
                key: value for key, value in d.items() if key != "ID"
            }
            return case
        else:
            raise ConstructorError

    @staticmethod
    def read_manifest_yaml(fn):
        """
        Read a YAML manifest file with custom tags.

        This method uses a custom YAML loader to handle special tags like !case and !common-item.

        Args:
            fn (str): The filename of the YAML manifest to read.

        Returns:
            dict: The parsed content of the YAML file.
        """

        # NOTE: inspired by https://matthewpburruss.com/post/yaml/

        # Add constructor
        Loader = yaml.FullLoader
        Loader.add_constructor("!case", ManifestParser._yaml_constructor_case)
        Loader.add_constructor("!common-item", ManifestParser._yaml_constructor_common_item)

        with open(fn) as f:
            content = yaml.load(f, Loader)

        return content

    @staticmethod
    def parse_yaml(filename):
        """
        Parse a YAML manifest file into a Manifest object.

        This method reads the YAML file, validates its content, and then parses it into a Manifest object.

        Args:
            filename (str): The filename of the YAML manifest to parse.

        Returns:
            scenery.manifest.Manifest: A Manifest object created from the YAML file.
        """
        d = ManifestParser.read_manifest_yaml(filename)
        ManifestParser.validate_yaml(d)
        d["manifest_origin"] = d.get("manifest_origin", filename)
        if "variables" in d:
            del d["variables"]
        return ManifestParser.parse_dict(d)
