import os
from lxml import etree
from typing import List, Dict, Tuple
import shutil
from datetime import datetime, timedelta
from PIL import Image

import ids
from common import (
    Link,
    Projects,
    ChartType,
    TaskType,
    TEMPLATE_PATH,
    WORKING_DIR_PATH,
    PICTURES_PATH,
)
from tasks_export import get_tasks, get_main_tasks
from bugs_list_export import get_blockers, get_bugs
from pr_status_export import get_pull_requests_status
from jenkins_export import get_latest_build_data
from charts_export import export_charts
import word

REPORT_FILE_PATH = "./report.docx"


def append_bullet_list_element_after(
    element: etree.Element, content: str
) -> etree.Element:
    bullet = word.create_bullet(list_id=25, lvl=0, content=content)

    # append this bullet element after specified
    word.append_element_after(new_el=bullet, after=element)

    # return new bullet element
    return bullet


def add_blocker_bullet_list_element(
    element: etree.Element, link: Link, description: str
) -> etree.Element:
    content = ("[", link, "]", word.create_whitespace(), description)
    bullet = word.create_bullet(list_id=9, lvl=1, content=content)

    # append this bullet element after provided
    word.append_element_after(new_el=bullet, after=element)

    # return new bullet
    return bullet


def add_main_tasks_bullet_list_element(
    element: etree.Element, content: str
) -> etree.Element:
    # create bullet element

    bullet = word.create_bullet(list_id=9, lvl=1, content=content)

    # append this bullet element after provided
    word.append_element_after(new_el=bullet, after=element)

    # return new bullet
    return bullet


def fill_pr_table(tree: etree.Element, project: Projects, data: List):
    # find table by id
    table = word.find_by_id(tree, ids.PR_STATUS_TABLE_ID[project])

    # add rows to the table accordingly to data rows amount
    data_rows = len(data)
    if data_rows > 1:
        word.table_add_rows(table, data_rows - 1)

    # copy data to the table
    table_rows = table.findall("./{*}tr")[1:]  # find all rows (skip header row)
    for row_num, row_data in enumerate(data):
        cells = table_rows[row_num].findall("./{*}tc")

        word.set_table_cell_value(cells[0], row_data["link"])
        word.set_table_cell_value(cells[2], row_data["status"])


def fill_task_list(tree: etree.Element, task_list_id: str, tasks: List):
    task_list_header = word.find_by_id(tree, task_list_id)

    # fill completed tasks list
    if tasks:  # fill list with tasks
        element = task_list_header
        for task in tasks:
            element = append_bullet_list_element_after(element, task["description"])
    else:  # remove empty list header
        word.remove_element(task_list_header)


def fill_task_lists(tree: etree.Element, task_lists: Dict[TaskType, str], tasks: List):
    # sort tasks
    completed_tasks = list(filter(lambda task: task["status"] == "complete", tasks))
    planned_tasks = list(filter(lambda task: task["status"] == "incomplete", tasks))

    # find lists headers
    fill_task_list(tree, task_lists[TaskType.COMPLETED], completed_tasks)
    fill_task_list(tree, task_lists[TaskType.PLANNED], planned_tasks)


def fill_build_status_table(tree: etree.Element, project: Projects, build_data: Dict):
    row_id = ids.BUILD_STATUS_TABLE_ROW[project]
    row = word.find_by_id(tree, row_id)

    cells = row.findall("./{*}tc")

    # 1 cell - Date ###########################

    if not build_data:
        word.set_table_cell_value(cells[1], "-")
    else:
        first_build = list(build_data.keys())[0]
        word.set_table_cell_value(cells[1], build_data[first_build]["date"])

    # 2 cell - Report Link ####################

    if not build_data:
        word.set_table_cell_value(cells[2], "-")
    else:
        links = [
            Link(build_data[build]["link"], build_data[build]["version"])
            for build in build_data
        ]
        # add spaces between links
        content: Tuple = tuple()
        for i, link in enumerate(links):
            content += tuple((link,))
            if (i + 1) < len(links):
                content += tuple((word.create_whitespace(),))

        word.set_table_cell_value(cells[2], content)

    # 3 cell - Status #########################
    # skip for now

    # 4 cell - Comment ########################
    # skip for now


