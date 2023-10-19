import os
import requests
import json
from lxml import html
from datetime import datetime, timedelta
from typing import Dict
from copy import deepcopy
from common import Projects
from calendar import THURSDAY

CONFLUENCE_TOKEN = os.environ["CONFLUENCE_TOKEN"]

projects_confluence_names = {
    Projects.MAYA_RPR: "RPR Maya",
    Projects.MAYA_USD: "Maya USD",
    Projects.BLENDER_RPR: "RPR Blender",
    Projects.BLENDER_USD: "Blender USD",
    Projects.RENDER_STUDIO: "Render Studio",
    Projects.SOLIDWORKS: "Solidworks",
    Projects.HOUDINI: "Houdini",
    Projects.HDRPR: "hdRPR",
    Projects.INVENTOR: "Inventor"
}


def _request_projects_statuses_page(report_date: datetime) -> html.Element:
    url = "https://luxproject.luxoft.com/confluence/rest/api/content"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {CONFLUENCE_TOKEN}",
    }

    response = requests.get(
        f"{url}/?title=Thursday weekly {report_date.strftime('%d/%m/%Y')}&expand=body.storage",
        headers=headers,
    )

    page_content = json.loads(response.text)["results"][0]["body"]["storage"]["value"]
    return html.fromstring(page_content)


def _get_projects_info(report_date: datetime):
    tree = _request_projects_statuses_page(report_date)

    projects_info: Dict = {}

    for project in projects_confluence_names:
        project_name = projects_confluence_names[project]
        projects_info[project] = []

        # find project block
        project_name_el = tree.xpath(
            f"//*[contains(text(),'{project_name}') and count(ancestor::*)<4]"
        )[0]
        if project_name_el.tag != "p":
            project_name_el = project_name_el.xpath("ancestor::p[1]")[0]

        # find project tasks list
        task_list_el = project_name_el.xpath("./following-sibling::*")[0]

        # enumerate all project tasks
        for task_el in task_list_el.xpath("./task"):
            # get task info
            task_body: str = task_el.xpath("./task-body")[0].text_content()
            task_status = task_el.xpath("./task-status")[0].text_content()

            # remove unicode character (completance mark)
            task_body = task_body.replace("\u00a0", "")

            # identify task priority
            # and remove "HP: ", "MP: ", or "LP: " from the start of the string
            priority = ""
            if task_body.startswith("HP:"):
                priority = "high"
                task_body = task_body[3:].strip()
            elif task_body.startswith("MP:"):
                priority = "medium"
                task_body = task_body[3:].strip()
            elif task_body.startswith("LP:"):
                priority = "low"
                task_body = task_body[3:].strip()
            elif task_body.startswith("NFR:"):  # not for report
                continue

            # remove comment from the end of the string
            task_body = task_body.split(" - ")[0]

            projects_info[project].append(
                {"description": task_body, "status": task_status, "priority": priority}
            )

    return projects_info


def get_main_tasks(projects_info) -> set:
    main_tasks = set()

    for project in projects_info:
        for task in projects_info.get(project):
            if task.get("status") == "complete" and task.get("priority") == "high":
                main_tasks.add(task.get("description"))

    return main_tasks


def get_tasks(report_date: datetime):
    offset = (report_date.weekday() - THURSDAY) % 7
    last_thursday = report_date - timedelta(days=offset)

    previous_thursday = last_thursday - timedelta(weeks=1)

    # get info about projects on this week and previous
    old_projects_info = _get_projects_info(report_date=previous_thursday)
    new_projects_info = _get_projects_info(report_date=last_thursday)

    # combine info
    # filter previous week tasks (only completed)

    all_projects_info = deepcopy(new_projects_info)

    for project in old_projects_info:
        all_project_info = all_projects_info[project]
        new_tasks = set([task["description"] for task in all_project_info])

        for task in old_projects_info[project]:
            if task["status"] == "complete" and task["description"] not in new_tasks:
                all_project_info.append(task)

    return all_projects_info


if __name__ == "__main__":
    # Tasks
    print("Tasks:")
    tasks = get_tasks(datetime.today())
    for project in projects_confluence_names:
        print(projects_confluence_names[project] + ":")
        print(json.dumps(tasks[project], indent=4))

    print("\n\n\n\n")
    # Main Tasks
    print("Main tasks")
    main_tasks = list(get_main_tasks(tasks))
    for project in projects_confluence_names:
        print(projects_confluence_names[project] + ":")
        print(json.dumps(main_tasks, indent=4))
