import gidgethub.routing

import random

from . import tasks
from . import util

EASTER_EGG = "I'm not a witch! I'm not a witch!"

router = gidgethub.routing.Router()


@router.register("pull_request", action="closed")
@router.register("pull_request", action="labeled")
async def backport_pr(event, gh, *args, **kwargs):
    if event.data["pull_request"]["merged"]:

        issue_number = event.data['pull_request']['number']
        merged_by = event.data['pull_request']['merged_by']['login']
        created_by = event.data['pull_request']['user']['login']

        commit_hash = event.data['pull_request']['merge_commit_sha']

        gh_issue = await gh.getitem(event.data['repository']['issues_url'],
                                             {'number': f"{event.data['pull_request']['number']}"})

        pr_labels = await gh.getitem(gh_issue['labels_url'])
        branches = [label['name'].split()[-1]
                    for label in pr_labels
                        if label['name'].startswith("needs backport to")]

        if branches:
            easter_egg = ""
            if random.random() < 0.1:
                easter_egg = random.choice(EASTER_EGG)
            thanks_to = ""
            if created_by == merged_by:
                thanks_to = f"Thanks @{created_by} for the PR 🌮🎉."
            else:
                thanks_to = f"Thanks @{created_by} for the PR, and @{merged_by} for merging it 🌮🎉."
            message = f"""\
            {thanks_to}. I'm working now to backport this PR to: {', '.join(branches)}.
            🐍🍒⛏🤖 
            {easter_egg}
            """
            util.comment_on_pr(issue_number, message)

            for branch in branches:
                tasks.backport_task.delay(commit_hash,
                                          branch,
                                          issue_number=issue_number,
                                          created_by=created_by,
                                          merged_by=merged_by)
