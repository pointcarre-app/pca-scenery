
from selenium.webdriver.common.by import By

def post_frontend(django_testcase, url, data):
    django_testcase.driver.get(url)
    input_field = django_testcase.driver.find_element(By.ID, "testInput")
    input_field.send_keys(data["message"])
    post_button = django_testcase.driver.find_element(By.ID, "testButton")
    post_button.click()
    


    