def remove_chart(tree, project, chart_type):
    # if removed left chart,
    if chart_type == ChartType.UNRESOLVED_ISSUES:
        # then right header should be moved to the left

        # remove junk between headers
        header_el_r = word.find_by_id(
            tree, ids.CHART_HEADER_ID[project][ChartType.ISSUES_UPDATES_2W]
        )
        header_el_l = word.find_by_id(
            tree, ids.CHART_HEADER_ID[project][ChartType.UNRESOLVED_ISSUES]
        )

        parent = header_el_l.getparent()
        left_header_index = parent.index(header_el_l)
        right_header_index = parent.index(header_el_r)

        for i in range(right_header_index - 1, left_header_index, -1):
            parent.remove(parent[i])

        # and then right chart should be moved to the left
        image_el_l = word.find_by_id(
            tree, ids.CHART_ID[project][ChartType.UNRESOLVED_ISSUES]
        )
        image_el_r = word.find_by_id(
            tree, ids.CHART_ID[project][ChartType.ISSUES_UPDATES_2W]
        )
        image_el_r.find(".//{*}positionH").find("./{*}posOffset").text = str(
            int(image_el_l.find(".//{*}positionH").find("./{*}posOffset").text)
            + 350000  # magic number
        )
    elif not tree.findall(
        "//*[@id='{id}']".format(id=ids.CHART_ID[project][ChartType.UNRESOLVED_ISSUES])
    ):  # if there no one chart remains
        # then we need to remove all line breaks before 'view issues'
        headers_paragraph = word.find_by_id(
            tree, ids.CHART_HEADER_ID[project][chart_type]
        ).getparent()
        p = headers_paragraph.getnext()
        while not list(p):  # if it is empty paragraph (line breaks)
            word.remove_element(p)
            p = headers_paragraph.getnext()

    image_el = word.find_by_id(tree, ids.CHART_ID[project][chart_type])
    header_el = word.find_by_id(tree, ids.CHART_HEADER_ID[project][chart_type])

    # add note about chart absence
    note_text = ""
    if chart_type == ChartType.ISSUES_UPDATES_2W:
        note_text = "No issue updates in 2 weeks"
    else:
        note_text = "No unresolved issues"

    paragraph = word.create_paragraph()

    word.append_content(paragraph, note_text)

    header_paragraph = header_el.getparent()
    word.append_element_before(new_el=paragraph, before=header_paragraph)

    # remove elements
    word.remove_element(header_el)
    word.remove_element(image_el)


def replace_image(image_el, new_chart_path):
    # identify chart placeholder file location
    chart_placeholder_path = word.get_image_file_location(image_el)

    # replace file in archive
    os.replace(new_chart_path, chart_placeholder_path)

    # adjust new image size
    img = Image.open(chart_placeholder_path)
    word.adjust_image_size(image_el, img.height, img.width)


def update_chart(tree, project, chart_type, new_chart_path):
    # get chart element
    image_el = word.find_by_id(tree, ids.CHART_ID[project][chart_type])
    # replace chart image
    replace_image(image_el, new_chart_path)


def template_validation(tree) -> bool:
    # validate presence of all ids in template
    for id in ids.IDS:
        if word.find_by_id(tree, id) is None:
            return False

    return True


def prepare_working_directory():
    # remove tmp dir if exists
    if os.path.exists(WORKING_DIR_PATH):
        shutil.rmtree(WORKING_DIR_PATH)

    # remove pics dir if exists
    if os.path.exists(PICTURES_PATH):
        shutil.rmtree(PICTURES_PATH)

    # remove report if exists
    if os.path.exists(REPORT_FILE_PATH):
        os.remove(REPORT_FILE_PATH)

    # copy template to the working directory
    shutil.copytree(TEMPLATE_PATH, WORKING_DIR_PATH)

    # create pics directory
    os.mkdir(PICTURES_PATH)


def clean_working_dir():
    # remove tmp directories
    shutil.rmtree(WORKING_DIR_PATH)
    shutil.rmtree(PICTURES_PATH)


def finalize_report():
    # archive directory
    shutil.make_archive(
        "report",
        "zip",
        WORKING_DIR_PATH,
    )
    # and change it extension to ".docx"
    os.rename("report.zip", REPORT_FILE_PATH)


