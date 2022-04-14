import re

import gidgethub
from gidgethub import routing

from . import util

router = routing.Router()

TITLE_RE = re.compile(r"\[(?P<branch>\d+\.\d+)\].+?(?P<pr>\d+)\)")
AUTOMERGE_TRAILER = "Automerge-Triggered-By"


@router.register("status")
async def check_status(event, gh, *args, **kwargs):
    """
    Check the state change
    """
    sha = event.data["sha"]

    if (
        event.data["commit"].get("committer")
        and event.data["commit"]["committer"]["login"] == "miss-islington"
    ):
        await check_ci_status_and_approval(gh, sha, leave_comment=True)
    else:
        pr_for_commit = await util.get_pr_for_commit(gh, sha)
        if pr_for_commit:
            pr_labels = pr_for_commit["labels"]
            if util.pr_is_automerge(pr_labels) and util.pr_is_awaiting_merge(pr_labels):
                await check_ci_status_and_approval(
                    gh,
                    sha,
                    pr_for_commit=pr_for_commit,
                    leave_comment=True,
                    is_automerge=True,
                )


@router.register("pull_request", action="labeled")
async def pr_reviewed(event, gh, *args, **kwargs):

    pr_labels = event.data["pull_request"]["labels"]
    sender = event.data["sender"]["login"]
    label = event.data["label"]["name"]

    if label == util.AUTOMERGE_LABEL:
        if await util.is_core_dev(gh, sender):
            await add_automerged_by(gh, event.data["pull_request"], sender)
        else:
            await util.remove_automerge(gh, event.data["pull_request"])
            return

    if util.pr_is_automerge(pr_labels) and util.pr_is_awaiting_merge(pr_labels):
        sha = event.data["pull_request"]["head"]["sha"]

        await check_ci_status_and_approval(
            gh, sha, pr_for_commit=event.data["pull_request"], is_automerge=True
        )
    elif event.data["pull_request"]["user"][
        "login"
    ] == "miss-islington" and util.pr_is_awaiting_merge(
        event.data["pull_request"]["labels"]
    ):
        sha = event.data["pull_request"]["head"]["sha"]
        await check_ci_status_and_approval(
            gh, sha, pr_for_commit=event.data["pull_request"]
        )


async def check_ci_status_and_approval(
    gh, sha, pr_for_commit=None, leave_comment=False, is_automerge=False
):

    result = await gh.getitem(f"/repos/python/cpython/commits/{sha}/status")
    all_ci_status = [status["state"] for status in result["statuses"]]

    check_runs = await util.get_check_runs_for_sha(gh, sha)

    all_check_run_status = [
        check_run["status"] for check_run in check_runs["check_runs"]
    ]
    all_check_run_conclusions = [
        check_run["conclusion"] for check_run in check_runs["check_runs"]
    ]

    if (
        "pending" not in all_ci_status
        and "in_progress" not in all_check_run_status
        and "queued" not in all_check_run_status
    ):  # wait until all status and check runs are completed

        if not pr_for_commit:
            pr_for_commit = await util.get_pr_for_commit(gh, sha)
        if pr_for_commit:
            pr_number = pr_for_commit["number"]
            normalized_pr_title = util.normalize_title(
                pr_for_commit["title"], pr_for_commit["body"]
            )

            title_match = TITLE_RE.match(normalized_pr_title)
            if title_match or is_automerge:
                success = result["state"] == "success" and not any(
                    elem in [None, "failure", "timed_out"]
                    for elem in all_check_run_conclusions
                )
                if leave_comment:
                    if is_automerge:
                        participants = await util.get_gh_participants(gh, pr_number)
                    else:
                        original_pr_number = title_match.group("pr")
                        participants = await util.get_gh_participants(
                            gh, original_pr_number
                        )
                    if success:
                        emoji = "✅"
                        description = "success"
                    else:
                        emoji = "❌"
                        description = "failure"
                    await util.leave_comment(
                        gh,
                        pr_number=pr_number,
                        message=f"{participants}: Status check is done, and it's a {description} {emoji} .",
                    )
                if success:
                    if util.pr_is_awaiting_merge(pr_for_commit["labels"]):
                        await merge_pr(
                            gh, pr_for_commit, sha, is_automerge=is_automerge
                        )


async def merge_pr(gh, pr, sha, is_automerge=False):
    pr_number = pr["number"]
    async for commit in gh.getiter(f"/repos/python/cpython/pulls/{pr_number}/commits"):
        if commit["sha"] == sha:  # pragma: no branch
            if is_automerge:
                pr_commit_msg = util.normalize_message(pr["body"])
                pr_title = f"{pr['title']} (GH-{pr_number})"
            else:
                commit_msg = commit["commit"]["message"].split("\n")
                pr_commit_msg = "\n".join(commit_msg[1:])
                pr_title = f"{commit_msg[0]}"

            data = {
                "commit_title": pr_title,
                "commit_message": pr_commit_msg,
                "sha": sha,
                "merge_method": "squash",
            }
            try:
                await gh.put(
                    f"/repos/python/cpython/pulls/{pr_number}/merge", data=data
                )
            except gidgethub.BadRequest as err:
                await util.comment_on_pr(
                    gh, pr_number, f"Sorry, I can't merge this PR. Reason: `{err}`."
                )
            break


async def add_automerged_by(gh, pr_data, username):
    new_pr_body = f"{pr_data['body'].rstrip()}\n\n{AUTOMERGE_TRAILER}: GH:{username}"
    await gh.patch(pr_data["url"], data={"body": new_pr_body})
