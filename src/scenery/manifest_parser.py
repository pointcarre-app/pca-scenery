"""Parse manifest YAML files and build proper Manifests."""

import os
import io
from typing import Any, cast

import scenery.common
import scenery.manifest

import yaml
from yaml.constructor import ConstructorError


#####################
# PARSER
#####################


class ManifestParser:
    """
    A class responsible for parsing test manifest files in YAML format.

    This class provides methods to validate, format, and parse manifest files
    into Python objects that can be used by the testing framework.

    Attributes:
        common_items (dict): Common items loaded from a YAML file specified by the SCENERY_COMMON_ITEMS environment variable.
    """

    common_items: dict[str, dict] = scenery.common.read_yaml(os.environ["SCENERY_COMMON_ITEMS"])

    ##########
    # RAW DICT
    ##########

    @staticmethod
    def validate_dict(d: dict) -> None:  # scenery.manifest.RawManifestDict
        """
        Validate the top-level keys of a manifest dictionary.

        This method checks if only valid keys are present at the top level and ensures
        that either singular or plural forms of 'case' and 'scene' are provided, but not both.

        Args:
            d (dict): The manifest dictionary to validate.

        Raises:
            ValueError: If invalid keys are present or if the case/scene keys are not correctly specified.
        """
        if not all(
            key in scenery.manifest.RawManifestDict.__annotations__.keys() for key in d.keys()
        ):
            raise ValueError(
                f"Invalid key(s) in {d.keys()} ({d.get('manifest_origin', 'No origin found.')})"
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
    def format_dict(d: scenery.manifest.RawManifestDict) -> scenery.manifest.ManifestDict:
        """
        Reformat the manifest dictionary to ensure it has all expected keys and provide default values if needed.

        Args:
            d (dict): The original manifest dictionary.

        Returns:
            dict: A formatted dictionary with all expected keys.
        """
        return {
            "set_up_class": d.get("set_up_class", []),
            "set_up": d.get("set_up", []),
            "scenes": ManifestParser._format_dict_scenes(d),
            "cases": ManifestParser._format_dict_cases(d),
            "manifest_origin": d["manifest_origin"],
            "ttype": d.get("ttype")
        }

    @staticmethod
    def _format_dict_cases(d: scenery.manifest.RawManifestDict) -> dict[str, dict]:
        has_one = "case" in d
        has_many = "cases" in d
        if has_one:
            return {"CASE": d["case"]}
        elif has_many:
            return d["cases"]
        else:
            return {"NO_CASE": {}}

    @staticmethod
    def _format_dict_scenes(d: scenery.manifest.RawManifestDict) -> list[dict]:
        has_one = "scene" in d
        has_many = "scenes" in d
        if has_one:
            return [d["scene"]]
        elif has_many:
            return d["scenes"]
        else:
            raise ValueError

    @staticmethod
    def parse_dict(d: dict) -> scenery.manifest.Manifest:
        """
        Parse a manifest dictionary into a Manifest object.

        This method validates the dictionary, formats it, and then parses it into a Manifest object.

        Args:
            d (dict): The manifest dictionary to parse.

        Returns:
            scenery.manifest.Manifest: A Manifest object created from the input dictionary.
        """
        ManifestParser.validate_dict(d)
        formatted_d = ManifestParser.format_dict(cast(scenery.manifest.RawManifestDict, d))
        return scenery.manifest.Manifest.from_formatted_dict(formatted_d)

    ##########
    # YAML
    ##########

    @staticmethod
    def validate_yaml(obj: Any) -> None:
        """
        Validate the structure of a YAML-loaded manifest.

        This method checks if the YAML content is a dictionary and if it contains only expected keys.

        Args:
            obj (Any): The YAML content to validate.

        Raises:
            TypeError: If the YAML content is not a dictionary.
            ValueError: If the YAML content contains unexpected keys.
        """
        if not isinstance(obj, dict):
            raise TypeError(f"Manifest need to be a dict not a '{type(obj)}'")

        if not all(
            key in scenery.manifest.RawManifestDict.__annotations__.keys() for key in obj.keys()
        ):
            raise ValueError(
                f"Invalid key(s) in {obj.keys()} ({obj.get('manifest_origin', 'No origin found.')})"
            )

    @staticmethod
    def _yaml_constructor_case(
        loader: yaml.SafeLoader, node: yaml.nodes.Node
    ) -> scenery.manifest.Substituable:
        if isinstance(node, yaml.nodes.ScalarNode):
            return scenery.manifest.Substituable(loader.construct_scalar(node))
        else:
            raise ConstructorError

    @staticmethod
    def _yaml_constructor_common_item(loader: yaml.SafeLoader, node: yaml.nodes.Node) -> dict:
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
    # def read_manifest_yaml(filename: str) -> Any:
    def read_manifest_yaml(stream: str | io.TextIOWrapper) -> Any:
        """
        Read a YAML manifest stream with custom tags.

        This method uses a custom YAML loader to handle special tags like !case and !common-item.

        Args:
            stream(str | StringIO): The stream of the YAML manifest to read.

        Returns:
            dict: The parsed content of the YAML file.
        """
        # NOTE: inspired by https://matthewpburruss.com/post/yaml/

        # Add constructor
        Loader = yaml.FullLoader
        Loader.add_constructor("!case", ManifestParser._yaml_constructor_case)
        Loader.add_constructor("!common-item", ManifestParser._yaml_constructor_common_item)

        # with open(filename) as f:
        #     content = yaml.load(f, Loader)

        content = yaml.load(stream, Loader)
        ManifestParser.validate_yaml(content)
        return content


    @staticmethod
    def parse_yaml_from_file(filename: str) -> scenery.manifest.Manifest:
        """
        Parse a YAML manifest file into a Manifest object.

        This method reads the YAML file, validates its content, and then parses it into a Manifest object.

        Args:
            filename (str): The filename of the YAML manifest to parse.

        Returns:
            scenery.manifest.Manifest: A Manifest object created from the YAML file.
        """
        with open(filename) as f:
            d = ManifestParser.read_manifest_yaml(f)
        d["manifest_origin"] = d.get("manifest_origin", filename)
        return ManifestParser.parse_dict(d)

