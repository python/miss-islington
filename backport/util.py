import requests
import os
import subprocess

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
