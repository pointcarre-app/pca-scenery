"""Represent all data conveied by the manifest."""

from dataclasses import dataclass, field
import enum
import os
import http
from typing import Any
from urllib.parse import urlparse
import re
import typing
import itertools

from django.utils.http import urlencode
from django.urls.exceptions import NoReverseMatch
from django.db.models.base import ModelBase

from django.apps import apps as django_apps
from django.urls import reverse 



#############################
# TYPE HINTS
#############################


class RawManifestDict(typing.TypedDict, total=False):
    """The type of dict which can appear in the yamls."""

    set_up_class: typing.Sequence[dict]
    set_up: typing.Sequence[dict]
    case: dict
    cases: dict[str, dict]
    scene: dict
    scenes: typing.List[dict]
    manifest_origin: str
    ttype: str


class ManifestDict(typing.TypedDict):
    """The clean version of the dict parsed, ready to be transformed into a proper manifest."""

    scenes: typing.List[dict]
    cases: dict[str, dict]
    manifest_origin: str
    set_up_class: typing.Sequence[str | dict]
    set_up: typing.Sequence[str | dict]
    ttype: typing.Optional[str]


########################
# SINGLE KEY DICTIONNARY
########################


SingleKeyDictKey = typing.TypeVar("SingleKeyDictKey", bound=str)
SingleKeyDictKeyValue = typing.TypeVar("SingleKeyDictKeyValue")


@dataclass
class SingleKeyDict(typing.Generic[SingleKeyDictKey, SingleKeyDictKeyValue]):
    """A dataclass representing a dictionary with a single key-value pair.

    This class is useful for having a quick as_tuple representation of a dict {key:value}
    returned as (key, value).

    Attributes:
        _dict (Dict[SingleKeyDictKey, SingleKeyDictKeyValue]): The underlying dictionary.
        key (SingleKeyDictKey): The single key in the dictionary.
        value (SingleKeyDictKeyValue): The value associated with the single key.

    Methods:
        validate(): Ensures the dictionary has exactly one key-value pair.
        as_tuple(): Returns the key-value pair as a tuple.

    Raises:
        ValueError: If the dictionary does not contain exactly one key-value pair.
    """

    _dict: typing.Dict[SingleKeyDictKey, SingleKeyDictKeyValue] = field()
    key: SingleKeyDictKey = field(init=False)
    value: SingleKeyDictKeyValue = field(init=False)

    def __post_init__(self) -> None:
        self.validate()
        self.key, self.value = next(iter(self._dict.items()))

    def validate(self) -> None:
        """Check the dictonary has indeed a single key."""
        if len(self._dict) != 1:
            raise ValueError(
                f"SingleKeyDict should have length 1 not '{len(self._dict)}'\n{self._dict}"
            )

    def as_tuple(self) -> tuple:
        """🔴 This should not be confused with built-in method datclasses.astuple."""
        return self.key, self.value


####################################
# ENUMS
####################################


########
# CHECKS
########


class DirectiveCommand(enum.Enum):
    """Values allowed for Manifest["checks"]."""

    STATUS_CODE = "status_code"
    REDIRECT_URL = "redirect_url"
    COUNT_INSTANCES = "count_instances"
    DOM_ELEMENT = "dom_element"
    FIELD_OF_INSTANCE = "field_of_instance"
    # JS_VARIABLE = "js_variable"
    JS_STRINGIFY = "js_stringify"
    JSON = "inspect_json"


class DomArgument(enum.Enum):
    """Values allowed for Manifest["checks]["dom_element"]."""

    FIND = "find"
    FIND_ALL = "find_all"
    COUNT = "count"
    SCOPE = "scope"
    TEXT = "text"
    ATTRIBUTE = "attribute"


##########################
# SET UP TEST DATA, SET UP
##########################


@dataclass(frozen=True)
class SetUpInstruction:
    """Store the command and potential arguments for setUpTestData and setUp."""

    command: str
    args: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_object(cls, x: str | dict) -> "SetUpInstruction":
        """Return an instruction from a string or a dict."""
        match x:
            case str(s):
                cmd_name, args = s, {}
            case dict(d) if len(d) == 1:
                cmd_name, args = SingleKeyDict(d).as_tuple()
            case dict(d):
                raise ValueError(
                    f"`SetUpInstruction` cannot be instantiated from dictionnary of length {len(x)}\n{x}"
                )
            case _:
                raise TypeError(f"`SetUpInstruction` cannot be instantiated from {type(x)}")

        return cls(cmd_name, args)


########################
# CASE
########################


