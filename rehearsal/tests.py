"""Testcases"""

import http
import unittest
import typing

import scenery.common
from scenery.response_checker import Checker
import scenery.manifest
from scenery.manifest_parser import ManifestParser
from scenery.metatest import MetaFrontTest
from scenery.method_builder import MethodBuilder
import rehearsal
from rehearsal.django_project.some_app.models import SomeModel
from scenery.set_up_handler import SetUpHandler

import django.http
from django.contrib.staticfiles.testing import StaticLiveServerTestCase


#####################
# COMMON
#####################


class TestSingleKeyDict(unittest.TestCase):
    def test(self):
        d: scenery.manifest.SingleKeyDict[str, typing.Any] = scenery.manifest.SingleKeyDict(
            {"key": "value"}
        )
        self.assertEqual(d.key, "key")
        self.assertEqual(d.value, "value")
        self.assertEqual(d.as_tuple(), ("key", "value"))
        with self.assertRaisesRegex(ValueError, r"^SingleKeyDict should have length 1 not '2'"):
            d = scenery.manifest.SingleKeyDict({"1": None, "2": None})


######################
# MANIFEST DATACLASSES
######################


class TestSetUpInstruction(unittest.TestCase):
    def test(self):
        cmd = "reset_db"
        args = {"arg": object()}

        with self.subTest("__init__ without args"):
            instruction = scenery.manifest.SetUpInstruction(cmd)
            self.assertEqual(instruction.command, cmd)
            self.assertEqual(instruction.args, {})

        with self.subTest("__init__ with args"):
            instruction = scenery.manifest.SetUpInstruction(cmd, args)
            self.assertEqual(instruction.command, cmd)
            self.assertEqual(instruction.args, args)

        with self.subTest("from_object"):
            instruction = scenery.manifest.SetUpInstruction.from_object(cmd)
            self.assertEqual(instruction, scenery.manifest.SetUpInstruction(cmd))
            instruction = scenery.manifest.SetUpInstruction.from_object({cmd: args})
            self.assertEqual(instruction, scenery.manifest.SetUpInstruction(cmd, args))


class TestItem(unittest.TestCase):
    def test(self):
        d = {"a": object()}
        item = scenery.manifest.Item("id", d)
        self.assertEqual(item._id, "id")
        self.assertEqual(item["a"], d["a"])


class TestManifestCase(unittest.TestCase):
    # NOTE: the logical name should have been TestCase
    # but this is an incredibly bad name

    def test(self):
        with self.subTest("__init__"):
            case_a = scenery.manifest.Case("id", {"item_id": scenery.manifest.Item("item_id", {})})
            self.assertEqual(case_a._id, "id")
            self.assertEqual(case_a.items, {"item_id": scenery.manifest.Item("item_id", {})})

        with self.subTest("from_id_and_dict"):
            case_b = scenery.manifest.Case.from_id_and_dict("id", {"item_id": {}})
            self.assertEqual(case_a, case_b)


class TesDirective(unittest.TestCase):
    def test(self):
        scenery.manifest.Directive(scenery.manifest.DirectiveCommand("status_code"), 200)
        scenery.manifest.Directive(
            scenery.manifest.DirectiveCommand("redirect_url"), "https://www.example.com"
        )
        scenery.manifest.Directive(
            scenery.manifest.DirectiveCommand("dom_element"), {"find": object()}
        )
        scenery.manifest.Directive(
            scenery.manifest.DirectiveCommand("count_instances"),
            {"model": "SomeModel", "n": 1},
        )
        with self.assertRaises(ValueError):
            scenery.manifest.Directive(scenery.manifest.DirectiveCommand("status_code"), "200")
        with self.assertRaises(ValueError):
            scenery.manifest.Directive(scenery.manifest.DirectiveCommand("redirect_url"), 0)
        with self.assertRaises(ValueError):
            scenery.manifest.Directive(scenery.manifest.DirectiveCommand("dom_element"), 0)
        with self.assertRaises(LookupError):
            scenery.manifest.Directive(
                scenery.manifest.DirectiveCommand("count_instances"),
                {"model": "NotAModel", "n": 1},
            )

        scenery.manifest.Directive.from_dict({"dom_element": {"find": object()}})
        scenery.manifest.Directive.from_dict({"dom_element": {"find": object(), "scope": {}}})
        scenery.manifest.Directive.from_dict({"dom_element": {"find_all": object()}})
        with self.assertRaises(ValueError):
            scenery.manifest.Directive.from_dict({"dom_element": {"scope": {}}})
        with self.assertRaises(ValueError):
            scenery.manifest.Directive.from_dict(
                {"dom_element": {"find": object(), "find_all": object()}}
            )


