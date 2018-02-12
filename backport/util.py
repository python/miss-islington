import requests
import os
import subprocess

import gidgethub

from gidgethub import sansio


def comment_on_pr(issue_number, message):
    """
    Leave a comment on a PR/Issue
    """
    request_headers = sansio.create_headers(
        "miss-islington",
        oauth_token=os.getenv('GH_AUTH'))
    issue_comment_url = f"https://api.github.com/repos/python/cpython/issues/{issue_number}/comments"
    data = {
        "body": message,
    }
    response = requests.post(issue_comment_url,
                             headers=request_headers,
                             json=data)
    if response.status_code == requests.codes.created:
        print(f"Commented at {response.json()['html_url']}, message: {message}")
    else:
        print(response.status_code)
        print(response.text)


def user_login(item):
    return item["user"]["login"]


def is_cpython_repo():
    cmd = "git log -r 7f777ed95a19224294949e1b4ce56bbffcb1fe9f"
    try:
        subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
    except subprocess.SubprocessError:
        return False
    return True


def get_participants(created_by, merged_by):
    participants = ""
    if created_by == merged_by:
        participants = f"@{created_by}"
    else:
        participants = f"@{created_by} and @{merged_by}"
    return participants


def delete_branch(branch_name):
    """
    Delete the branch on GitHub
    """
    request_headers = sansio.create_headers(
        "miss-islington",
        oauth_token=os.environ.get('GH_AUTH'))
    url = f"https://api.github.com/repos/miss-islington/cpython/git/refs/heads/{branch_name}"
    response = requests.delete(url, headers=request_headers)
    if response.status_code == 204:
        print(f"{branch_name} branch deleted.")
    else:
        print(f"Couldn't delete the branch {branch_name}")


def normalize_title(title, body):
    """Normalize the title if it spills over into the PR's body."""
    if not (title.endswith('…') and body.startswith('…')):
        return title
    else:
        # Being paranoid in case \r\n is used.
        return title[:-1] + body[1:].partition('\r\n')[0]

# Copied over from https://github.com/python/bedevere
async def is_core_dev(gh, username):
    """Check if the user is a CPython core developer."""
    org_teams = "/orgs/python/teams"
    team_name = "python core"
    async for team in gh.getiter(org_teams):
        if team["name"].lower() == team_name:
            break
    else:
        raise ValueError(f"{team_name!r} not found at {org_teams!r}")
    # The 'teams' object only provides a URL to a deprecated endpoint,
    # so manually construct the URL to the non-deprecated team membership
    # endpoint.
    membership_url = f"/teams/{team['id']}/memberships/{username}"
    print(f"membership url {membership_url}")
    try:
        await gh.getitem(membership_url)
    except gidgethub.BadRequest as exc:
        print("badrequest")
        if exc.status_code == 404:
            print("404")
            return False
        raise
    else:
        print("return rtw")
        return True