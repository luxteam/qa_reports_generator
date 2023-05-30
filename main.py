import os
from lxml import etree
from typing import List, Dict, Tuple
import shutil
from datetime import datetime, timedelta
from PIL import Image
import plotly.graph_objects as go

import ids
from common import (
    Link,
    Projects,
    ChartType,
    TaskType,
    SummaryTableColumn,
    IssueType,
    TEMPLATE_PATH,
    WORKING_DIR_PATH,
    PICTURES_PATH,
)
from confluence_export import get_tasks, get_main_tasks
from jira_export import (
    get_blockers,
    get_bugs,
    get_crits,
    get_blockers_link,
    get_crits_link,
    get_issues_statistic,
)
from github_export import get_pull_requests_status, get_merged_prs
from jenkins_export import get_latest_build_data, get_wml_report_link
from charts_export import export_charts
import word

REPORT_FILE_PATH = "./weekly_qa_report-{date}.docx"


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
        if row_data["status"] == "Closed":
            word.set_table_cell_value(cells[1], "Approved by QA")
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


def fill_build_status_table(
    tree: etree.Element,
    project: Projects,
    build_data: Dict,
    blockers: Dict,
    crits: Dict,
):
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
    # Stable   - if not crits and blockers
    # Unstable -  if crits but no blockers
    # Failed   - if blockers
    if project in blockers and project in crits:
        has_blockers = len(blockers[project]) > 0
        has_crits = len(crits[project]) > 0

        if not has_blockers and not has_crits:  # stable
            content = word.Text(text="Stable", bold=True, hex_color="92D050")
        elif has_blockers:  # failed
            content = word.Text(text="Failed", bold=True, hex_color="FF0000")
        else:  # unstable
            content = word.Text(text="Unstable", bold=True, hex_color="E36C0A")

        word.set_table_cell_value(cells[3], content)

    # 4 cell - Comment ########################
    # if has crits or blockers add link
    if project in blockers and project in crits:
        has_blockers = len(blockers[project]) > 0
        has_crits = len(crits[project]) > 0

        if not has_blockers and not has_crits:  # stable
            pass
        elif has_blockers:  # failed
            word.clear_table_cell(cells[4])
            amount = len(blockers[project])
            content = Link(
                url=get_blockers_link(project), text=f"Blocker issues ({amount})"
            )
            word.set_table_cell_value(cells[4], content)
        else:  # unstable
            word.clear_table_cell(cells[4])
            amount = len(crits[project])
            content = Link(
                url=get_crits_link(project), text=f"Critical issues ({amount})"
            )
            word.set_table_cell_value(cells[4], content)


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


def replace_image(image_el, new_image_path):
    # identify chart placeholder file location
    image_placeholder_path = word.get_image_file_location(image_el)

    # replace file in archive
    os.replace(new_image_path, image_placeholder_path)

    # adjust new image size
    img = Image.open(image_placeholder_path)
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


def prepare_working_directory(report_file_path: str):
    # remove tmp dir if exists
    if os.path.exists(WORKING_DIR_PATH):
        shutil.rmtree(WORKING_DIR_PATH)

    # remove pics dir if exists
    if os.path.exists(PICTURES_PATH):
        shutil.rmtree(PICTURES_PATH)

    # remove report if exists
    if os.path.exists(report_file_path):
        os.remove(report_file_path)

    # copy template to the working directory
    shutil.copytree(TEMPLATE_PATH, WORKING_DIR_PATH)

    # create pics directory
    os.mkdir(PICTURES_PATH)


def clean_working_dir():
    # remove tmp directories
    shutil.rmtree(WORKING_DIR_PATH)
    shutil.rmtree(PICTURES_PATH)


def finalize_report(report_file_path: str):
    # archive directory
    shutil.make_archive(
        "report",
        "zip",
        WORKING_DIR_PATH,
    )
    # change it's extension to ".docx" and move to the right directory
    os.rename("report.zip", report_file_path)


def get_issues_plot(project: Projects, report_date: datetime):
    intervals, blockers_per_interval = get_issues_statistic(
        project, report_date, IssueType.BLOCKER
    )
    _, criticals_per_interval = get_issues_statistic(
        project, report_date, IssueType.CRITICAL
    )

    different_values = len(
        set(blockers_per_interval + criticals_per_interval)
    )  # to configure high of the plot

    # create a scatter plot
    fig = go.Figure(
        [
            go.Scatter(
                x=intervals,
                y=blockers_per_interval,
                name="Blocker",
                line_color="#FF5630",
            ),
            go.Scatter(
                x=intervals,
                y=criticals_per_interval,
                name="Critical",
                line_color="#0065FF",
            ),
        ],
        layout=go.Layout(
            xaxis=dict(
                tickmode="array",
                tickvals=intervals,
                ticktext=[
                    datetime(year=d.year, month=d.month, day=d.day).strftime("%m-%d-%Y")
                    for d in intervals
                ],
                tickangle=-45,
                automargin=True,
                showgrid=False,
                linecolor="#DADCE2",
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="#DADCE2",
                linecolor="#DADCE2",
                zeroline=False,
                tickformat=",d",
            ),
            height=200 + 300 * min(1, abs((different_values - 2) / 10)),  # maximum 500,
            width=1000,
            font=dict(size=10),
            font_family="Segoe UI",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                xanchor="right",
                y=1,
                x=1,
                font=dict(
                    size=15,
                ),
            ),
            margin=dict(l=20, r=20, t=5, b=20),
            plot_bgcolor="rgba(0,0,0,0)",
        ),
    )
    # workaround to avoid yaxis label 0, 0.2, 0.4, 0.6, 0.8, 1
    max_value = max(max(criticals_per_interval), max(blockers_per_interval))
    if max_value < 4:
        fig.update_yaxes(tickvals=[*range(max_value + 1)])

    # save plot
    path = PICTURES_PATH + f"/plot_{project}.png"
    fig.write_image(path)
    return path


