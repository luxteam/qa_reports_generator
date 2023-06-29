import os
from datetime import datetime, timedelta, date
from atlassian import Jira
from common import Projects, IssueType
import json
import urllib
from typing import List

JIRA_URL = os.getenv("JIRA_URL", "https://amdrender.atlassian.net/")
JIRA_USERNAME = os.environ["JIRA_USERNAME"]
JIRA_TOKEN = os.environ["JIRA_TOKEN"]


jira_instance = Jira(
    # Url of jira server
    url=JIRA_URL,
    # loginuser name
    username=JIRA_USERNAME,
    # password/token
    password=JIRA_TOKEN,
    cloud=True,
)

projects_jira_names = {
    Projects.MAYA_RPR: "RPRMAYA",
    Projects.MAYA_USD: "MAYAUS",
    Projects.BLENDER_RPR: "RPRBLND",
    Projects.BLENDER_USD: "BLEN",
    Projects.RENDER_STUDIO: "RS",
    Projects.SOLIDWORKS: "SV",
    Projects.HOUDINI: "RPRHOUD",
    Projects.HDRPR: "RPRUSD",
    Projects.RPRHYBRID: "RPRHYB",
    Projects.INVENTOR: "INV",
}

jira_open_statuses_list = [
    "Assessment",
    "Backlog",
    "Blocked",
    "Deployment",
    "In Progress",
    "In Review",
    "In Test",
    "In Testing",
    "Needs Merging",
    "Open",
    "Planning",
    "Reopened",
    "Selected for development",
    "Testing / QA",
    "Testing/QA",
    "To Do",
    "Waiting for Merge",
]

projects_jira_open_statuses = {
    Projects.MAYA_RPR: '"In Progress","Assessment","In Review","In Test","Open","Reopened",Blocked',
    Projects.MAYA_USD: '"In Progress","Assessment","In Review","In Test","Open","Reopened",Blocked',
    Projects.BLENDER_RPR: '"In Progress","Assessment","In Review","In Test","Open","Reopened",Blocked',
    Projects.BLENDER_USD: '"In Progress","Assessment","In Review","In Test","Open","Reopened",Blocked',
    Projects.RENDER_STUDIO: 'Backlog,Blocked,"In Progress","Testing/QA","To Do","Waiting for Merge"',
    Projects.HOUDINI: '"Backlog","Blocked","In Progress","Selected for development","Testing / QA"',
    Projects.HDRPR: '"Backlog","In Progress","In Testing","Selected for Development","To Do",Blocked',
    Projects.SOLIDWORKS: '"Blocked","In Progress","In Test","Needs Merging","To Do"',
    Projects.RPRHYBRID: 'Assessment,Deployment,Blocked,"In Progress","In Review","In Test",Open,Planning,Reopened,"To Do"',
    Projects.INVENTOR: '"In Progress", "In Testing", Open, Reopened',
}


