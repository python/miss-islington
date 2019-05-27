import asyncio
import os
import random

import gidgethub.routing
from kombu import exceptions as kombu_ex
from redis import exceptions as redis_ex

from . import tasks, util

EASTER_EGG = "I'm not a witch! I'm not a witch!"

router = gidgethub.routing.Router()


@router.register("pull_request", action="closed")
@router.register("pull_request", action="labeled")
async def backport_pr(event, gh, *args, **kwargs):
    if event.data["pull_request"]["merged"]:

        issue_number = event.data["pull_request"]["number"]
        merged_by = event.data["pull_request"]["merged_by"]["login"]
        created_by = event.data["pull_request"]["user"]["login"]

        commit_hash = event.data["pull_request"]["merge_commit_sha"]

        pr_labels = []
        if event.data["action"] == "labeled":
            pr_labels = [event.data["label"]]
        else:
            gh_issue = await gh.getitem(
                event.data["repository"]["issues_url"],
                {"number": f"{event.data['pull_request']['number']}"},
            )
            pr_labels = await gh.getitem(gh_issue["labels_url"])

        branches = [
            label["name"].split()[-1]
            for label in pr_labels
            if label["name"].startswith("needs backport to")
        ]

        if branches:
            easter_egg = ""
            if random.random() < 0.1:
                easter_egg = EASTER_EGG
            thanks_to = ""
            if created_by == merged_by or merged_by == "miss-islington":
                thanks_to = f"Thanks @{created_by} for the PR 🌮🎉."
            else:
                thanks_to = f"Thanks @{created_by} for the PR, and @{merged_by} for merging it 🌮🎉."
            message = (
                f"{thanks_to}. I'm working now to backport this PR to: {', '.join(branches)}."
                f"\n🐍🍒⛏🤖 {easter_egg}"
            )

            await util.leave_comment(gh, issue_number, message)

            sorted_branches = sorted(
                branches, reverse=True, key=lambda v: tuple(map(int, v.split(".")))
            )

            for branch in sorted_branches:
                await kickoff_backport_task(
                    gh, commit_hash, branch, issue_number, created_by, merged_by
                )


async def kickoff_backport_task(
    gh, commit_hash, branch, issue_number, created_by, merged_by, retry_num=0
):
    try:
        tasks.backport_task.delay(
            commit_hash,
            branch,
            issue_number=issue_number,
            created_by=created_by,
            merged_by=merged_by,
        )
    except (redis_ex.ConnectionError, kombu_ex.OperationalError) as ex:
        retry_num = retry_num + 1
        if retry_num < 5:
            err_message = f"I'm having trouble backporting to `{branch}`. Reason: '`{ex}`'. Will retry in 1 minute. Retry # {retry_num}"
            await util.leave_comment(gh, issue_number, err_message)
            await asyncio.sleep(int(os.environ.get("RETRY_SLEEP_TIME", "60")))
            await kickoff_backport_task(
                gh,
                commit_hash,
                branch,
                issue_number,
                created_by,
                merged_by,
                retry_num=retry_num,
            )
        else:
            err_message = f"I'm still having trouble backporting after {retry_num} attempts. Please backport manually."
            await util.leave_comment(gh, issue_number, err_message)
            await util.assign_pr_to_core_dev(gh, issue_number, merged_by)
