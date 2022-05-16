import re
import subprocess

import gidgethub

from .status_change import AUTOMERGE_TRAILER

AUTOMERGE_LABEL = ":robot: automerge"
AWAITING_MERGE_LABEL = "awaiting merge"

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


def normalize_message(body):
    """Normalize the message body to make it commit-worthy.

    Mostly this just means removing HTML comments, but also removes unwanted
    leading or trailing whitespace.

    Returns the normalized body.
    """
    while "<!--" in body:
        body = body[: body.index("<!--")] + body[body.index("-->") + 3 :]
    # Delete BPO link added by Bedevere.
    body = re.sub(r"https://bugs.python.org/issue(\d+)", "", body)
    # Strip additional newlines between commit body and automerge label.
    body_parts = body.split(AUTOMERGE_TRAILER)
    if len(body_parts) > 1:
        body, automerge_user = body_parts
        body = f"{body.strip()}\n\n{AUTOMERGE_TRAILER}{automerge_user}"
    return "\n\n" + body.strip()


# Copied over from https://github.com/python/bedevere
async def is_core_dev(gh, username):
    """Check if the user is a CPython core developer."""
    org_teams = "/orgs/python/teams"
    team_name = "python core"
    async for team in gh.getiter(org_teams):
        if team["name"].lower() == team_name:  # pragma: no branch
            break
    else:
        raise ValueError(f"{team_name!r} not found at {org_teams!r}")
    # The 'teams' object only provides a URL to a deprecated endpoint,
    # so manually construct the URL to the non-deprecated team membership
    # endpoint.
    membership_url = f"/teams/{team['id']}/memberships/{username}"
    try:
        await gh.getitem(membership_url)
    except gidgethub.BadRequest as exc:
        if exc.status_code == 404:
            return False
        raise
    else:
        return True


def pr_is_awaiting_merge(pr_labels):
    label_names = [label["name"] for label in pr_labels]
    if (
        "DO-NOT-MERGE" not in label_names
        and "awaiting merge" in label_names
        and "CLA not signed" not in label_names
    ):
        return True
    return False


def pr_is_automerge(pr_labels):
    for label in pr_labels:
        if label["name"] == AUTOMERGE_LABEL:
            return True
    return False


async def get_pr_for_commit(gh, sha):
    prs_for_commit = await gh.getitem(
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}"
    )
    if prs_for_commit["total_count"] > 0:  # there should only be one
        pr_for_commit = prs_for_commit["items"][0]
        return pr_for_commit
    return None


async def remove_automerge(gh, pr_data):
    """Remove the automerge label"""
    await gh.delete(
        f"{pr_data['issue_url']}/labels/{AUTOMERGE_LABEL}",
        accept="application/vnd.github.symmetra-preview+json",
    )


async def remove_awaiting_merge(gh, pr_data):
    """Remove the automerge label"""
    await gh.delete(
        f"{pr_data['issue_url']}/labels/{AWAITING_MERGE_LABEL}",
        accept="application/vnd.github.symmetra-preview+json",
    )


async def get_check_runs_for_sha(gh, sha):
    return await gh.getitem(
        f"/repos/python/cpython/commits/{sha}/check-runs",
        accept="application/vnd.github.antiope-preview+json",
    )