class TestSubstituable(unittest.TestCase):
    def test(self):
        case = scenery.manifest.Case(
            "id", {"item_id": scenery.manifest.Item("item_id", {"a": object()})}
        )
        sub = scenery.manifest.Substituable("item_id")
        x = sub.shoot(case)
        self.assertDictEqual(x, case["item_id"]._dict)
        sub = scenery.manifest.Substituable("item_id:a")
        x = sub.shoot(case)
        self.assertEqual(x, case["item_id"]["a"])

    def test_regex(self):
        self.assertRegex("item", scenery.manifest.Substituable.regex_field)
        self.assertRegex("item_with_underscore", scenery.manifest.Substituable.regex_field)
        self.assertRegex("item:field", scenery.manifest.Substituable.regex_field)
        self.assertRegex("item:field_with_underscore", scenery.manifest.Substituable.regex_field)
        self.assertNotRegex("item_Uppercase", scenery.manifest.Substituable.regex_field)
        self.assertNotRegex("item_0", scenery.manifest.Substituable.regex_field)
        self.assertNotRegex("item-with-hyphen", scenery.manifest.Substituable.regex_field)
        self.assertNotRegex("item:field_Uppercase", scenery.manifest.Substituable.regex_field)
        self.assertNotRegex("item:field_0", scenery.manifest.Substituable.regex_field)
        self.assertNotRegex("item:field-with-hyphen", scenery.manifest.Substituable.regex_field)