@dataclass(frozen=True)
class Item:
    """Store potential information that will be used to build the HTTP Request."""

    _id: str
    _dict: dict[str, Any]

    def __getitem__(self, key: str) -> Any:
        return self._dict[key]


@dataclass(frozen=True)
class Case:
    """Store a collection of items representing a test case.

    Attributes:
        _id (str): The identifier for this case.
        items (dict[str, Item]): A dictionary of items in this case, indexed by item ID.

    Methods:
        __getitem__(item_id): Retrieve an item from the case by its ID.

    Class Methods:
        from_id_and_dict(case_id: str, items: dict[str, dict]) -> Case:
            Create a Case instance from a case ID and a dictionary of items.
    """

    _id: str
    items: dict[str, Item]

    def __getitem__(self, item_id: str) -> Item:
        return self.items[item_id]

    @classmethod
    def from_id_and_dict(cls, case_id: str, items_dict: dict[str, dict[str, Any]]) -> "Case":
        """Return a case from an id and a dict."""
        items = {item_id: Item(item_id, item_dict) for item_id, item_dict in items_dict.items()}
        return cls(case_id, items)


########################
# SCENES
########################


@dataclass
class Substituable:
    """Represent the field which need to be replace by some value coming from a given case."""

    field_repr: str
    regex_field = re.compile(r"^(?P<item_id>[a-z_]+):?(?P<field_name>[a-z_]+)?$")

    def __post_init__(self) -> None:
        if not (re_match := re.match(self.regex_field, self.field_repr)):
            raise ValueError(f"Invalid field representation '{self.field_repr}'")
        else:
            self.field_repr_match = re_match

    def shoot(self, case: Case) -> Any:
        """Return the corresponding case's value based on the field representation."""
        match self.field_repr_match.groups():
            case item_id, None:
                # There is only a reference to the item
                # In this case , we pass all the variables with the dict
                # return case[item_id][self.target]
                return case[item_id]._dict
            case item_id, field_name:
                # There is only a reference to the item:field_name
                # In this case, we pass only the corresponding value
                # field_value = case[item_id][self.target][field_name]
                field_value = case[item_id][field_name]
                return field_value


@dataclass
class Directive:
    """Store a given check to perform, before the substitution (this is part of a Scene, not a Take).

    This class represents a directive (check) to be performed on an HTTP response,
    before case-specific substitutions have been made.

    Attributes:
        instruction (DirectiveCommand): The type of check to perform.
        args (Any): The arguments for the check.

    Class Methods:
        from_dict(directive_dict: dict) -> Directive:
            Create an Directive instance from a dictionary.
    """

    instruction: DirectiveCommand
    args: Any

    def __post_init__(self) -> None:
        """Format self.args."""
        match self.instruction, self.args:
            case DirectiveCommand.STATUS_CODE, int(n):
                self.args = http.HTTPStatus(n)
                # NOTE: Workaround if we want the class to be frozen
                # object.__setattr__(self, "args", HTTPStatus(n))
                pass
            case DirectiveCommand.STATUS_CODE, Substituable():
                pass
            case DirectiveCommand.DOM_ELEMENT, dict(d):
                self.args = {DomArgument(key): value for key, value in d.items()}
                # Check if there is and only one locator
                locators = [
                    self.args.get(key, None) for key in (DomArgument.FIND_ALL, DomArgument.FIND)
                ]
                if not any(locators):
                    raise ValueError("Neither `find_all` or `find` provided to check DOM element")
                else:
                    locators = list(filter(None, locators))
                    if len(locators) > 1:
                        raise ValueError("More than one locator provided")

            case DirectiveCommand.DOM_ELEMENT, Substituable():
                pass
            case DirectiveCommand.REDIRECT_URL, str(s):
                pass
            case DirectiveCommand.REDIRECT_URL, Substituable():
                pass
            case DirectiveCommand.COUNT_INSTANCES, {"model": str(s), "n": int(n)}:
                # if os.environ.get("DJANGO_SETTINGS_MODULE"):
                app_config = django_apps.get_app_config(os.environ["SCENERY_TESTED_APP_NAME"])
                self.args["model"] = app_config.get_model(s)
            case DirectiveCommand.COUNT_INSTANCES, Substituable():
                pass
            case DirectiveCommand.JSON, {"key": str(s), "value": _}: # 
                pass
            case DirectiveCommand.FIELD_OF_INSTANCE, {"find": {"model": str(model)}, "field": str(s), "value": _}: # 
                # if os.environ.get("DJANGO_SETTINGS_MODULE"):
                app_config = django_apps.get_app_config(os.environ["SCENERY_TESTED_APP_NAME"])
                self.args["find"]["model"] = app_config.get_model(model)
            case _:
                raise ValueError(
                    f"Cannot interpret '{self.instruction}:({self.args})' as Directive"
                )

    @classmethod
    def from_dict(cls, directive_dict: dict) -> "Directive":
        """Return the Directive based on the provided dict."""
        instruction, args = SingleKeyDict(directive_dict).as_tuple()
        return cls(DirectiveCommand(instruction), args)