def main():
    # eval report dates
    report_date = datetime.today()
    report_start_date = report_date - timedelta(weeks=2) + timedelta(days=1)

    report_path = REPORT_FILE_PATH.format(date=report_date.strftime("%d-%m-%Y"))

    prepare_working_directory(report_path)
    print("[0/11] Initial preparations...")

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
    print("[1/11] Projects status table...")

    blockers = get_blockers()
    crits = get_crits()

    for project in ids.BUILD_STATUS_TABLE_ROW:
        if project != Projects.WML:
            build_data = get_latest_build_data(project)
            fill_build_status_table(tree, project, build_data, blockers, crits)

    # WML link should be placed on the project page instead of projects table
    wml_report_link = get_wml_report_link()
    word.update_link(
        tree, link_id=ids.WML_BUILD_LINK, url=wml_report_link, text="Weekly report"
    )

    ###############################################################
    # update summary table
    print("[2/11] Summary table...")

    # Found issues
    found_issues = get_bugs(report_date)

    for project in found_issues:
        if project in [
            Projects.SOLIDWORKS,
            Projects.RPRHYBRID,
        ]:  # skip solidworks in this table for now
            continue

        table_cell_id = ids.SUMMARY_TABLE[project][SummaryTableColumn.FOUND_ISSUES]
        table_cell = word.find_by_id(tree, table_cell_id)

        text = "Issues ({amount})".format(amount=found_issues[project]["count"])
        url = found_issues[project]["link"]

        word.set_table_cell_value(table_cell, Link(url=url, text=text))

    # Merged PRs
    for project in ids.SUMMARY_TABLE:
        table_cell_id = ids.SUMMARY_TABLE[project][SummaryTableColumn.MERGED_PRS]
        table_cell = word.find_by_id(tree, table_cell_id)

        merged_prs = get_merged_prs(project, report_date)

        url = merged_prs["link"]
        text = "PRs ({amount})".format(amount=merged_prs["count"])

        word.set_table_cell_value(table_cell, Link(url=url, text=text))

    ###############################################################
    # update issues plots
    print("[3/11] Issue plots...")

    for project in ids.ISSUES_PLOT:
        plot_id = ids.ISSUES_PLOT[project]
        plot = word.find_by_id(tree, plot_id)

        plot_file_path = get_issues_plot(project, report_date)

        replace_image(image_el=plot, new_image_path=plot_file_path)

    ###############################################################
    # update PRs status tables
    print("[4/11] PRs status tables...")

    for project in ids.PR_STATUS_TABLE_ID:
        data = get_pull_requests_status(project, report_date)
        fill_pr_table(tree, project, data)

        project_added_elements[project] += len(data)

    ###############################################################
    # import tasks
    print("[5/11] Task lists...")

    projects_tasks = get_tasks(report_date)

    for project in ids.TASK_LISTS_ID:
        tasks = projects_tasks[project]
        task_lists = ids.TASK_LISTS_ID[project]

        fill_task_lists(tree, task_lists, tasks)

        project_added_elements[project] += len(tasks)

    ###############################################################
    # fill main tasks table
    print("[6/11] Main tasks...")

    main_tasks = get_main_tasks(projects_tasks)

    # fill summary task list with important tasks
    elem = word.find_by_id(tree, ids.MAIN_TASKS_LIST)
    for task in main_tasks:
        elem = add_main_tasks_bullet_list_element(elem, task)

    ###############################################################
    # fill blockers list
    print("[7/11] Blockers list...")

    blockers_by_proj = get_blockers()
    blockers = []
    for project in blockers_by_proj:
        blockers.extend(blockers_by_proj[project])

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
    print("[8/11] Bugs links")

    projects_bugs = get_bugs(report_date)

    for project in projects_bugs:
        if project in [
            Projects.SOLIDWORKS,
            Projects.RPRHYBRID,
        ]:  # skip Solidworks bugs link for now
            continue

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
    print("[9/11] Report dates...")

    footer_tree = word.load_xml(word.FOOTER_PATH)

    report_period_field = word.find_by_id(footer_tree, ids.REPORT_PERIOD_FIELD_ID)
    report_period_field.text = "{from_date} - {to_date}".format(
        from_date=report_start_date.strftime("%d-%B-%Y"),
        to_date=report_date.strftime("%d-%B-%Y"),
    )

    word.write_xml(footer_tree, word.FOOTER_PATH)

    ###############################################################
    # import images
    print("[10/11] Charts...")

    available_charts = export_charts()

    # for pages allignment
    projects_with_charts = set()

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
    print("[11/11] Saving report...")

    # save report document.xml
    word.write_xml(tree, word.DOCUMENT_PATH)

    # combine files into docx
    finalize_report(report_path)

    print(f"Report '{report_path}' generated!")

    clean_working_dir()


if __name__ == "__main__":
    main()
