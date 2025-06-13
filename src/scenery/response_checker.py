"""Perform assertions on HTTP response from the test client."""
import os
import http
import importlib
import json
import time
from typing import Any, cast, Protocol, Mapping
import requests

from  scenery import logger
from scenery.common import (
    SceneryTestCase, 
    DjangoBackendTestCase, 
    DjangoFrontendTestCase,
    RemoteBackendTestCase,
    RemoteFrontendTestCase,
    )
from scenery.manifest import Take, Check, DirectiveCommand, DomArgument

import bs4
import django.http

from selenium import webdriver


# RESPONSE PROTOCOL
###################

class ResponseProtocol(Protocol):
    """A protocol for HTTP responses, covering both basic Django http response and from Selenium Driver."""

    @property
    def status_code(self) -> int:
        """The HTTP status code of the response."""

    @property
    def headers(self) -> Mapping[str, str]:
        """The headers of the response."""

    @property
    def content(self) -> Any:
        """The content of the response."""

    # @property
    # def json(self) -> str | None:
    #     """The json of the response."""
    #     raise NotImplementedError

    # @property
    # def charset(self) -> str | None:
    #     """The charset of the response."""

    # def has_header(self, header_name: str) -> bool:
    #     """Check if the response has a specific header."""

    # def __getitem__(self, header_name: str) -> str: ...

    # def __setitem__(self, header_name: str, value: str) -> None: ...



# NOTE mad: we do not declare any django.http.HttpResponse child 
# as this is the whole point of protocols to avoid painful inheritance

class SeleniumResponse(ResponseProtocol):
    """A response wrapper class for Selenium WebDriver operations.

    This class implements the ResponseProtocol interface for Selenium WebDriver,
    providing access to response data like headers, content, and charset. Note that
    some HTTP-specific features like status codes are not available through Selenium.

    Args:
        driver (webdriver.Chrome): The Selenium Chrome WebDriver instance to wrap.

    Attributes:
        driver (webdriver.Chrome): The wrapped Selenium WebDriver instance.
        _headers (dict[str, str]): Dictionary storing response headers.

    Properties:
        status_code (int): Not implemented for Selenium responses.
        headers (dict[str, str]): Dictionary of response headers.
        content (Any): Page source of the current webpage.
        charset (str): Character encoding of the response.

    Methods:
        has_header(header_name: str) -> bool: Check if a header exists in the response.
    """

    def __init__(
        self, 
        driver: webdriver.Chrome,
        ) -> None:
        self.driver = driver
        self._headers : dict[str, str] = {}

    @property
    def status_code(self) -> int:
        """Not implemented for Selenium responses."""
        # NOTE mad: this is probably hard to solve in general
        # we can't use Selenium for the status code
        raise NotImplementedError
    
    @property
    def headers(self) -> dict[str, str]:
        """Dictionary of response headers."""
        return self._headers
    
    @property
    def content(self) -> Any:
        """Page source of the current webpage."""
        return self.driver.page_source
    
    @property
    def charset(self) -> str | None:
        """Character encoding of the response."""
        # return None
        return None
    
    def has_header(self, header_name: str) -> bool:
        """Check if a header exists in the response."""
        return header_name in self._headers
    
    def __getitem__(self, header_name: str) -> str:
        return self._headers[header_name]
    
    def __setitem__(self, header_name: str, value: str) -> None:
        self._headers[header_name] = value


# RESPONSE CHECKER
##################