@dataclass
class Scene:
    """Store all actions to perform, before the substitution of information from the `Cases`.

    This class represents an Scene, which includes the method, URL, and various
    parameters and checks to be performed.

    Attributes:
        method (http.HTTPMethod): The HTTP method for this scene.
        url (str): The URL or URL pattern for this scene.
        directives (list[Directive]): The list of directives (checks) to perform.
        data (dict[str, Any]): The data to be sent with the request.
        query_parameters (dict): Query parameters for the URL.
        url_parameters (dict): URL parameters for reverse URL lookup.

    Methods:
        shoot(case: Case) -> Take:
            Create an Take instance by substituting case values into the scene.

    Class Methods:
        from_dict(d: dict) -> Scene:
            Create an Scene instance from a dictionary.
        substitute_recursively(x, case: Case):
            Recursively substitute values from a case into a data structure.
    """

    method: http.HTTPMethod
    url: str
    directives: list[Directive]
    data: dict[str, Any] = field(default_factory=dict)
    query_parameters: dict = field(default_factory=dict)
    url_parameters: dict = field(default_factory=dict)
    actions: typing.Optional[list[SetUpInstruction]] = field(default_factory=list)


    def __post_init__(self) -> None:
        self.method = http.HTTPMethod(self.method)
        # At this point we don't check url as we wait for subsitution
        # potentially occuring through data/query_parameters/url_parameters

    @classmethod
    def from_dict(cls, d: dict) -> "Scene":
        """Return a scene from a dict."""
        d["directives"] = [Directive.from_dict(directive) for directive in d["directives"]]
        return cls(**d)

    @classmethod
    def substitute_recursively(cls, x: typing.Any, case: Case) -> typing.Any:
        """Perform the substitution."""
        match x:
            case int(_) | str(_):
                return x
            case ModelBase():
                return x
            case Substituable(_):
                return x.shoot(case)
            case Directive(instruction, args):
                return Check(instruction, cls.substitute_recursively(args, case))
            case dict(_):
                return {key: cls.substitute_recursively(value, case) for key, value in x.items()}
            case list(_):
                return [cls.substitute_recursively(value, case) for value in x]
            case _:
                raise NotImplementedError(f"Cannot substitute recursively '{x}' ('{type(x)}')")

    def shoot(self, case: Case) -> "Take":
        """Return the Take resulting from the case applied to its scene."""
        return Take(
            method=self.method,
            url=self.url,
            query_parameters=self.query_parameters,
            data=self.substitute_recursively(self.data, case),
            url_parameters=self.substitute_recursively(self.url_parameters, case),
            checks=self.substitute_recursively(self.directives, case),
        )


################
# MANIFEST
################


@dataclass(frozen=True)
class Manifest:
    """Store all the information to build/shoot all different `Takes`.

    This class represents a complete test manifest, including setup instructions,
    test cases, and scenes to be executed.

    Attributes:
        set_up_test_data (list[SetUpInstruction]): Instructions for setting up test data.
        set_up (list[SetUpInstruction]): Instructions for general test setup.
        scenes (list[Scene]): The scenes to be executed.
        cases (dict[str, Case]): The test cases, indexed by case ID.
        manifest_origin (str): The origin of the manifest file.

    Class Methods:
        from_formatted_dict(d: dict) -> Manifest:
            Create a Manifest instance from a formatted dictionary.
    """

    set_up_class: list[SetUpInstruction]
    set_up: list[SetUpInstruction]
    scenes: list[Scene]
    cases: dict[str, Case]
    manifest_origin: str
    ttype: str | None

    @classmethod
    def from_formatted_dict(cls, d: ManifestDict) -> "Manifest":
        """Return a manifest from a dict with expected keys."""
        return cls(
            [
                SetUpInstruction.from_object(instruction)
                for instruction in d[
                    "set_up_class"
                ]  # d[ManifestFormattedDictKeys.set_up_test_data]
            ],
            [
                SetUpInstruction.from_object(instruction)
                for instruction in d["set_up"]  # d[ManifestFormattedDictKeys.set_up]
            ],
            [
                Scene.from_dict(scene) for scene in d["scenes"]
            ],  # d[ManifestFormattedDictKeys.scenes]],
            {
                case_id: Case.from_id_and_dict(case_id, case_dict)
                for case_id, case_dict in d[
                    "cases"
                ].items()  # d[ManifestFormattedDictKeys.cases].items()
            },
            # d[ManifestFormattedDictKeys.manifest_origin],
            d["manifest_origin"],
            d.get("ttype")
        )
    
    def iter_on_takes(
        self, 
        only_url: str | None, 
        only_case_id: str | None, 
        only_scene_pos: str | None
    ) -> typing.Iterable[typing.Tuple[str, int, "Take"]]:
        for (case_id, case), (scene_pos, scene) in itertools.product(
            self.cases.items(), enumerate(self.scenes)
        ):
            if only_case_id is not None and case_id != only_case_id:
                continue
            elif only_scene_pos is not None and str(scene_pos) != only_scene_pos:
                continue
            if only_url is not None and only_url != scene.url:
                continue
            take = scene.shoot(case)
            yield case_id, scene_pos, take


