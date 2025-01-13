
from selenium.webdriver.common.by import By

# from django.contrib.staticfiles.testing import StaticLiveServerTestCase



# def find_element(driver, **kwargs):
#     for by, value in kwargs.items():
#         if by == "id":
#             selector = By.ID
#         else:
#             raise ValueError(f"{by=}")
#         return driver.find_element(selector, value)


def post_frontend(django_testcase, data):

    print("I AM POSTING STUFF")

    input_field = django_testcase.driver.find_element(By.ID, "testInput")
    input_field.send_keys(data["message"])
    post_button = django_testcase.driver.find_element(By.ID, "testButton")
    post_button.click()
    