class TestScene(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.scene_base_dict = {
            "method": http.HTTPMethod.GET,
            "url": "https://www.example.com",
            "directives": [{"status_code": 200}],
        }

        case_dict = {
            "item_id": {
                "a": object(),
                "b": object(),
                "status_code": 200,
                "dom_element_id": "id",
                "attribute_value": "value",
            },
        }

        self.case = scenery.manifest.Case.from_id_and_dict("case_id", case_dict)

    def test(self):
        scenery.manifest.Scene(
            http.HTTPMethod.GET,
            "https://www.example.com",
            [scenery.manifest.Directive(scenery.manifest.DirectiveCommand("status_code"), 200)],
            {},
            {},
            {},
        )
        scenery.manifest.Scene.from_dict(
            {
                "method": "GET",
                "url": "https://www.example.com",
                "directives": [{"status_code": 200}],
                "data": [],
                "url_parameters": {},
                "query_parameters": {},
            }
        )

    def test_substitute_recusively(self):
        scene = scenery.manifest.Scene.from_dict(
            self.scene_base_dict
            | {
                "data": scenery.manifest.Substituable("item_id"),
                "url_parameters": scenery.manifest.Substituable("item_id"),
                "directives": [
                    {
                        scenery.manifest.DirectiveCommand.STATUS_CODE: scenery.manifest.Substituable(
                            "item_id:status_code"
                        )
                    }
                ],
            }
        )
        data = scenery.manifest.Scene.substitute_recursively(scene.data, self.case)
        self.assertDictEqual(data, self.case["item_id"]._dict)
        url_parameters = scenery.manifest.Scene.substitute_recursively(
            scene.url_parameters, self.case
        )
        self.assertDictEqual(url_parameters, self.case["item_id"]._dict)
        checks = scenery.manifest.Scene.substitute_recursively(scene.directives, self.case)

        self.assertEqual(
            checks[0],
            scenery.manifest.Check.from_dict(
                {"status_code": self.case["item_id"]["status_code"]}
            ),
        )

    def test_shoot(self):
        scene = scenery.manifest.Scene.from_dict(
            self.scene_base_dict
            | {"data": {"a": scenery.manifest.Substituable("item_id:a")}}
            | {"url_parameters": {"key": scenery.manifest.Substituable("item_id:a")}}
            | {
                "directives": [
                    {
                        "dom_element": {
                            "find": {"id": scenery.manifest.Substituable("item_id:dom_element_id")},
                            "attribute": {
                                "name": "name",
                                "value": scenery.manifest.Substituable("item_id:attribute_value"),
                            },
                        }
                    }
                ]
            }
        )
        take = scene.shoot(self.case)
        self.assertEqual(
            take,
            scenery.manifest.Take(
                method=typing.cast(http.HTTPMethod, self.scene_base_dict["method"]),
                url=typing.cast(str, self.scene_base_dict["url"]),
                data={"a": self.case["item_id"]["a"]},
                url_parameters={"key": self.case["item_id"]["a"]},
                query_parameters={},
                checks=[
                    scenery.manifest.Check(
                        instruction=scenery.manifest.DirectiveCommand.DOM_ELEMENT,
                        args={
                            "find": {
                                "id": self.case["item_id"]["dom_element_id"],
                            },
                            "attribute": {
                                "name": "name",
                                "value": self.case["item_id"]["attribute_value"],
                            },
                        },
                    )
                ],
            ),
        )


class TestManifest(unittest.TestCase):
    def test(self):
        scene = scenery.manifest.Scene(
            http.HTTPMethod.GET,
            "https://www.example.com",
            [scenery.manifest.Directive(scenery.manifest.DirectiveCommand("status_code"), 200)],
            {},
            {},
            {},
        )
        scenes = [scene]
        set_up_test_data = [scenery.manifest.SetUpInstruction("reset_db")]
        set_up = [scenery.manifest.SetUpInstruction("login")]

        cases = {
            "a": scenery.manifest.Case("a", {"item_id": scenery.manifest.Item("item_id", {})}),
            "b": scenery.manifest.Case("b", {"item_id": scenery.manifest.Item("item_id", {})}),
        }

        scenery.manifest.Manifest(set_up_test_data, set_up, scenes, cases, "origin", None)
        scenery.manifest.Manifest.from_formatted_dict(
            {
                "set_up_test_data": ["reset_db"],
                "set_up": ["login"],
                "cases": {"case_id": {"item_id": {}}},
                "scenes": [
                    {
                        "method": "GET",
                        "url": "https://www.example.com",
                        "data": [],
                        "url_parameters": {},
                        "query_parameters": {},
                        "directives": [{"status_code": 200}],
                    }
                ],
                "manifest_origin": "origin",
            }
        )


class TestCheck(unittest.TestCase):
    def test(self):
        class NotAModel:
            pass

        scenery.manifest.Check(scenery.manifest.DirectiveCommand("status_code"), 200)
        scenery.manifest.Check(
            scenery.manifest.DirectiveCommand("redirect_url"), "https://www.example.com"
        )
        scenery.manifest.Check(scenery.manifest.DirectiveCommand("dom_element"), {})
        scenery.manifest.Check(
            scenery.manifest.DirectiveCommand("count_instances"),
            {"model": SomeModel, "n": 1},
        )
        with self.assertRaises(ValueError):
            scenery.manifest.Check(scenery.manifest.DirectiveCommand("status_code"), "200")
        with self.assertRaises(ValueError):
            scenery.manifest.Check(scenery.manifest.DirectiveCommand("redirect_url"), 0)
        with self.assertRaises(ValueError):
            scenery.manifest.Check(scenery.manifest.DirectiveCommand("dom_element"), 0)
        with self.assertRaises(ValueError):
            scenery.manifest.Check(
                scenery.manifest.DirectiveCommand("count_instances"),
                {"model": NotAModel, "n": 1},
            )


class TestTake(unittest.TestCase):
    def test(self):
        take = scenery.manifest.Take(
            http.HTTPMethod.GET,
            "https://www.example.com",
            [scenery.manifest.Check(scenery.manifest.DirectiveCommand("status_code"), 200)],
            {},
            {},
            {},
        )
        self.assertEqual(take.method, http.HTTPMethod.GET)


#################
# MANIFEST PARSER
#################


class TestManifestParser(unittest.TestCase):
    def test_validate_dict(self):
        manifest_base_dict = {
            "set_up_test_data": object(),
            "set_up": object(),
            "cases": object(),
            "scenes": object(),
            "manifest_origin": "origin",
            # "testtype": None,
        }

        # Unknown key
        manifest = manifest_base_dict | {"unknown": object()}
        with self.assertRaises(ValueError):
            ManifestParser.validate_dict(manifest)

        # Both case and cases
        manifest = manifest_base_dict | {"case": object()}
        with self.assertRaisesRegex(
            ValueError,
            r"Both `case` and `cases` keys are present at top level\.$",
        ):
            ManifestParser.validate_dict(manifest)

        # Both scene and scenes
        manifest = manifest_base_dict | {"scene": object()}
        with self.assertRaisesRegex(
            ValueError,
            r"Both `scene` and `scenes` keys are present at top level\.$",
        ):
            ManifestParser.validate_dict(manifest)

        # Neither scene or scenes
        manifest = manifest_base_dict.copy()
        manifest.pop("scenes")
        with self.assertRaisesRegex(
            ValueError,
            r"Neither `scene` and `scenes` keys are present at top level\.$",
        ):
            ManifestParser.validate_dict(manifest)

        # Success all fields
        manifest = manifest_base_dict
        ManifestParser.validate_dict(manifest)

        # Success no optional field
        manifest = manifest_base_dict.copy()
        manifest.pop("set_up")
        manifest.pop("set_up_test_data")
        ManifestParser.validate_dict(manifest)

    def test_format_dict(self):
        scene_a = object()
        scene_b = object()
        case_a = object()
        case_b = object()
        d: dict[str, typing.Any] = {
            "cases": [case_a, case_b],
            "scenes": [scene_a, scene_b],
            "manifest_origin": "origin",
        }
        ManifestParser.validate_dict(d)
        # TODO: is this the best solution for type checking? I do this several times in the file
        manifest = ManifestParser.format_dict(typing.cast(scenery.manifest.RawManifestDict, d))
        self.assertDictEqual(
            manifest,
            {
                "cases": [case_a, case_b],
                "scenes": [scene_a, scene_b],
                "manifest_origin": "origin",
                "set_up_test_data": [],
                "set_up": [],
                "testtype": None
            },
        )
        d = {
            "case": case_a,
            "scene": scene_a,
            "manifest_origin": "origin",
            "set_up_test_data": ["a", "b"],
            "set_up": ["c", "d"],
        }
        ManifestParser.validate_dict(d)
        manifest = ManifestParser.format_dict(typing.cast(scenery.manifest.RawManifestDict, d))
        self.assertDictEqual(
            manifest,
            {
                "cases": {"CASE": case_a},
                "scenes": [scene_a],
                "manifest_origin": "origin",
                "set_up_test_data": ["a", "b"],
                "set_up": ["c", "d"],
                "testtype": None
            },
        )

    def test__format_dict_scenes(self):
        scene_1 = object()
        scene_2 = object()
        base_dict = {
            "cases": object(),
            "manifest_origin": "origin",
        }

        # Single scene
        d = base_dict | {"scene": scene_1}
        ManifestParser.validate_dict(d)
        manifest = typing.cast(scenery.manifest.RawManifestDict, d)
        scenes = ManifestParser._format_dict_scenes(manifest)
        self.assertListEqual(scenes, [scene_1])

        # Single scene in scenes
        d = base_dict | {"scenes": [scene_1]}
        ManifestParser.validate_dict(d)
        manifest = typing.cast(scenery.manifest.RawManifestDict, d)
        scenes = ManifestParser._format_dict_scenes(manifest)
        self.assertListEqual(scenes, [scene_1])

        # Scenes
        d = base_dict | {"scenes": [scene_1, scene_2]}
        ManifestParser.validate_dict(d)
        manifest = typing.cast(scenery.manifest.RawManifestDict, d)
        scenes = ManifestParser._format_dict_scenes(manifest)
        self.assertListEqual(scenes, [scene_1, scene_2])

    def test__format_dict_cases(self):
        case_1 = object()
        case_2 = object()
        base_dict = {
            "scenes": object(),
            "manifest_origin": "origin",
        }

        # Single case
        d = base_dict | {"case": case_1}
        ManifestParser.validate_dict(d)
        manifest = typing.cast(scenery.manifest.RawManifestDict, d)
        cases = ManifestParser._format_dict_cases(manifest)
        self.assertDictEqual(cases, {"CASE": case_1})

        # Single case in cases
        d = base_dict | {"cases": {"case_id": case_1}}
        ManifestParser.validate_dict(d)
        manifest = typing.cast(scenery.manifest.RawManifestDict, d)
        cases = ManifestParser._format_dict_cases(manifest)
        self.assertDictEqual(cases, {"case_id": case_1})

        # Cases
        d = base_dict | {"cases": {"case_1": case_1, "case_2": case_2}}
        ManifestParser.validate_dict(d)
        manifest = typing.cast(scenery.manifest.RawManifestDict, d)
        cases = ManifestParser._format_dict_cases(manifest)
        self.assertDictEqual(cases, {"case_1": case_1, "case_2": case_2})

    def test_parse_dict(self):
        d = {
            "case": {},
            "scene": {
                "method": "GET",
                "url": "https://www.example.com",
                "directives": [{"status_code": 200}],
            },
            "manifest_origin": "origin",
            "set_up_test_data": ["reset_db"],
            "set_up": ["create_testuser"],
        }
        ManifestParser.parse_dict(d)
        d.pop("scene")
        with self.assertRaises(ValueError):
            ManifestParser.parse_dict(d)

    def test_validate_yaml(self):
        # success
        manifest = {
            "cases": object(),
            "scenes": object(),
            "manifest_origin": "origin",
        }
        ManifestParser.validate_yaml(manifest)


#################
# CHECKER
#################


class TestChecker(rehearsal.TestCaseOfDjangoTestCase):
    def test_check_status_code(self):
        response = django.http.HttpResponse()
        response.status_code = 200

        def test_pass(django_testcase):
            Checker.check_status_code(django_testcase, response, 200)

        def test_fail(django_testcase):
            Checker.check_status_code(django_testcase, response, 400)

        setattr(self.django_testcase, "test_pass", test_pass)
        setattr(self.django_testcase, "test_fail", test_fail)

        self.assertTestPasses(self.django_testcase("test_pass"))
        self.assertTestFails(self.django_testcase("test_fail"))

    def test_check_redirect_url(self):
        response = django.http.HttpResponseRedirect(redirect_to="somewhere")

        def test_pass(django_testcase):
            Checker.check_redirect_url(django_testcase, response, "somewhere")

        def test_fail(django_testcase):
            Checker.check_redirect_url(django_testcase, response, "elsewhere")

        setattr(self.django_testcase, "test_pass", test_pass)
        setattr(self.django_testcase, "test_fail", test_fail)

        self.assertTestPasses(self.django_testcase("test_pass"))
        self.assertTestFails(self.django_testcase("test_fail"))

    def test_check_count_instances(self):
        # NOTE As the method below is tested in TestSetUpInstructions we assume it is working
        SetUpHandler.exec_set_up_instruction(
            self.django_testcase, scenery.manifest.SetUpInstruction("reset_db", {})
        )
        response = django.http.HttpResponse()

        def test_pass(django_testcase):
            Checker.check_count_instances(
                django_testcase, response, {"model": SomeModel, "n": 0}
            )

        def test_fail(django_testcase):
            Checker.check_count_instances(
                django_testcase, response, {"model": SomeModel, "n": 1}
            )

        def test_error(django_testcase):
            class UndefinedModel:
                pass

            Checker.check_count_instances(
                django_testcase, response, {"model": UndefinedModel, "n": 1}
            )

        setattr(self.django_testcase, "test_pass", test_pass)
        setattr(self.django_testcase, "test_fail", test_fail)
        setattr(self.django_testcase, "test_error", test_error)

        self.assertTestPasses(self.django_testcase("test_pass"))
        self.assertTestFails(self.django_testcase("test_fail"))
        self.assertTestRaises(self.django_testcase("test_error"), Exception)

    def test_check_dom_element(self):
        def test_pass_find_by_id(django_testcase):
            response = django.http.HttpResponse()
            response.content = '<div id="target">Pass</div>'
            Checker.check_dom(
                django_testcase,
                response,
                {scenery.manifest.DomArgument.FIND: {"id": "target"}},
            )

        def test_pass_find_by_class(django_testcase):
            response = django.http.HttpResponse()
            response.content = '<div class="target">Pass</div>'
            Checker.check_dom(
                django_testcase,
                response,
                {scenery.manifest.DomArgument.FIND: {"class": "target"}},
            )

        def test_pass_text(django_testcase):
            response = django.http.HttpResponse()
            response.content = '<div id="target">Pass</div>'
            Checker.check_dom(
                django_testcase,
                response,
                {
                    scenery.manifest.DomArgument.FIND: {"id": "target"},
                    scenery.manifest.DomArgument.TEXT: "Pass",
                },
            )

        def test_pass_attribute(django_testcase):
            response = django.http.HttpResponse()
            response.content = '<div id="target" class="something">Pass</div>'
            Checker.check_dom(
                django_testcase,
                response,
                {
                    scenery.manifest.DomArgument.FIND: {"id": "target"},
                    scenery.manifest.DomArgument.ATTRIBUTE: {
                        "name": "class",
                        "value": ["something"],
                    },
                },
            )

        def test_pass_find_all(django_testcase):
            response = django.http.HttpResponse()
            response.content = '<div class="something">Pass</div> <div class="something">Pass</div>'
            Checker.check_dom(
                django_testcase,
                response,
                {
                    scenery.manifest.DomArgument.FIND_ALL: {"class": "something"},
                    scenery.manifest.DomArgument.COUNT: 2,
                },
            )

        def test_pass_scope(django_testcase):
            response = django.http.HttpResponse()
            response.content = '<div id="scope"> <div class="something">In</div> <div class="something">In</div> </div> <div class="something">'
            Checker.check_dom(
                django_testcase,
                response,
                {
                    scenery.manifest.DomArgument.SCOPE: {"id": "scope"},
                    scenery.manifest.DomArgument.FIND_ALL: {"class": "something"},
                    scenery.manifest.DomArgument.COUNT: 2,
                },
            )

        def test_fail_1(django_testcase):
            response = django.http.HttpResponse()
            response.content = '<div id="target">Pass</div>'
            Checker.check_dom(
                django_testcase,
                response,
                {scenery.manifest.DomArgument.FIND: {"id": "another_target"}},
            )

        def test_fail_2(django_testcase):
            response = django.http.HttpResponse()
            response.content = '<div id="target">Pass</div>'
            Checker.check_dom(
                django_testcase,
                response,
                {
                    scenery.manifest.DomArgument.FIND: {"id": "target"},
                    scenery.manifest.DomArgument.TEXT: "Fail",
                },
            )

        def test_fail_3(django_testcase):
            response = django.http.HttpResponse()
            response.content = '<div id="target" class="something">Pass</div>'
            Checker.check_dom(
                django_testcase,
                response,
                {
                    scenery.manifest.DomArgument.FIND: {"id": "target"},
                    scenery.manifest.DomArgument.ATTRIBUTE: {
                        "name": "class",
                        "value": ["something_else"],
                    },
                },
            )

        def test_error_1(django_testcase):
            response = django.http.HttpResponse()
            response.content = '<div id="target" class="something">Pass</div>'
            Checker.check_dom(
                django_testcase,
                response,
                {},
            )

        setattr(self.django_testcase, "test_pass_find_by_id", test_pass_find_by_id)
        setattr(self.django_testcase, "test_pass_find_by_class", test_pass_find_by_class)
        setattr(self.django_testcase, "test_pass_text", test_pass_text)
        setattr(self.django_testcase, "test_pass_attribute", test_pass_attribute)
        setattr(self.django_testcase, "test_pass_find_all", test_pass_find_all)
        setattr(self.django_testcase, "test_pass_scope", test_pass_scope)
        setattr(self.django_testcase, "test_fail_1", test_fail_1)
        setattr(self.django_testcase, "test_fail_2", test_fail_2)
        setattr(self.django_testcase, "test_fail_3", test_fail_3)
        setattr(self.django_testcase, "test_error_1", test_error_1)

        self.assertTestPasses(self.django_testcase("test_pass_find_by_id"))
        self.assertTestPasses(self.django_testcase("test_pass_find_by_class"))
        self.assertTestPasses(self.django_testcase("test_pass_attribute"))
        self.assertTestPasses(self.django_testcase("test_pass_text"))
        self.assertTestPasses(self.django_testcase("test_pass_find_all"))
        self.assertTestPasses(self.django_testcase("test_pass_scope"))
        self.assertTestFails(self.django_testcase("test_fail_1"))
        self.assertTestFails(self.django_testcase("test_fail_2"))
        self.assertTestFails(self.django_testcase("test_fail_3"))
        self.assertTestRaises(self.django_testcase("test_error_1"), ValueError)


################
# METHOD BUILDER
################


class TestMethodBuilder(rehearsal.TestCaseOfDjangoTestCase):
    exec_order: list[str] = []

    def test_execution_order(self):
        """
        We check the setUpTestData function is executed before the tests and only once
        As opposed to setUp
        Note that currently, there is only one single test by TestCase (ie by Take)
        But we could therefore easily go beyond
        """
        print(scenery.common.colorize("yellow", "execution order skipped, needs to be fixed."))
        self.skipTest("")
        # NOTE mad: do not erase code below

        # # Reset class attribute
        # TestMethodBuilder.exec_order = []

        # take = scenery.manifest.Take(
        #     http.HTTPMethod.GET, "http://127.0.0.1:8000/hello/", [], {}, {}, {}
        # )

        # @typing.overload
        # def watch(func: classmethod) -> classmethod: ...

        # @typing.overload
        # def watch(func: typing.Callable) -> typing.Callable: ...

        # def watch(func: typing.Callable | classmethod) -> typing.Callable | classmethod:
        #     def wrapper(*args, **kwargs):
        #         if isinstance(func, classmethod):
        #             # NOTE: otherwise the call fails
        #             method = func.__get__(None, self.django_testcase)
        #             x = method(*args, **kwargs)
        #         else:
        #             x = func(*args, **kwargs)

        #         TestMethodBuilder.exec_order.append(func.__name__)
        #         return x

        #     return wrapper if not isinstance(func, classmethod) else classmethod(wrapper)

        # setattr(self.django_testcase, "setUpTestData", watch(MethodBuilder.build_setUpTestData([])))
        # setattr(self.django_testcase, "setUp", watch(MethodBuilder.build_setUp([])))

        # test_1 = MethodBuilder.build_test_from_take(take)
        # test_1.__name__ = "test_1"
        # test_2 = MethodBuilder.build_test_from_take(take)
        # test_2.__name__ = "test_2"

        # setattr(self.django_testcase, "test_1", watch(test_1))
        # setattr(self.django_testcase, "test_2", watch(test_2))

        # self.run_django_testcase()

        # self.assertListEqual(
        #     TestMethodBuilder.exec_order,
        #     ["setUpTestData", "setUp", "test_1", "setUp", "test_2"],
        # )

    def test_persistency_test_data(self):
        # Check the persistency of data created during tests
        setattr(
            self.django_testcase,
            "setUpTestData",
            MethodBuilder.build_setUpTestData(
                [
                    scenery.manifest.SetUpInstruction("reset_db"),
                    scenery.manifest.SetUpInstruction(
                        "create_some_instance",
                        {
                            "some_field": "some_value",
                        },
                    ),
                ]
            ),
        )

        def test_1(django_testcase):
            # NOTE: the assertion is done on the unittest.TestCase and not the django.TestCase
            instances = SomeModel.objects.all()
            self.assertEqual(len(instances), 1)

        def test_2(django_testcase):
            # NOTE: the assertion is done on the unittest.TestCase and not the django.TestCase
            SetUpHandler.exec_set_up_instruction(
                django_testcase,
                scenery.manifest.SetUpInstruction(
                    "create_some_instance", {"some_field": "another_value"}
                ),
            )
            instances = SomeModel.objects.all()
            self.assertEqual(len(instances), 2)

        setattr(self.django_testcase, "test_1", test_1)
        setattr(self.django_testcase, "test_2", test_2)

        self.assertTestPasses(self.django_testcase("test_1"))
        self.assertTestPasses(self.django_testcase("test_2"))


#################
# SELENIUM
#################

class TestSelenium(unittest.TestCase):

    def test_json_stringify(self):

        # Dummy manifest jjust to init the frontend test class
        d = {
            "case": {},
            "scene": {
                "method": "GET",
                "url": "https://www.example.com",
                "directives": [{"status_code": 200}],
            },
            "manifest_origin": "origin",
        }
        manifest = ManifestParser.parse_dict(d)
        frontend_test_cls = MetaFrontTest(
                "some_manifest.frontend",
                (StaticLiveServerTestCase,),
                manifest,
            )
        frontend_test_cls.setUpClass()

        # Basic list 
        attribute_value = "[1, 2, 3]"
        val = frontend_test_cls.driver.execute_script(
            f"return JSON.stringify({attribute_value})"
        )
        self.assertEqual(val, "[1,2,3]")

        # Actual correction format
        attribute_value = '{"1": [true, ""], 2: [true, ""], 3: [false, "Some exception"]}'
        val = frontend_test_cls.driver.execute_script(
            f"return JSON.stringify({attribute_value})"
        )
        self.assertEqual(val, '{"1":[true,""],"2":[true,""],"3":[false,"Some exception"]}')

        attribute_value = '{1: [true,""], 2}'
        with self.assertRaises(Exception) as e:
            val = frontend_test_cls.driver.execute_script(
                f"return JSON.stringify({attribute_value})"
                )
            

        attribute_value = '{"1": [true, ""], 2: [true, ""]'
        with self.assertRaises(Exception):
            val = frontend_test_cls.driver.execute_script(
                f"return JSON.stringify({attribute_value})"
                )

    def test_cache(self):
        d = {
            "case": {},
            "scene": {
                "method": "GET",
                "url": "https://www.example.com",
                "directives": [{"status_code": 200}],
            },
            "manifest_origin": "origin",
            "set_up_test_data": ["reset_db"],
            "set_up": ["create_testuser"],
        }
        manifest = ManifestParser.parse_dict(d)

        # Create first test class instance and check initial cache
        frontend_test_cls = MetaFrontTest(
                "some_manifest.frontend",
                (StaticLiveServerTestCase,),
                manifest,
            )
        frontend_test_cls.setUpClass()
        initial_cache = frontend_test_cls.driver.execute_script("""
            const entries = performance.getEntriesByType('resource');
            return entries.map(entry => ({
                url: entry.name,
                transferSize: entry.transferSize,
                type: entry.initiatorType
            }));
        """)

        self.assertListEqual(initial_cache, [])

        # TODO mad: finish the test

        # # Add an entry to the cache
        # test_url = 'https://www.example.com/test-resource'
        # frontend_test_cls.driver.execute_script("""
        #     // Create a new request and cache it
        #     fetch('https://www.example.com/test-resource', {
        #         method: 'GET',
        #         cache: 'force-cache'  // This forces the browser to cache the response
        #     }).then(response => {
        #         // Optional: You can do something with the response here
        #         console.log('Resource cached');
        #     });
        # """)
        # # Verify the cache entry was added
        # updated_cache = frontend_test_cls.driver.execute_script("""
        #     const entries = performance.getEntriesByType('resource');
        #     return entries.map(entry => ({
        #         url: entry.name,
        #         transferSize: entry.transferSize,
        #         type: entry.initiatorType
        #     }));
        # """)

        # # Assert the new resource is in the cache
        # cached_urls = [entry['url'] for entry in updated_cache]
        # self.assertIn(
        #     test_url,
        #     cached_urls,
        #     f"Expected {test_url} to be in cache. Current cache entries: {cached_urls}"
        # )
        
        # Optionally, verify it's a new entry by comparing with initial cache
        # initial_urls = [entry['url'] for entry in initial_cache]
        # self.assertNotIn(
        #     test_url,
        #     initial_urls,
        #     f"URL {test_url} should not be in initial cache"
        # )

        # # Add something to the cache
        # frontend_test_cls.driver.cache['test_key'] = 'test_value'
        
        # Create a new test class instance with the same manifest
        # new_frontend_test_cls = MetaFrontTest(
        #     "some_manifest.frontend",
        #     (StaticLiveServerTestCase,),
        #     manifest,
        # )
        # new_frontend_test_cls.setUpClass()


        # new_cache = new_frontend_test_cls.driver.execute_script("""
        #     const entries = performance.getEntriesByType('resource');
        #     return entries.map(entry => ({
        #         url: entry.name,
        #         transferSize: entry.transferSize,
        #         type: entry.initiatorType
        #     }));
        # """)

        # new_urls = [entry['url'] for entry in new_cache]
        # self.assertNotIn(
        #     test_url,
        #     new_urls,
        #     f"URL {test_url} should not be in initial cache"
        # )

        # # from pprint import pprint
        # # pprint(new_cache)
        
        # # Assertions
        # self.assertIn('test_key', initial_cache)
        # self.assertEqual(initial_cache['test_key'], 'test_value')
        # self.assertNotIn('test_key', new_cache, "Cache should be cleared for new test instance")