class Checker:
    """A utility class for performing HTTP requests and assertions on responses.

    This class provides static methods to execute HTTP requests and perform
    various checks on the responses, as specified in the test manifests.
    """

    # NOTE mad: the first functions take a Take 
    # as argument to retrieve the server respone
    # The next function takes the response protocols
    # and potentially other arguments to perform checks



    # COLLECT RESPONSE
    ##################

    selenium_module = importlib.import_module(os.environ["SCENERY_POST_REQUESTS_INSTRUCTIONS_SELENIUM"])


    @staticmethod
    def get_django_client_response(
        testcase: DjangoBackendTestCase, take: Take
    ) -> django.http.HttpResponse:
        """Execute an HTTP request based on the given HttpTake object.

        Args:
            testcase (BackendDjangoTestCase): The Django testcase instance.
            take (scenery.manifest.HttpTake): The HttpTake object specifying the request details.

        Returns:
            django.http.HttpResponse: The response from the HTTP request.

        Raises:
            NotImplementedError: If the HTTP method specified in the take is not implemented.
        """
        logger.debug(Checker.get_django_client_response)
        logger.debug(f"{take.url=}")
        logger.debug(f"{take.method=}")
        if take.data:
            logger.debug(take.data)

        if take.method == http.HTTPMethod.GET:
            response = testcase.client.get(
                take.url,
                take.data,
            )
        elif take.method == http.HTTPMethod.POST:
            response = testcase.client.post(
                take.url,
                take.data,
            )
        else:
            raise NotImplementedError(take.method)

        # FIXME mad: this one is a bit puzzling to me
        # running mypy I get:
        # Incompatible return value type (got "_MonkeyPatchedWSGIResponse", expected "HttpResponse")
        return response # type: ignore[return-value]
    
    @classmethod
    def get_selenium_response(
        cls, testcase: DjangoFrontendTestCase | RemoteFrontendTestCase, take: Take
    ) -> SeleniumResponse:
        """Create a SeleniumResponse by executing a request through Selenium WebDriver.

        This function handles both GET and POST requests through Selenium. For POST requests,
        it dynamically loads and executes request handlers from a configured Selenium module.

        Args:
            testcase (FrontendDjangoTestCase): The test case instance containing
                the Selenium WebDriver and live server URL.
            take (Take): The request specification containing method, URL, and data
                for the request to be executed.

        Returns:
            SeleniumResponse: A wrapper containing the response from the Selenium-driven request.

        Raises:
            ImportError: If the SCENERY_POST_REQUESTS_INSTRUCTIONS_SELENIUM module cannot be loaded.
            AttributeError: If a POST request handler method cannot be found in the Selenium module.

        Notes:
            - For POST requests, the handler method name is derived from the URL name by
            replacing ':' with '_' and prefixing with 'post_'.
            - The Selenium module path must be specified in the SCENERY_POST_REQUESTS_INSTRUCTIONS_SELENIUM
            environment variable.
        """
        # url = testcase.live_server_url + take.url
        url = testcase.base_url + take.url

        logger.debug(Checker.get_selenium_response)
        logger.debug(f"{url=}")
        logger.debug(f"{take.method=}")
        if take.data:
            logger.debug(take.data)


        response = SeleniumResponse(testcase.driver)


        if take.method == http.HTTPMethod.GET:
            testcase.driver.get(url)
        if take.method == http.HTTPMethod.POST:
            # TODO mad: improve and or document
            method_name = take.url_name.replace(":", "_")
            method_name =  f"post_{method_name}"
            post_method = getattr(cls.selenium_module, method_name)
            post_method(testcase, url, take.data)

        # time.sleep(1000)


        return response 
    
    @staticmethod
    def get_http_response(testcase: RemoteBackendTestCase, take: Take) -> requests.Response:

        url = testcase.base_url + take.url

        logger.debug(Checker.get_http_response)
        logger.debug(f"{url=}")
        logger.debug(f"{take.method=}")
        if take.data:
            logger.debug(take.data)

        if take.method == http.HTTPMethod.GET:
            response = testcase.session.get(
                url,
                data=take.data,
                headers=testcase.headers,
            )
        elif take.method == http.HTTPMethod.POST:
            response = testcase.session.post(
                testcase.base_url + take.url,
                take.data,
                headers=testcase.headers,
            )
        else:
            raise NotImplementedError(take.method)

        return response

    # CHECKS
    ################################

    @staticmethod
    def exec_check(
        testcase: SceneryTestCase,
        response: ResponseProtocol,
        check: Check,
    ) -> None:
        """Execute a specific check on an HTTP response.

        This method delegates to the appropriate check method based on the instruction
        specified in the HttpCheck object.

        Args:
            testcase (DjangoTestCase): The Django test case instance.
            response (ResponseProtocol): The response to check.
            check (scenery.manifest.HttpCheck): The check to perform on the response.

        Raises:
            NotImplementedError: If the check instruction is not implemented.
        """

        logger.debug(check)

        if check.instruction == DirectiveCommand.STATUS_CODE:
            Checker.check_status_code(testcase, response, check.args)
        elif check.instruction == DirectiveCommand.REDIRECT_URL:
            Checker.check_redirect_url(testcase, response, check.args)
        elif check.instruction == DirectiveCommand.COUNT_INSTANCES:
            Checker.check_count_instances(testcase, response, check.args)
        elif check.instruction == DirectiveCommand.DOM_ELEMENT:
            Checker.check_dom(testcase, response, check.args)
        elif check.instruction == DirectiveCommand.JSON:
            Checker.check_json(testcase, response, check.args)
        elif check.instruction == DirectiveCommand.FIELD_OF_INSTANCE:
            Checker.check_field_of_instance(testcase, response, check.args)
        # NOTE mad: do not erase
        # elif check.instruction == scenery.manifest.DirectiveCommand.JS_VARIABLE:
        #     Checker.check_js_variable(testcase, response, check.args)
        # elif check.instruction == scenery.manifest.DirectiveCommand.JS_STRINGIFY:
        #     Checker.check_js_stringify(testcase, response, check.args)
        else:
            raise NotImplementedError(check)
        

    @staticmethod
    def check_status_code(
        testcase: SceneryTestCase,
        response: ResponseProtocol,
        args: int,
    ) -> None:
        """Check if the response status code matches the expected code.

        Args:
            testcase (DjangoTestCase): The Django test case instance.
            response (ResponseProtocol): The HTTP response to check.
            args (int): The expected status code.
        """
        testcase.assertEqual(
            response.status_code,
            args,
            f"Expected status code {args}, but got {response.status_code}",
        )

    @staticmethod
    def check_redirect_url(
        testcase: SceneryTestCase,
        response: ResponseProtocol,
        args: str,
    ) -> None:
        """Check if the response redirect URL matches the expected URL.

        Args:
            testcase (DjangoTestCase): The Django test case instance.
            response (django.http.HttpResponseRedirect): The HTTP redirect response to check.
            args (str): The expected redirect URL.
        """
        # NOTE mad: this will fail when we try with frontend for login etc... 
        # but I skip those kind of test in the method builder
        testcase.assertIsInstance(
            response,
            django.http.HttpResponseRedirect,
            f"Expected HttpResponseRedirect but got {type(response)}",
        )
        # FIXME mad: this is done for static type checking
        redirect = cast(django.http.HttpResponseRedirect, response)
        testcase.assertEqual(
            redirect.url,
            args,
            f"Expected redirect URL '{args}', but got '{redirect.url}'",
        )

    @staticmethod
    def check_count_instances(
        testcase: SceneryTestCase,
        response: ResponseProtocol,
        args: dict,
    ) -> None:
        """Check if the count of model instances matches the expected count.

        Args:
            testcase (DjangoTestCase): The Django test case instance.
            response (ResponseProtocol): The HTTP response (not used in this check).
            args (dict): A dictionary containing 'model' (the model class) and 'n' (expected count).
        """
        instances = list(args["model"].objects.all())
        testcase.assertEqual(
            len(instances),
            args["n"],
            f"Expected {args['n']} instances of {args['model'].__name__}, but found {len(instances)}",
        )

    @staticmethod
    def check_dom(
        testcase: SceneryTestCase,
        response: ResponseProtocol,
        args: dict[DomArgument, Any],
    ) -> None:
        """Check for the presence and properties of DOM elements in the response content.

        This method uses BeautifulSoup to parse the response content and perform various
        checks on DOM elements as specified in the args dictionary.

        Args:
            testcase (DjangoTestCase): The Django test case instance.
            response (django.ResponseProtocol): The HTTP response to check.
            args (dict): A dictionary of DomArgument keys and their corresponding values,
                         specifying the checks to perform.

        Raises:
            ValueError: If neither 'find' nor 'find_all' arguments are provided in args.
        """
        # NOTE mad: this is incredibly important for the frontend test
        time.sleep(1)

        soup = bs4.BeautifulSoup(response.content, "html.parser")

        # Apply the scope
        if scope := args.get(DomArgument.SCOPE):
            scope_result = soup.find(**scope)
            testcase.assertIsNotNone(
                scope,
                f"Expected to find an element matching {args[DomArgument.SCOPE]}, but found none",
            )
        else:
            scope_result = soup

        # FIXME mad: we inforce type checking by regarding bs4 objects as Tag
        scope_result = cast(bs4.Tag, scope_result)

        # Locate the element(s)
        if args.get(DomArgument.FIND_ALL):
            dom_elements = scope_result.find_all(**args[DomArgument.FIND_ALL])
            testcase.assertGreaterEqual(
                len(dom_elements),
                1,
                f"Expected to find at least one element matching {args[DomArgument.FIND_ALL]}, but found none",
            )
        elif args.get(DomArgument.FIND):
            dom_element = scope_result.find(**args[DomArgument.FIND])
            testcase.assertIsNotNone(
                dom_element,
                f"Expected to find an element matching {args[DomArgument.FIND]}, but found none",
            )
            dom_elements = bs4.ResultSet(source=bs4.SoupStrainer(), result=[dom_element])
        else:
            raise ValueError("Neither find of find_all argument provided")
        # FIXME mad: as I enforce the results to be a bs4.ResultSet[bs4.Tag] above
        dom_elements = cast(bs4.ResultSet[bs4.Tag], dom_elements)

        # Perform the additional checks
        if count := args.get(DomArgument.COUNT):
            testcase.assertEqual(
                len(dom_elements),
                count,
                f"Expected to find {count} elements, but found {len(dom_elements)}",
            )
        for dom_element in dom_elements:
            if text := args.get(DomArgument.TEXT):
                testcase.assertEqual(
                    dom_element.text,
                    text,
                    f"Expected element text to be '{text}', but got '{dom_element.text}'",
                )
            if attribute := args.get(DomArgument.ATTRIBUTE):

                if value := attribute.get("value"):
                    # TODO mad: should this move to manifest parser?
                    # in manifest _format_dom_element should be used here, or even before and just disappear
                    if isinstance(value, (str, list)):
                        pass
                    elif isinstance(value, int):
                        value = str(value)
                    else:
                        raise TypeError(
                            f"attribute value can only by `str` or `list[str]` not '{type(value)}'"
                        )
                    testcase.assertEqual(
                        dom_element[attribute["name"]],
                        value,
                        f"Expected attribute '{attribute['name']}' to have value '{value}', but got '{dom_element[attribute['name']]}'",
                    )
                elif regex := attribute.get("regex"):

                    testcase.assertRegex(
                        dom_element[attribute["name"]],
                        regex,
                        f"Expected attribute '{attribute['name']}' to match regex '{regex}', but got '{dom_element[attribute['name']]}'",
                    )
                if exepected_value_from_ff := attribute.get("json_stringify"):

                    if isinstance(testcase, DjangoFrontendTestCase):
                        # NOTE mad: we cannot anotate it.
                        value_from_ff = testcase.driver.execute_script( # type: ignore[no-untyped-call]
                        f"return JSON.stringify({dom_element[attribute['name']]})"
                    )
                    else:
                        raise Exception("json_stringify can only be called for frontend tests")

                    if exepected_value_from_ff == "_":
                        # NOTE mad: this means we only want to check the value is a valid json string
                        pass
                    else:
                        value_from_ff = json.loads(value_from_ff)
                        testcase.assertEqual(
                            value_from_ff,
                            exepected_value_from_ff,
                            f"Expected attribute '{attribute['name']}' to have value '{exepected_value_from_ff}', but got '{value_from_ff}'",
                        )
                
    @staticmethod
    def check_json(
        testcase: SceneryTestCase,
        response: ResponseProtocol,
        args: dict,
    ) -> None:
        # print(f"{response.json()=}")
        testcase.assertIsInstance(response, django.http.JsonResponse)
        # FIXME
        data = response.json() # type: ignore [attr-defined]
        testcase.assertEqual(data[args["key"]], args["value"])


    @staticmethod
    def check_field_of_instance(
        testcase: SceneryTestCase,
        response: ResponseProtocol,
        args: dict,
    ) -> None:
        

        instances = list(args["find"]["model"].objects.all())
        if len(instances) != 1:
            testcase.fail(f"Checking the {args['field']} field of {args['find']['model']} requires that there is a single instance in the db, but found {len(instances)}.")
        
        instance = instances[0]
        field_value = getattr(instance, args["field"])
        testcase.assertEqual(
            field_value, 
            args["value"],
            f"{args['find']['model'].__name__}.{args['field']} = {field_value} but expected {args['value']}"
        )

        # testcase.assertEqual(
        #     len(instances),
        #     args["n"],
        #     f"Expected {args['n']} instances of {args['model'].__name__}, but found {len(instances)}",
        # )

# NOTE mad: do not erase
    # def check_js_variable(self, testcase: DjangoFrontendTestCase, args: dict) -> None:
    #     """
    #     Check if a JavaScript variable has the expected value.
    #     Args:
    #         testcase (DjangoTestCase): The Django test case instance.
    #         args (dict): The arguments for the check.
    #     """

    #     variable_name = args["name"]
    #     expected_value = args["value"]
    #     actual_value = testcase.driver.execute_script(
    #         f"return {variable_name};"
    #     )
    #     testcase.assertEqual(
    #         actual_value,
    #         expected_value,
    #         f"Expected JavaScript variable '{variable_name}' to have value '{expected_value}', but got '{actual_value}'",
    #     )