########################
# TAKES
########################


@dataclass
class Check(Directive):
    """Store a given check to perform (after the subsitution)."""

    def __post_init__(self) -> None:
        """Format self.args."""
        match self.instruction, self.args:
            case DirectiveCommand.STATUS_CODE, int(n):
                self.args = http.HTTPStatus(n)
            case DirectiveCommand.DOM_ELEMENT, dict(d):
                self.args = {DomArgument(key): value for key, value in d.items()}
                if attribute := self.args.get(DomArgument.ATTRIBUTE):
                    if value:= attribute.get("value"):
                        self.args[DomArgument.ATTRIBUTE]["value"] = (
                            self._format_dom_element_attribute_value(value)
                        )
            case DirectiveCommand.REDIRECT_URL, str(_):
                pass
            case DirectiveCommand.COUNT_INSTANCES, {"model": ModelBase(), "n": int(n)}:
                # NOTE mad: Validate model is registered
                app_config = django_apps.get_app_config(os.environ["SCENERY_TESTED_APP_NAME"])
                app_config.get_model(self.args["model"].__name__)
            case DirectiveCommand.JS_STRINGIFY, _:
                # TODO mad: js_stringify
                pass
            case DirectiveCommand.JSON, {"key": str(_), "value": _} :
                pass
            case DirectiveCommand.FIELD_OF_INSTANCE, {"find":{"model": ModelBase()}, "field": str(_), "value": _}:
                # NOTE mad: Validate model is registered
                app_config = django_apps.get_app_config(os.environ["SCENERY_TESTED_APP_NAME"])
                app_config.get_model(self.args["find"]["model"].__name__)
            
            case _:
                raise ValueError(
                    f"Cannot interpret '{self.instruction}:({self.args})' as Check"
                )

    @staticmethod
    def _format_dom_element_attribute_value(value: str | int | list[str]) -> list[str] | str:
        if isinstance(value, (str, list)):
            return value
        elif isinstance(value, int):
            return str(value)
        else:
            raise TypeError(
                f"attribute value can only be `str` or `list[str]` not {value} ('{type(value)}')"
            )


@dataclass
class Take:
    """Store all the information after the substitution from the `Cases` has been performed.

    This class represents a fully resolved HTTP request to be executed, including
    the method, URL, data, and checks to be performed.

    Attributes:
        method (http.HTTPMethod): The HTTP method for this take.
        url (str): The fully resolved URL for this take.
        checks (list[Check]): The list of checks to perform on the response.
        data (dict): The data to be sent with the request.
        query_parameters (dict): Query parameters for the URL.
        url_parameters (dict): URL parameters used in URL resolution.

    Notes:
        The `url` is expected to be either a valid URL or a registered viewname.
        If it's a viewname, it will be resolved using Django's `reverse` function.
    """

    method: http.HTTPMethod
    url: str
    checks: list[Check]
    data: dict
    query_parameters: dict
    url_parameters: dict

    def __post_init__(self) -> None:
        self.method = http.HTTPMethod(self.method)

        try:
            # First we try if the url is a django viewname
            url_name = self.url
            self.url = reverse(self.url, kwargs=self.url_parameters)
            self.url_name = url_name
        except NoReverseMatch:
            # Otherwise we check it is a valid url
            parsed = urlparse(self.url)
            if not (parsed.scheme and parsed.netloc):
                raise ValueError(f"'{self.url}' could not be reversed and is not a valid url")

        if self.query_parameters:
            # NOTE mad: We use http.urlencode instead for compatibility
            # https://stackoverflow.com/questions/4995279/including-a-querystring-in-a-django-core-urlresolvers-reverse-call
            # https://gist.github.com/benbacardi/227f924ec1d9bedd242b
            self.url += "?" + urlencode(self.query_parameters)
