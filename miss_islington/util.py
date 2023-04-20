import re
import subprocess

import gidgethub



async def comment_on_pr(gh, issue_number, message):
    """
    Leave a comment on a PR/Issue
    """
    issue_comment_url = f"/repos/python/cpython/issues/{issue_number}/comments"
    data = {"body": message}
    response = await gh.post(issue_comment_url, data=data)
    print(f"Commented at {response['html_url']}, message: {message}")
    return response


async def assign_pr_to_core_dev(gh, issue_number, coredev_login):
    """
    Assign the PR to a core dev.  Should be done when miss-islington failed
    to backport.
    """

    edit_issue_url = f"/repos/python/cpython/issues/{issue_number}"
    data = {"assignees": [coredev_login]}
    await gh.patch(edit_issue_url, data=data)


async def leave_comment(gh, pr_number, message):
    """
    Leave a comment on a PR/Issue
    """
    issue_comment_url = f"/repos/python/cpython/issues/{pr_number}/comments"
    data = {"body": message}
    await gh.post(issue_comment_url, data=data)


def is_cpython_repo():
    cmd = "git log -r 7f777ed95a19224294949e1b4ce56bbffcb1fe9f"
    try:
        subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
    except subprocess.SubprocessError:
        return False
    return True


async def get_gh_participants(gh, pr_number):
    pr_url = f"/repos/python/cpython/pulls/{pr_number}"
    pr_result = await gh.getitem(pr_url)
    created_by = pr_result["user"]["login"]

    merged_by = None
    if pr_result["merged_by"] and pr_result["merged_by"]["login"] != "miss-islington":
        merged_by = pr_result["merged_by"]["login"]

    participants = ""
    if created_by == merged_by or merged_by is None:
        participants = f"@{created_by}"
    else:
        participants = f"@{created_by} and @{merged_by}"

    return participants


def get_participants(created_by, merged_by):
    participants = ""
    if created_by == merged_by or merged_by == "miss-islington":
        participants = f"@{created_by}"
    else:
        participants = f"@{created_by} and @{merged_by}"
    return participants


def normalize_title(title, body):
    """Normalize the title if it spills over into the PR's body."""
    if not (title.endswith("…") and body.startswith("…")):
        return title
    else:
        # Being paranoid in case \r\n is used.
        return title[:-1] + body[1:].partition("\r\n")[0]

