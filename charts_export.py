import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from time import sleep
from PIL import Image
from common import Projects, ChartType

JIRA_AMD_HOST = os.getenv("JIRA_AMD_HOST", "amdrender.atlassian.net")
JIRA_AMD_USERNAME = os.environ["JIRA_AMD_USERNAME"]
JIRA_AMD_PASSWORD = os.environ["JIRA_AMD_PASSWORD"]

projects_chart_names = {
    Projects.MAYA_RPR: {
        ChartType.UNRESOLVED_ISSUES: "Maya RPR: Unresolved issues",
        ChartType.ISSUES_UPDATES_2W: "Maya RPR: Issues updates in 2 weeks",
    },
    Projects.MAYA_USD: {
        ChartType.UNRESOLVED_ISSUES: "Maya USD: Unresolved issues",
        ChartType.ISSUES_UPDATES_2W: "Maya USD: Issues updates in 2 weeks",
    },
    Projects.BLENDER_RPR: {
        ChartType.UNRESOLVED_ISSUES: "Blender RPR: Unresolved issues",
        ChartType.ISSUES_UPDATES_2W: "Blender RPR: Issues updates in 2 weeks",
    },
    Projects.BLENDER_USD: {
        ChartType.UNRESOLVED_ISSUES: "Blender USD: Unresolved issues",
        ChartType.ISSUES_UPDATES_2W: "Blender USD: Issues updates in 2 weeks",
    },
    # Projects.SOLIDWORKS: {
    #     ChartType.UNRESOLVED_ISSUES: "Solidworks: Unresolved issues",
    #     ChartType.ISSUES_UPDATES_2W: "Solidworks: Issues updates in 2 weeks",
    # },
    Projects.HOUDINI: {
        ChartType.UNRESOLVED_ISSUES: "Houdini: Unresolved issues",
        ChartType.ISSUES_UPDATES_2W: "Houdini: Issues updates in 2 weeks",
    },
    Projects.HDRPR: {
        ChartType.UNRESOLVED_ISSUES: "hdRPR: Unresolved issues",
        ChartType.ISSUES_UPDATES_2W: "hdRPR: Issues updates in 2 weeks",
    },
    Projects.RENDER_STUDIO: {
        ChartType.UNRESOLVED_ISSUES: "Render Studio: Unresolved issues",
        ChartType.ISSUES_UPDATES_2W: "Render Studio: Issues updates in 2 weeks",
    },
    Projects.INVENTOR: {
        ChartType.UNRESOLVED_ISSUES: "Inventor: Unresolved issues",
        ChartType.ISSUES_UPDATES_2W: "Inventor: Issues updates in 2 weeks",
    },
}


def login(driver: webdriver.Firefox):
    driver.get("https://id.atlassian.com/login")
    driver.find_element(By.ID, "username").send_keys(JIRA_AMD_USERNAME)
    sleep(1)  # to avaid bot protection
    driver.find_element(By.ID, "login-submit").click()

    while not driver.find_elements(By.ID, "password"):
        sleep(1)

    sleep(4)

    driver.find_element(By.ID, "password").send_keys(JIRA_AMD_PASSWORD)
    sleep(4)  # to avaid bot protection
    driver.find_element(By.ID, "login-submit").click()

    # waiting for main page to load
    while not driver.find_elements(By.TAG_NAME, "button"):
        sleep(1)

    sleep(2)


def _save_chart_screenshot(driver, project: Projects, chart_type: ChartType):
    chart_name = projects_chart_names[project][chart_type]

    # check wheter chart is available
    chart_not_available = driver.find_elements(
        By.XPATH,
        "//div[text()='{chart_name}']//ancestor::div[6]//descendant::div[contains(text(), 'No Data Available')]".format(
            chart_name=chart_name
        ),
    )

    if chart_not_available:
        return None

    # find chart
    chart_el = None
    try:
        chart_el = driver.find_element(
            By.XPATH,
            "//div[text()='{chart_name}']//ancestor::div[6]//descendant::div[@class='piechart-with-legend']".format(
                chart_name=chart_name
            ),
        )
    except Exception:
        sleep(5)
        chart_el = driver.find_element(
            By.XPATH,
            "//div[text()='{chart_name}']//ancestor::div[6]//descendant::div[@class='piechart-with-legend']".format(
                chart_name=chart_name
            ),
        )

    # screen chart box
    sleep(1)
    img_name = "pics/chart_{project}_{type}.png".format(
        project=project.value, type=chart_type.value
    )
    chart_el.screenshot(img_name)

    # crop screenshot
    img = Image.open(img_name)
    box = (150, 0, img.width - 160, img.height)
    img.crop(box).save(img_name)

    return img_name


def export_charts():
    driver = webdriver.Firefox(executable_path="./geckodriver.exe")
    # driver.fullscreen_window()
    driver.set_window_size(1920,1080)

    login(driver)

    result_report = {
        project: {ChartType.UNRESOLVED_ISSUES: None, ChartType.ISSUES_UPDATES_2W: None}
        for project in projects_chart_names
    }

    ################# open issues updates board

    driver.get(f"https://{JIRA_AMD_HOST}/jira/dashboards/10322")

    # wait for charts to render
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//h1[contains(text(),'QA report')]"))
    )

    chart_type = ChartType.ISSUES_UPDATES_2W

    for project in projects_chart_names:
        img_path = _save_chart_screenshot(driver, project, chart_type)
        if img_path is None:
            continue
        result_report[project][chart_type] = img_path

    ################## open unresolved issues board

    driver.get(f"https://{JIRA_AMD_HOST}/jira/dashboards/10324")

    # wait for charts to render
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//h1[contains(text(),'QA Report')]"))
    )

    chart_type = ChartType.UNRESOLVED_ISSUES

    for project in projects_chart_names:
        img_path = _save_chart_screenshot(driver, project, chart_type)
        if img_path is None:
            continue
        result_report[project][chart_type] = img_path

    driver.close()

    return result_report


if __name__ == "__main__":
    export_charts()
