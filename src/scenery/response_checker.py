"""Perform assertions on HTTP response from the test client."""
import os
import http
import typing
import importlib

import scenery.manifest

import django.test
import django.http
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

import bs4

# TODO mad: change type hints using ResponseProtocol
from scenery.common import ResponseProtocol

class SeleniumResponse(ResponseProtocol):

    def __init__(
        self, 
        driver,
        url
        ):

        self.driver = driver


    @property
    def status_code(self) -> int:
        # TODO mad, sel: should be returned in the html
        # NOTE mad: this is probably much harder to solve in general
        # Wwe can't use Selenium for the status code
        # one solution could be to use request
        return -1
    
    @property
    def headers(self) -> typing.Mapping[str, str]:
        return None
    
    @property
    def content(self) -> bytes:
        return self.driver.page_source
    
    @property
    def charset(self) -> str:
        return None
    
    def has_header(self, header_name: str) -> bool:
        return header_name in self._headers
    
    def __getitem__(self, header_name: str) -> str:
        return self._headers[header_name]
    
    def __setitem__(self, header_name: str, value: str) -> None:
        self._headers[header_name] = value




class Checker:
    """A utility class for performing HTTP requests and assertions on responses.

    This class provides static methods to execute HTTP requests and perform
    various checks on the responses, as specified in the test manifests.
    """

    # TODO: mad, the get_response methods should be somwhere else

    @staticmethod
    def get_http_client_response(
        django_testcase: django.test.TestCase, take: scenery.manifest.HttpTake
    ) -> django.http.HttpResponse:
        """Execute an HTTP request based on the given HttpTake object.

        Args:
            client: The Django test client to use for the request.
            take (scenery.manifest.HttpTake): The HttpTake object specifying the request details.

        Returns:
            django.http.HttpResponse: The response from the HTTP request.

        Raises:
            NotImplementedError: If the HTTP method specified in the take is not implemented.
        """
        if take.method == http.HTTPMethod.GET:
            response = django_testcase.client.get(
                take.url,
                take.data,
            )
        elif take.method == http.HTTPMethod.POST:
            response = django_testcase.client.post(
                take.url,
                take.data,
            )
        else:
            raise NotImplementedError(take.method)

        # NOTE: this one is a bit puzzling to me
        # runnning mypy I get:
        # Incompatible return value type (got "_MonkeyPatchedWSGIResponse", expected "HttpResponse")
        return response  # type: ignore[return-value]
    
    @staticmethod
    def get_selenium_response(
        django_testcase: StaticLiveServerTestCase, take: scenery.manifest.HttpTake
    ) -> django.http.HttpResponse:
        
        # Get the correct url form the StaticLiveServerTestCase
        url = django_testcase.live_server_url + take.url

        response = SeleniumResponse(django_testcase.driver, url)



        # TODO: should be a class attribute or something, maybe module could be loaded at the beggining
        selenium_module = importlib.import_module(os.environ["SCENERY_POST_REQUESTS_INSTRUCTIONS_SELENIUM"])

        django_testcase.driver.get(url)


        if take.method == http.HTTPMethod.GET:
            pass
        if take.method == http.HTTPMethod.POST:
            # TODO mad: improve and or document
            method_name = take.url_name.replace(":", "_")
            method_name =  f"post_{method_name}"
            post_method = getattr(selenium_module, method_name)
            post_method(django_testcase, take.data)


        return response 
      

    @staticmethod
    def exec_check(
        django_testcase: django.test.TestCase,
        response: django.http.HttpResponse,
        check: scenery.manifest.HttpCheck,
    ) -> None:
        """Execute a specific check on an HTTP response.

        This method delegates to the appropriate check method based on the instruction
        specified in the HttpCheck object.

        Args:
            django_testcase (django.test.TestCase): The Django test case instance.
            response (django.http.HttpResponse): The HTTP response to check.
            check (scenery.manifest.HttpCheck): The check to perform on the response.

        Raises:
            NotImplementedError: If the check instruction is not implemented.
        """
        if check.instruction == scenery.manifest.DirectiveCommand.STATUS_CODE:
            Checker.check_status_code(django_testcase, response, check.args)
        elif check.instruction == scenery.manifest.DirectiveCommand.REDIRECT_URL:
            Checker.check_redirect_url(django_testcase, response, check.args)
        elif check.instruction == scenery.manifest.DirectiveCommand.COUNT_INSTANCES:
            Checker.check_count_instances(django_testcase, response, check.args)
        elif check.instruction == scenery.manifest.DirectiveCommand.DOM_ELEMENT:
            Checker.check_dom(django_testcase, response, check.args)
        else:
            raise NotImplementedError(check)

    @staticmethod
    def check_status_code(
        django_testcase: django.test.TestCase,
        response: django.http.HttpResponse,
        args: int,
    ) -> None:
        """Check if the response status code matches the expected code.

        Args:
            django_testcase (django.test.TestCase): The Django test case instance.
            response (django.http.HttpResponse): The HTTP response to check.
            args (int): The expected status code.
        """
        # print("HERE", response.status_code)
        # print(response.content)
        print(django_testcase.__class__.__name__)
        django_testcase.assertEqual(
            response.status_code,
            args,
            f"Expected status code {args}, but got {response.status_code}",
        )

    @staticmethod
    def check_redirect_url(
        django_testcase: django.test.TestCase,
        response: django.http.HttpResponse,
        args: str,
    ) -> None:
        """Check if the response redirect URL matches the expected URL.

        Args:
            django_testcase (django.test.TestCase): The Django test case instance.
            response (django.http.HttpResponseRedirect): The HTTP redirect response to check.
            args (str): The expected redirect URL.
        """
        django_testcase.assertIsInstance(
            response,
            django.http.HttpResponseRedirect,
            f"Expected HttpResponseRedirect but got {type(response)}",
        )
        # NOTE mad: this is done for static type checking
        # TODO mad: I don't like it
        redirect = typing.cast(django.http.HttpResponseRedirect, response)
        django_testcase.assertEqual(
            redirect.url,
            args,
            f"Expected redirect URL '{args}', but got '{redirect.url}'",
        )

    @staticmethod
    def check_count_instances(
        django_testcase: django.test.TestCase,
        response: django.http.HttpResponse,
        args: dict,
    ) -> None:
        """Check if the count of model instances matches the expected count.

        Args:
            django_testcase (django.test.TestCase): The Django test case instance.
            response (django.http.HttpResponse): The HTTP response (not used in this check).
            args (dict): A dictionary containing 'model' (the model class) and 'n' (expected count).
        """
        instances = list(args["model"].objects.all())
        django_testcase.assertEqual(
            len(instances),
            args["n"],
            f"Expected {args['n']} instances of {args['model'].__name__}, but found {len(instances)}",
        )

    @staticmethod
    def check_dom(
        django_testcase: django.test.TestCase | StaticLiveServerTestCase,
        response: django.http.HttpResponse,
        args: dict[scenery.manifest.DomArgument, typing.Any],
    ) -> None:
        """Check for the presence and properties of DOM elements in the response content.

        This method uses BeautifulSoup to parse the response content and perform various
        checks on DOM elements as specified in the args dictionary.

        Args:
            django_testcase (django.test.TestCase): The Django test case instance.
            response (django.http.HttpResponse): The HTTP response to check.
            args (dict): A dictionary of DomArgument keys and their corresponding values,
                         specifying the checks to perform.

        Raises:
            ValueError: If neither 'find' nor 'find_all' arguments are provided in args.
        """


        soup = bs4.BeautifulSoup(response.content, "html.parser")

        # Apply the scope
        if scope := args.get(scenery.manifest.DomArgument.SCOPE):
            scope_result = soup.find(**scope)
            django_testcase.assertIsNotNone(
                scope,
                f"Expected to find an element matching {args[scenery.manifest.DomArgument.SCOPE]}, but found none",
            )
        else:
            scope_result = soup

        # NOTE: we inforce type checking by regarding bs4 objects as Tag
        scope_result = typing.cast(bs4.Tag, scope_result)

        # Locate the element(s)
        if args.get(scenery.manifest.DomArgument.FIND_ALL):
            dom_elements = scope_result.find_all(**args[scenery.manifest.DomArgument.FIND_ALL])
            django_testcase.assertGreaterEqual(
                len(dom_elements),
                1,
                f"Expected to find at least one element matching {args[scenery.manifest.DomArgument.FIND_ALL]}, but found none",
            )
        elif args.get(scenery.manifest.DomArgument.FIND):
            dom_element = scope_result.find(**args[scenery.manifest.DomArgument.FIND])
            django_testcase.assertIsNotNone(
                dom_element,
                f"Expected to find an element matching {args[scenery.manifest.DomArgument.FIND]}, but found none",
            )
            dom_elements = bs4.ResultSet(source=bs4.SoupStrainer(), result=[dom_element])
        else:
            raise ValueError("Neither find of find_all argument provided")

        # NOTE: I enforce the results to be a bs4.ResultSet[bs4.Tag] above
        dom_elements = typing.cast(bs4.ResultSet[bs4.Tag], dom_elements)

        # Perform the additional checks
        if count := args.get(scenery.manifest.DomArgument.COUNT):
            django_testcase.assertEqual(
                len(dom_elements),
                count,
                f"Expected to find {count} elements, but found {len(dom_elements)}",
            )
        for dom_element in dom_elements:
            # NOTE: we are sure it is not
            if text := args.get(scenery.manifest.DomArgument.TEXT):
                django_testcase.assertEqual(
                    dom_element.text,
                    text,
                    f"Expected element text to be '{text}', but got '{dom_element.text}'",
                )
            if attribute := args.get(scenery.manifest.DomArgument.ATTRIBUTE):
                # TODO: should this move to manifest parser? we will decide in v2
                if isinstance(attribute["value"], (str, list)):
                    pass
                elif isinstance(attribute["value"], int):
                    attribute["value"] = str(attribute["value"])
                else:
                    raise TypeError(
                        f"attribute value can only by `str` or `list[str]` not '{type(attribute['value'])}'"
                    )
                django_testcase.assertEqual(
                    dom_element[attribute["name"]],
                    attribute["value"],
                    f"Expected attribute '{attribute['name']}' to have value '{attribute['value']}', but got '{dom_element[attribute['name']]}'",
                )
