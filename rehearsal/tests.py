"""Testcases"""

import http
import unittest

import scenery.common
from scenery.http_checker import HttpChecker
import scenery.manifest
from scenery.manifest_parser import ManifestParser
from scenery.method_builder import MethodBuilder
import rehearsal
from rehearsal.project_django.some_app.models import SomeModel
from scenery.set_up_handler import SetUpHandler

import django.http

#####################
# COMMON
#####################


class TestSingleKeyDict(unittest.TestCase):
    def test(self):
        d = scenery.manifest.SingleKeyDict({"key": "value"})
        self.assertEqual(d.key, "key")
        self.assertEqual(d.value, "value")
        self.assertEqual(d.as_tuple(), ("key", "value"))
        with self.assertRaisesRegex(ValueError, r"^SingleKeyDict should have length 1 not '2'"):
            d = scenery.manifest.SingleKeyDict({"1": None, "2": None})


#####################
# MANIFEST DATCLASSES
#####################


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


class TestHttpDirective(unittest.TestCase):
    def test(self):
        scenery.manifest.HttpDirective(scenery.manifest.DirectiveCommand("status_code"), 200)
        scenery.manifest.HttpDirective(
            scenery.manifest.DirectiveCommand("redirect_url"), "https://www.example.com"
        )
        scenery.manifest.HttpDirective(
            scenery.manifest.DirectiveCommand("dom_element"), {"find": object()}
        )
        scenery.manifest.HttpDirective(
            scenery.manifest.DirectiveCommand("count_instances"),
            {"model": "SomeModel", "n": 1},
        )
        with self.assertRaises(ValueError):
            scenery.manifest.HttpDirective(scenery.manifest.DirectiveCommand("status_code"), "200")
        with self.assertRaises(ValueError):
            scenery.manifest.HttpDirective(scenery.manifest.DirectiveCommand("redirect_url"), 0)
        with self.assertRaises(ValueError):
            scenery.manifest.HttpDirective(scenery.manifest.DirectiveCommand("dom_element"), 0)
        with self.assertRaises(LookupError):
            scenery.manifest.HttpDirective(
                scenery.manifest.DirectiveCommand("count_instances"),
                {"model": "NotAModel", "n": 1},
            )

        scenery.manifest.HttpDirective.from_dict({"dom_element": {"find": object()}})
        scenery.manifest.HttpDirective.from_dict({"dom_element": {"find": object(), "scope": {}}})
        scenery.manifest.HttpDirective.from_dict({"dom_element": {"find_all": object()}})
        with self.assertRaises(ValueError):
            scenery.manifest.HttpDirective.from_dict({"dom_element": {"scope": {}}})
        with self.assertRaises(ValueError):
            scenery.manifest.HttpDirective.from_dict(
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


class TestHttpScene(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.scene_base_dict = {
            "method": "GET",
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
        scenery.manifest.HttpScene(
            "GET",
            "https://www.example.com",
            [scenery.manifest.HttpDirective(scenery.manifest.DirectiveCommand("status_code"), 200)],
            [],
            {},
            {},
        )
        scenery.manifest.HttpScene.from_dict(
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
        scene = scenery.manifest.HttpScene.from_dict(
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
        data = scenery.manifest.HttpScene.substitute_recursively(scene.data, self.case)
        self.assertDictEqual(data, self.case["item_id"]._dict)
        url_parameters = scenery.manifest.HttpScene.substitute_recursively(
            scene.url_parameters, self.case
        )
        self.assertDictEqual(url_parameters, self.case["item_id"]._dict)
        checks = scenery.manifest.HttpScene.substitute_recursively(scene.directives, self.case)

        self.assertEqual(
            checks[0],
            scenery.manifest.HttpCheck.from_dict(
                {"status_code": self.case["item_id"]["status_code"]}
            ),
        )

    def test_shoot(self):
        scene = scenery.manifest.HttpScene.from_dict(
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
            scenery.manifest.HttpTake(
                method=self.scene_base_dict["method"],
                url=self.scene_base_dict["url"],
                data={"a": self.case["item_id"]["a"]},
                url_parameters={"key": self.case["item_id"]["a"]},
                query_parameters={},
                checks=[
                    scenery.manifest.HttpCheck(
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
        scene = scenery.manifest.HttpScene(
            "GET",
            "https://www.example.com",
            [scenery.manifest.HttpDirective(scenery.manifest.DirectiveCommand("status_code"), 200)],
            [],
            {},
            {},
        )
        scenes = [scene]
        set_up_test_data = [scenery.manifest.SetUpInstruction("reset_db")]
        set_up = [scenery.manifest.SetUpInstruction("login")]
        cases = [
            scenery.manifest.Case("a", [scenery.manifest.Item("item_id", {})]),
            scenery.manifest.Case("b", [scenery.manifest.Item("item_id", {})]),
        ]

        scenery.manifest.Manifest(set_up_test_data, set_up, scenes, cases, "origin")
        scenery.manifest.Manifest.from_formatted_dict(
            {
                scenery.manifest.ManifestFormattedDictKeys.SET_UP_TEST_DATA: ["reset_db"],
                scenery.manifest.ManifestFormattedDictKeys.SET_UP: ["login"],
                scenery.manifest.ManifestFormattedDictKeys.CASES: {"case_id": {"item_id": {}}},
                scenery.manifest.ManifestFormattedDictKeys.SCENES: [
                    {
                        "method": "GET",
                        "url": "https://www.example.com",
                        "data": [],
                        "url_parameters": {},
                        "query_parameters": {},
                        "directives": [{"status_code": 200}],
                    }
                ],
                scenery.manifest.ManifestFormattedDictKeys.MANIFEST_ORIGIN: "origin",
            }
        )


class TestHttpCheck(unittest.TestCase):
    def test(self):
        class NotAModel:
            pass

        scenery.manifest.HttpCheck(scenery.manifest.DirectiveCommand("status_code"), 200)
        scenery.manifest.HttpCheck(
            scenery.manifest.DirectiveCommand("redirect_url"), "https://www.example.com"
        )
        scenery.manifest.HttpCheck(scenery.manifest.DirectiveCommand("dom_element"), {})
        scenery.manifest.HttpCheck(
            scenery.manifest.DirectiveCommand("count_instances"),
            {"model": SomeModel, "n": 1},
        )
        with self.assertRaises(ValueError):
            scenery.manifest.HttpCheck(scenery.manifest.DirectiveCommand("status_code"), "200")
        with self.assertRaises(ValueError):
            scenery.manifest.HttpCheck(scenery.manifest.DirectiveCommand("redirect_url"), 0)
        with self.assertRaises(ValueError):
            scenery.manifest.HttpCheck(scenery.manifest.DirectiveCommand("dom_element"), 0)
        with self.assertRaises(ValueError):
            scenery.manifest.HttpCheck(
                scenery.manifest.DirectiveCommand("count_instances"),
                {"model": NotAModel, "n": 1},
            )


class TestHttpTake(unittest.TestCase):
    def test(self):
        take = scenery.manifest.HttpTake(
            "GET",
            "https://www.example.com",
            [scenery.manifest.HttpDirective(scenery.manifest.DirectiveCommand("status_code"), 200)],
            [],
            {},
            {},
        )
        self.assertEqual(take.method, http.HTTPMethod.GET)


#################
# MANIFEST PARSER
#################


class TestManifestParser(unittest.TestCase):
    def test_parse_formatted_dict(self):
        d = {
            "set_up_test_data": [],
            "set_up": [],
            "cases": {},
            "scenes": [],
            "manifest_origin": "origin",
        }
        ManifestParser.parse_formatted_dict(d)
        d.pop("cases")
        with self.assertRaises(KeyError):
            ManifestParser.parse_formatted_dict(d)

    def test_validate_dict(self):
        manifest_base_dict = {
            "set_up_test_data": object(),
            "set_up": object(),
            "cases": object(),
            "scenes": object(),
            "manifest_origin": "origin",
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

        # Neither case or cases, this now allowed
        # manifest = manifest_base_dict.copy()
        # manifest.pop("cases")
        # with self.assertRaisesRegex(
        #     ValueError,
        #     r"Neither `case` and `cases` keys are present at top level\.$",
        # ):
        #     ManifestParser.validate_dict(manifest)

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
        scene_1 = object()
        scene_2 = object()
        case_1 = object()
        case_2 = object()
        manifest = {
            "cases": [case_1, case_2],
            "scenes": [scene_1, scene_2],
            "manifest_origin": "origin",
        }
        ManifestParser.validate_dict(manifest)
        manifest = ManifestParser.format_dict(manifest)
        self.assertDictEqual(
            manifest,
            {
                "cases": [case_1, case_2],
                "scenes": [scene_1, scene_2],
                "manifest_origin": "origin",
                "set_up_test_data": [],
                "set_up": [],
            },
        )
        manifest = {
            "case": case_1,
            "scene": scene_1,
            "manifest_origin": "origin",
            "set_up_test_data": ["a", "b"],
            "set_up": ["c", "d"],
        }
        ManifestParser.validate_dict(manifest)
        manifest = ManifestParser.format_dict(manifest)
        self.assertDictEqual(
            manifest,
            {
                "cases": {"CASE": case_1},
                "scenes": [scene_1],
                "manifest_origin": "origin",
                "set_up_test_data": ["a", "b"],
                "set_up": ["c", "d"],
            },
        )

    def test__format_dict_scenes(self):
        scene_1 = object()
        scene_2 = object()
        manifest_base_dict = {
            "cases": object(),
            "manifest_origin": "origin",
        }

        # Single scene
        manifest = manifest_base_dict | {"scene": scene_1}
        ManifestParser.validate_dict(manifest)
        scenes = ManifestParser._format_dict_scenes(manifest)
        self.assertListEqual(scenes, [scene_1])

        # Single scene in scenes
        manifest = manifest_base_dict | {"scenes": [scene_1]}
        ManifestParser.validate_dict(manifest)
        scenes = ManifestParser._format_dict_scenes(manifest)
        self.assertListEqual(scenes, [scene_1])

        # Scenes
        manifest = manifest_base_dict | {"scenes": [scene_1, scene_2]}
        ManifestParser.validate_dict(manifest)
        scenes = ManifestParser._format_dict_scenes(manifest)
        self.assertListEqual(scenes, [scene_1, scene_2])

    def test__format_dict_cases(self):
        case_1 = object()
        case_2 = object()
        manifest_base_dict = {
            "scenes": object(),
            "manifest_origin": "origin",
        }

        # Single case
        manifest = manifest_base_dict | {"case": case_1}
        ManifestParser.validate_dict(manifest)
        cases = ManifestParser._format_dict_cases(manifest)
        self.assertDictEqual(cases, {"CASE": case_1})

        # Single case in cases
        manifest = manifest_base_dict | {"cases": {"case_id": case_1}}
        ManifestParser.validate_yaml(manifest)
        cases = ManifestParser._format_dict_cases(manifest)
        self.assertDictEqual(cases, {"case_id": case_1})

        # Cases
        manifest = manifest_base_dict | {"cases": {"case_1": case_1, "case_2": case_2}}
        ManifestParser.validate_dict(manifest)
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
        # wrong type
        manifest = []
        with self.assertRaisesRegex(
            TypeError, r"^Manifest need to be a dict not a '<class 'list'>'$"
        ):
            ManifestParser.validate_yaml(manifest)

        # success
        manifest = {
            "variables": object(),
            "cases": object(),
            "scenes": object(),
            "manifest_origin": "origin",
        }
        ManifestParser.validate_yaml(manifest)


#################
# HTTP CHECKER
#################


class TestHttpChecker(rehearsal.TestCaseOfDjangoTestCase):
    def test_check_status_code(self):
        response = django.http.HttpResponse()
        response.status_code = 200

        def test_pass(django_testcase):
            HttpChecker.check_status_code(django_testcase, response, 200)

        def test_fail(django_testcase):
            HttpChecker.check_status_code(django_testcase, response, 400)

        self.django_testcase.test_pass = test_pass
        self.django_testcase.test_fail = test_fail

        self.assertTestPasses(self.django_testcase("test_pass"))
        self.assertTestFails(self.django_testcase("test_fail"))

    def test_check_redirect_url(self):
        response = django.http.HttpResponseRedirect(redirect_to="somewhere")

        def test_pass(django_testcase):
            HttpChecker.check_redirect_url(django_testcase, response, "somewhere")

        def test_fail(django_testcase):
            HttpChecker.check_redirect_url(django_testcase, response, "elsewhere")

        self.django_testcase.test_pass = test_pass
        self.django_testcase.test_fail = test_fail

        self.assertTestPasses(self.django_testcase("test_pass"))
        self.assertTestFails(self.django_testcase("test_fail"))

    def test_check_count_instances(self):
        # NOTE As the method below is tested in TestSetUpInstructions we assume it is working
        SetUpHandler.exec_set_up_instruction(
            self.django_testcase, scenery.manifest.SetUpInstruction("reset_db", {})
        )
        response = django.http.HttpResponse()

        def test_pass(django_testcase):
            HttpChecker.check_count_instances(
                django_testcase, response, {"model": SomeModel, "n": 0}
            )

        def test_fail(django_testcase):
            HttpChecker.check_count_instances(
                django_testcase, response, {"model": SomeModel, "n": 1}
            )

        def test_error(django_testcase):
            class UndefinedModel:
                pass

            HttpChecker.check_count_instances(
                django_testcase, response, {"model": UndefinedModel, "n": 1}
            )

        self.django_testcase.test_pass = test_pass
        self.django_testcase.test_fail = test_fail
        self.django_testcase.test_error = test_error

        self.assertTestPasses(self.django_testcase("test_pass"))
        self.assertTestFails(self.django_testcase("test_fail"))
        self.assertTestRaises(self.django_testcase("test_error"), Exception)

    def test_check_dom_element(self):
        def test_pass_find_by_id(django_testcase):
            response = django.http.HttpResponse()
            response.content = '<div id="target">Pass</div>'
            HttpChecker.check_dom_element(
                django_testcase,
                response,
                {scenery.manifest.DomArgument.FIND: {"id": "target"}},
            )

        def test_pass_find_by_class(django_testcase):
            response = django.http.HttpResponse()
            response.content = '<div class="target">Pass</div>'
            HttpChecker.check_dom_element(
                django_testcase,
                response,
                {scenery.manifest.DomArgument.FIND: {"class": "target"}},
            )

        def test_pass_text(django_testcase):
            response = django.http.HttpResponse()
            response.content = '<div id="target">Pass</div>'
            HttpChecker.check_dom_element(
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
            HttpChecker.check_dom_element(
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
            HttpChecker.check_dom_element(
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
            HttpChecker.check_dom_element(
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
            HttpChecker.check_dom_element(
                django_testcase,
                response,
                {scenery.manifest.DomArgument.FIND: {"id": "another_target"}},
            )

        def test_fail_2(django_testcase):
            response = django.http.HttpResponse()
            response.content = '<div id="target">Pass</div>'
            HttpChecker.check_dom_element(
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
            HttpChecker.check_dom_element(
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
            HttpChecker.check_dom_element(
                django_testcase,
                response,
                {},
            )

        self.django_testcase.test_pass_find_by_id = test_pass_find_by_id
        self.django_testcase.test_pass_find_by_class = test_pass_find_by_class
        self.django_testcase.test_pass_text = test_pass_text
        self.django_testcase.test_pass_attribute = test_pass_attribute
        self.django_testcase.test_pass_find_all = test_pass_find_all
        self.django_testcase.test_pass_scope = test_pass_scope
        self.django_testcase.test_fail_1 = test_fail_1
        self.django_testcase.test_fail_2 = test_fail_2
        self.django_testcase.test_fail_3 = test_fail_3
        self.django_testcase.test_error_1 = test_error_1

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
    exec_order = []

    def test_execution_order(self):
        """
        We check the setUpTestData function is executed before the tests and only once
        As opposed to setUp
        Note that currently, there is only one single test by TestCase (ie by Take)
        But we could therefore easily go beyond
        """

        # Reset class attribute
        TestMethodBuilder.exec_order = []

        # take = scenery.manifest.HttpTake(
        #     http.HTTPMethod.GET, "https://www.example.com", [], {}, {}, {}
        # )
        take = scenery.manifest.HttpTake(
            http.HTTPMethod.GET, "http://127.0.0.1:8000/hello/", [], {}, {}, {}
        )

        def watch(func):
            def wrapper(*args, **kwargs):
                # print("beginning with exec_order")
                # print(TestMethodBuilder.exec_order)
                # print("trying this func.__name__")
                # print(func.__name__)
                # print(type(func))
                if type(func) is classmethod:
                    # print("is_class_method")
                    # otherwise the call fails
                    method = func.__get__(self.django_testcase, type(self.django_testcase))
                    x = method(*args, **kwargs)
                else:
                    # print("is_not_class_method")
                    # print("args")
                    # print(args)
                    # print("kwargs")
                    # print(kwargs)
                    x = func(*args, **kwargs)
                #     print("execution_succedded")

                # print(x)
                # print("exec order before append")
                # print(TestMethodBuilder.exec_order)
                TestMethodBuilder.exec_order.append(func.__name__)
                # print("ending with exec_order")
                # print(TestMethodBuilder.exec_order)

                # print("\n\n")
                return x

            return wrapper

        self.django_testcase.setUpTestData = watch(MethodBuilder.build_setUpTestData([]))
        self.django_testcase.setUp = watch(MethodBuilder.build_setUp([]))

        test_1 = MethodBuilder.build_test_from_take(take)
        test_1.__name__ = "test_1"
        test_2 = MethodBuilder.build_test_from_take(take)
        test_2.__name__ = "test_2"

        self.django_testcase.test_1 = watch(test_1)
        self.django_testcase.test_2 = watch(test_2)

        self.run_django_testcase()

        # print("self.django_testcase.test_1", self.django_testcase.test_1)
        # print("self.django_testcase.test_2", self.django_testcase.test_2)

        self.assertListEqual(
            # self.django_testcase.execution_order,
            TestMethodBuilder.exec_order,
            ["setUpTestData", "setUp", "test_1", "setUp", "test_2"],
        )

    def test_persistency_test_data(self):
        # Check the persistency of data created during tests
        self.django_testcase.setUpTestData = MethodBuilder.build_setUpTestData(
            [
                scenery.manifest.SetUpInstruction("reset_db"),
                scenery.manifest.SetUpInstruction(
                    "create_some_instance",
                    {
                        "some_field": "some_value",
                    },
                ),
            ]
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

        self.django_testcase.test_1 = test_1
        self.django_testcase.test_2 = test_2

        self.assertTestPasses(self.django_testcase("test_1"))
        self.assertTestPasses(self.django_testcase("test_2"))
