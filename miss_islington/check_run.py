import re

from gidgethub import routing

from . import util
from .status_change import check_ci_status_and_approval

router = routing.Router()

TITLE_RE = re.compile(r"\[(?P<branch>\d+\.\d+)\].+?(?P<pr>\d+)\)")
AUTOMERGE_TRAILER = "Automerge-Triggered-By"


@router.register("check_run", action="completed")
async def check_run_completed(event, gh, *args, **kwargs):
    """
    A check run is completed event handler.
    """
    sha = event.data["check_run"]["head_sha"]

    if event.data["sender"]["login"] == "miss-islington":
        await check_ci_status_and_approval(gh, sha, leave_comment=True)
    else:
        pr_for_commit = await util.get_pr_for_commit(gh, sha)
        if pr_for_commit:
            pr_labels = pr_for_commit["labels"]
            print("is auomer")
            print(util.pr_is_automerge(pr_labels))
            print(util.pr_is_awaiting_merge(pr_labels))
            print("pr label")
            print(pr_labels)
            if util.pr_is_automerge(pr_labels) and util.pr_is_awaiting_merge(pr_labels):
                await check_ci_status_and_approval(
                    gh,
                    sha,
                    pr_for_commit=pr_for_commit,
                    leave_comment=True,
                    is_automerge=True,
                )