def get_blockers_link(project: Projects, report_date: datetime) -> str:
    name = projects_jira_names[project]
    jql_request = "project = {name} AND issuetype in (Bug, Sub-task) AND status in ({statuses}) AND priority = Blocker AND created < '{to_datetime}' ORDER BY created DESC".format(
        name=name,
        statuses=projects_jira_open_statuses[project],
        to_datetime=(report_date + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
    )
    return (
        JIRA_URL
        + f"/jira/software/c/projects/{name}/issues/?jql="
        + urllib.parse.quote(jql_request)
    )


def get_crits_link(project: Projects, report_date: datetime) -> str:
    name = projects_jira_names[project]
    jql_request = "project = {name} AND issuetype in (Bug, Sub-task) AND status in ({statuses}) AND priority = Critical AND created < '{to_datetime}' ORDER BY created DESC".format(
        name=name,
        statuses=projects_jira_open_statuses[project],
        to_datetime=(report_date + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
    )
    return (
        JIRA_URL
        + f"/jira/software/c/projects/{name}/issues/?jql="
        + urllib.parse.quote(jql_request)
    )


def get_project_blockers(project: Projects, report_date: datetime) -> List[dict]:

    jql_request = "project = {name} AND issuetype in (Bug, Sub-task) AND status in ({statuses}) AND priority = Blocker AND created < '{to_datetime}' ORDER BY created DESC".format(
        name=projects_jira_names[project],
        statuses=projects_jira_open_statuses[project],
        to_datetime=(report_date + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
    )
    issues = jira_instance.jql(jql_request).get("issues")

    blockers = []
    for issue in issues:
        blocker = {
            "key": issue["key"],
            "link": JIRA_URL + "/browse/" + issue["key"],
            "description": issue["fields"]["summary"],
        }
        blockers.append(blocker)

    return blockers


def get_project_crits(project: Projects, report_date: datetime):
    jql_request = "project = {name} AND issuetype in (Bug, Sub-task) AND status in ({statuses}) AND priority = Critical AND created < '{to_datetime}' ORDER BY created DESC".format(
        name=projects_jira_names[project],
        statuses=projects_jira_open_statuses[project],
        to_datetime=(report_date + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
    )
    issues = jira_instance.jql(jql_request).get("issues")

    crits = []
    for issue in issues:
        crit = {
            "key": issue["key"],
            "link": JIRA_URL + "/browse/" + issue["key"],
            "description": issue["fields"]["summary"],
        }
        crits.append(crit)

    return crits


def get_blockers(report_date: datetime):
    blockers = {}
    for project in projects_jira_names:
        blockers[project] = get_project_blockers(project, report_date)

    return blockers


def get_crits(report_date: datetime):
    crits = {}
    for project in projects_jira_names:
        crits[project] = get_project_crits(project, report_date)

    return crits


def get_bugs(report_date: datetime):
    new_bugs = {}

    for project in projects_jira_names:
        project_jira_name = projects_jira_names[project]

        jql_request = "created >= {from_date} AND created < '{to_datetime}' AND project = {project} AND issuetype in (Bug, Sub-task) ORDER BY created DESC".format(
            from_date=(report_date - timedelta(weeks=2) + timedelta(days=1)).strftime(
                "%Y-%m-%d"
            ),
            to_datetime=(report_date + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
            project=project_jira_name,
        )
        issues = jira_instance.jql(jql_request)
        count = issues["total"]

        link = (
            JIRA_URL
            + "/issues/?jql="
            + urllib.parse.quote(
                "project = {project} AND issuetype in (Bug, Sub-task) AND created >= {from_date} AND created < '{to_datetime}' ORDER BY created DESC".format(
                    from_date=(
                        report_date - timedelta(weeks=2) + timedelta(days=1)
                    ).strftime("%Y-%m-%d"),
                    to_datetime=(report_date + timedelta(days=1)).strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    project=project_jira_name,
                )
            )
        )

        new_bugs[project] = {"count": int(count), "link": link}

    return new_bugs


def get_issues_statistic(project: Projects, report_date: datetime, type: IssueType):
    # request issues list
    name = projects_jira_names[project]
    jql_request = f'project = {name} AND issuetype in (Bug, Sub-task) AND priority = {"Blocker" if type == IssueType.BLOCKER else "Critical"} AND (updated >= -26w OR status IN ({str(jira_open_statuses_list).replace("[","").replace("]","")})) ORDER BY created ASC'
    issues = jira_instance.jql(
        jql_request, fields="statuscategorychangedate, created, status"
    ).get("issues")

    # format issues list
    issues = [
        {
            "from": datetime.strptime(
                issue["fields"]["created"].split("T")[0], "%Y-%m-%d"
            ).date(),
            "to": date.today()
            if issue["fields"]["status"]["name"] in jira_open_statuses_list
            else datetime.strptime(
                issue["fields"]["statuscategorychangedate"].split("T")[0], "%Y-%m-%d"
            ).date(),
        }
        for issue in issues
    ]

    # prepare periods array
    period_end = report_date
    period_start = report_date - timedelta(weeks=1)
    intervals = []
    # 26 weeks = year
    while period_start >= (report_date - timedelta(weeks=26)):
        intervals.append({"from": period_start.date(), "to": period_end.date()})
        period_end = period_start
        period_start -= timedelta(weeks=1)

    intervals = intervals[::-1]  # reverse list

    # calculate
    issues_per_interval = [0 for _ in intervals]

    i = 0
    j = 0
    for issue in issues:
        while i < len(intervals) and issue["from"] > intervals[i]["to"]:
            i += 1
        j = i
        while j < len(intervals) and issue["to"] > intervals[j]["from"]:
            issues_per_interval[j] += 1
            j += 1

    intervals = [interval["to"] for interval in intervals]
    return (intervals, issues_per_interval)


if __name__ == "__main__":
    print("Bugs: ")
    bugs = get_bugs(datetime.today())
    for project in projects_jira_names:
        print(projects_jira_names[project] + ": ")
        print(json.dumps(bugs[project], indent=4))

    print("Blockers:")
    blockers = get_blockers()
    for project in blockers:
        print(projects_jira_names[project])
        print(json.dumps(blockers[project], indent=4))

    print("Criticals:")
    crits = get_crits()
    for project in crits:
        print(projects_jira_names[project])
        print(json.dumps(crits[project], indent=4))

    # import plotly.graph_objects as go

    # project = Projects.BLENDER_RPR
    # report_date = datetime.today()

    # intervals, blockers_per_interval = get_issues_statistic(project, report_date, IssueType.BLOCKER)
    # _, criticals_per_interval = get_issues_statistic(project, report_date, IssueType.CRITICAL)

    # different_values = len(set(blockers_per_interval + criticals_per_interval))

    # # create a scatter plot
    # fig = go.Figure(
    #     [
    #         go.Scatter(
    #             x = intervals,
    #             y = blockers_per_interval,
    #             name="Blocker",
    #             line_color="#FF5630"
    #         ),
    #         go.Scatter(
    #             x=intervals,
    #             y=criticals_per_interval,
    #             name="Critical",
    #             line_color="#0065FF"
    #         )
    #     ],
    #     layout=go.Layout(
    #         xaxis=dict(
    #             tickmode='array',
    #             tickvals=intervals,
    #             ticktext=[datetime(year=d.year, month=d.month, day=d.day).strftime("%m-%d-%Y") for d in intervals],
    #             tickangle=-45,
    #             automargin=True,
    #             showgrid=False,
    #             linecolor="#DADCE2",
    #         ),
    #         yaxis=dict(
    #             showgrid=True,
    #             gridcolor="#DADCE2",
    #             linecolor="#DADCE2",
    #             zeroline=False,
    #             tickformat=',d'
    #         ),
    #         height=200 + 300 * min(1, abs((different_values-2)/10)), # maximum 500,
    #         width=800,
    #         font=dict(
    #             size=10
    #         ),
    #         font_family="Segoe UI",
    #         legend=dict(
    #             orientation="h",
    #             yanchor="bottom",
    #             xanchor="right",
    #             y=1,
    #             x=1,
    #             font=dict(
    #                 size=15,
    #             )
    #         ),
    #         margin=dict(
    #             l=20,
    #             r=20,
    #             t=5,
    #             b=20
    #         ),
    #         plot_bgcolor='rgba(0,0,0,0)'
    #     ),
    # )
    # # workaround to avoid yaxis label 0, 0.2, 0.4, 0.6, 0.8, 1
    # max_value = max(max(criticals_per_interval), max(blockers_per_interval))
    # if max_value < 4:
    #     fig.update_yaxes(
    #         tickvals = [*range(max_value+1)]
    #     )

    # # save plot
    # path = f"./plot_{project}.png"
    # fig.write_image(path)
