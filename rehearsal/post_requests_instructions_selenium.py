from scenery.common import DjangoFrontendTestCase
from selenium.webdriver.common.by import By

def post_frontend(django_testcase: DjangoFrontendTestCase, url: str, data: dict) -> None:
    django_testcase.driver.get(url)
    input_field = django_testcase.driver.find_element(By.ID, "testInput")
    input_field.send_keys(data["message"])
    post_button = django_testcase.driver.find_element(By.ID, "testButton")
    post_button.click()
    


    