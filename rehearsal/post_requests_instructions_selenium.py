from scenery.common import DjangoFrontendTestCase
from selenium.webdriver.common.by import By

def post_frontend(testcase: DjangoFrontendTestCase, url: str, data: dict) -> None:
    testcase.driver.get(url)
    input_field = testcase.driver.find_element(By.ID, "testInput")
    input_field.send_keys(data["message"])
    post_button = testcase.driver.find_element(By.ID, "testButton")
    post_button.click()
    


    