import os
from datetime import datetime, timedelta, date
from atlassian import Jira
from common import Projects, IssueType
import json
import urllib

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
    # Projects.SOLIDWORKS: "SV",
    Projects.HOUDINI: "RPRHOUD",
}

projects_jira_open_statuses = {
    Projects.MAYA_RPR: '"In Progress","Assessment","In Review","In Test","Open","Reopened"',
    Projects.MAYA_USD: '"In Progress","Assessment","In Review","In Test","Open","Reopened"',
    Projects.BLENDER_RPR: '"In Progress","Assessment","In Review","In Test","Open","Reopened"',
    Projects.BLENDER_USD: '"In Progress","Assessment","In Review","In Test","Open","Reopened"',
    Projects.RENDER_STUDIO: '"In Progress","Backlog","Blocked","Testing / QA","Waiting for merge"',
    Projects.HOUDINI: '"Backlog","Blocked","In Progress","Selected for development","Testing / QA"'
}

def get_blockers_link(project: Projects):
    name = projects_jira_names[project]
    statuses = projects_jira_open_statuses[project]
    jql_request = f'project = {name} AND issuetype = Bug AND status in ({statuses}) AND priority = Blocker ORDER BY created DESC'
    return JIRA_URL + f"/jira/software/c/projects/{name}/issues/?jql=" + urllib.parse.quote(jql_request)

def get_crits_link(project: Projects):
    name = projects_jira_names[project]
    statuses = projects_jira_open_statuses[project]
    jql_request = f'project = {name} AND issuetype = Bug AND status in ({statuses}) AND priority = Critical ORDER BY created DESC'
    return JIRA_URL + f"/jira/software/c/projects/{name}/issues/?jql=" + urllib.parse.quote(jql_request)
 

def get_project_blockers(project: Projects):
    name = projects_jira_names[project]
    statuses = projects_jira_open_statuses[project]
    jql_request = f'project = {name} AND issuetype = Bug AND status in ({statuses}) AND priority = Blocker ORDER BY created DESC'
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

def get_project_crits(project: Projects):
    name = projects_jira_names[project]
    statuses = projects_jira_open_statuses[project]
    jql_request = f'project = {name} AND issuetype = Bug AND status in ({statuses}) AND priority = Critical ORDER BY created DESC'
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


def get_blockers():
    blockers = {}
    for project in projects_jira_names:
        blockers[project] = get_project_blockers(project)
    
    return blockers

def get_crits():
    crits = {}
    for project in projects_jira_names:
        crits[project] = get_project_crits(project)

    return crits

def get_bugs(report_date: datetime):
    new_bugs = {}

    for project in projects_jira_names:
        project_jira_name = projects_jira_names[project]

        jql_request = "created > {from_date} AND created <= {to_date} AND project = {project} AND issuetype = Bug ORDER BY created DESC".format(
            from_date=(report_date - timedelta(weeks=2)).strftime("%Y-%m-%d"),
            to_date=report_date.strftime("%Y-%m-%d"),
            project=project_jira_name,
        )
        issues = jira_instance.jql(jql_request)
        count = issues["total"]

        link = JIRA_URL + "/issues/?jql=" + urllib.parse.quote(
            "project = {project} AND issuetype = Bug AND created > {from_date} AND created <= {to_date} ORDER BY created DESC".format(
                from_date=(report_date - timedelta(weeks=2)).strftime("%Y-%m-%d"),
                to_date=report_date.strftime("%Y-%m-%d"),
                project=project_jira_name,
            )
        )

        new_bugs[project] = {"count": int(count), "link": link}

    return new_bugs

def get_issues_statistic(project: Projects, report_date: datetime, type: IssueType):
    # request issues list
    name = projects_jira_names[project]
    statuses = projects_jira_open_statuses[project]
    jql_request = f'project = {name} AND issuetype = Bug AND priority = {"Blocker" if type == IssueType.BLOCKER else "Critical"} AND (updated >= -26w OR status IN ({statuses})) ORDER BY created ASC'
    issues = jira_instance.jql(jql_request, fields="statuscategorychangedate, created, status").get("issues")

    open_statuses_list = [s.replace('"', "") for s in statuses.split(",")]

    # format issues list
    issues = [{
        "from": datetime.strptime(issue['fields']['created'].split("T")[0], "%Y-%m-%d").date(), 
        "to": date.today() if issue['fields']['status']['name'] in open_statuses_list else datetime.strptime(issue['fields']['statuscategorychangedate'].split("T")[0], "%Y-%m-%d").date()
        } for issue in issues]

    # prepare periods array
    period_end = report_date
    period_start = report_date - timedelta(weeks=2)
    intervals = []
    # 26 weeks = year
    while period_start >= (report_date - timedelta(weeks=26)):
        intervals.append({"from": period_start.date(), "to": period_end.date()})
        period_end = period_start
        period_start -= timedelta(weeks=2)

    intervals = intervals[::-1] # reverse list

    # calculate
    issues_per_interval = [0 for _ in intervals]  

    i = 0
    j = 0
    for issue in issues:
        while i < len(intervals) and issue['from'] > intervals[i]['to']:
            i += 1
        j = i
        while j < len(intervals) and issue['to'] > intervals[j]['from']:
            issues_per_interval[j] += 1
            j += 1

    intervals = [interval['to'] for interval in intervals]
    return (intervals, issues_per_interval)




if __name__ == "__main__":
    print("Bugs: ")
    bugs = get_bugs(datetime.today())
    for project in projects_jira_names:
        print(projects_jira_names[project] + ": ")
        print(json.dumps(bugs[project], indent=4))

    print("Blockers:")
    blockers = get_blockers()
    for blocker in blockers:
        print(json.dumps(blocker, indent=4))