def main():
    prepare_working_directory()

    # eval report dates
    report_date = datetime.today()
    report_start_date = report_date - timedelta(weeks=2) + timedelta(days=1)

    # load document.xml (main xml file)
    tree = word.load_xml(word.DOCUMENT_PATH)

    # validate template
    if not template_validation(tree):
        print("Template is invalid! Some IDs are missing!")
        exit()

    # statistic for page allignment
    project_added_elements = {project: 0 for project in Projects}

    ###############################################################
    # update projects status table

    for project in Projects:
        build_data = get_latest_build_data(project)
        fill_build_status_table(tree, project, build_data)

    ###############################################################
    # update PRs status tables

    for project in ids.PR_STATUS_TABLE_ID:
        data = get_pull_requests_status(project)
        fill_pr_table(tree, project, data)

        project_added_elements[project] += len(data)

    ###############################################################
    # import tasks

    projects_tasks = get_tasks(report_date)

    for project in ids.TASK_LISTS_ID:
        tasks = projects_tasks[project]
        task_lists = ids.TASK_LISTS_ID[project]

        fill_task_lists(tree, task_lists, tasks)

        project_added_elements[project] += len(tasks)

    ###############################################################
    # fill main tasks table

    main_tasks = get_main_tasks(projects_tasks)

    # fill summary task list with important tasks
    elem = word.find_by_id(tree, ids.MAIN_TASKS_LIST)
    for task in main_tasks:
        elem = add_main_tasks_bullet_list_element(elem, task)

    ###############################################################
    # fill blockers list

    blockers = get_blockers()

    blocker_list_header = word.find_by_id(tree, ids.BLOCKERS_LIST)

    if blockers:
        # fill blockers in list
        element = blocker_list_header
        for blocker in blockers:
            link = Link(blocker["link"], blocker["key"])
            desc = blocker["description"]

            element = add_blocker_bullet_list_element(element, link, desc)
    else:  # remove blockers header
        word.remove_element(blocker_list_header)

    ###############################################################
    # update bugs links

    projects_bugs = get_bugs(report_date)

    for project in projects_bugs:
        link_id = ids.BUGS_LINK_ID[project]

        description = "New bugs ({amount})".format(
            amount=projects_bugs[project]["count"]
        )

        # update link address
        word.update_link(
            tree, link_id=link_id, url=projects_bugs[project]["link"], text=description
        )

    ###############################################################
    # update report period in footer

    footer_tree = word.load_xml(word.FOOTER_PATH)

    report_period_field = word.find_by_id(footer_tree, ids.REPORT_PERIOD_FIELD_ID)
    report_period_field.text = "{from_date} - {to_date}".format(
        from_date=report_start_date.strftime("%d-%B-%Y"),
        to_date=report_date.strftime("%d-%B-%Y"),
    )

    word.write_xml(footer_tree, word.FOOTER_PATH)

    ###############################################################
    # import images

    available_charts = export_charts()

    # for pages allignment
    projects_with_charts = set()

    # for testing purposes
    # available_charts = {
    #     Projects.MAYA_RPR: {
    #         # ChartType.UNRESOLVED_ISSUES: "",
    #         # ChartType.ISSUES_UPDATES_2W: ""
    #         ChartType.UNRESOLVED_ISSUES: "pics/chart_1_1.png",
    #         ChartType.ISSUES_UPDATES_2W: "pics/chart_1_2.png",
    #     },
    #     Projects.MAYA_USD: {
    #         # ChartType.UNRESOLVED_ISSUES: "",
    #         # ChartType.ISSUES_UPDATES_2W: ""
    #         ChartType.UNRESOLVED_ISSUES: "pics/chart_2_1.png",
    #         ChartType.ISSUES_UPDATES_2W: "pics/chart_2_2.png",
    #     },
    #     Projects.BLENDER_RPR: {
    #         # ChartType.UNRESOLVED_ISSUES: "",
    #         # ChartType.ISSUES_UPDATES_2W: ""
    #         ChartType.UNRESOLVED_ISSUES: "pics/chart_3_1.png",
    #         ChartType.ISSUES_UPDATES_2W: "pics/chart_3_2.png",
    #     },
    #     Projects.BLENDER_USD: {
    #         # ChartType.UNRESOLVED_ISSUES: "",
    #         # ChartType.ISSUES_UPDATES_2W: ""
    #         ChartType.UNRESOLVED_ISSUES: "pics/chart_4_1.png",
    #         ChartType.ISSUES_UPDATES_2W: "pics/chart_4_2.png",
    #     },
    #     Projects.HOUDINI: {
    #         # ChartType.UNRESOLVED_ISSUES: "",
    #         # ChartType.ISSUES_UPDATES_2W: ""
    #         ChartType.UNRESOLVED_ISSUES: "pics/chart_7_1.png",
    #         ChartType.ISSUES_UPDATES_2W: "pics/chart_7_2.png",
    #     },
    # }

    for project in ids.CHART_ID:
        for chart_type in ChartType:
            # if new chart available
            new_chart_path = available_charts[project][chart_type]
            if new_chart_path:
                update_chart(tree, project, chart_type, new_chart_path)

                # remember this project for further allignment
                projects_with_charts.add(project)
            else:
                # remove chart and chart header if there is no chart
                remove_chart(tree, project, chart_type)

    ###############################################################
    # fix images overlap with footer
    # add page break if there are more than 7 added elements (table + task lists)

    for project in projects_with_charts:
        if project_added_elements[project] >= 8:  # magic number
            # create page break element
            page_break = word.create_page_break()

            # find a place for a page break (after bugs link)
            bugs_link_paragraph = word.find_by_id(tree, ids.BUGS_LINK_ID[project])
            word.append_element_after(new_el=page_break, after=bugs_link_paragraph)

    ###############################################################

    # save report document.xml
    word.write_xml(tree, word.DOCUMENT_PATH)

    # combine files into docx
    finalize_report()

    print(f"Report '{REPORT_FILE_PATH}' generated!")

    clean_working_dir()


if __name__ == "__main__":
    main()
