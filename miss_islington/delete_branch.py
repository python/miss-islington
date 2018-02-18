import gidgethub.routing

from . import util

router = gidgethub.routing.Router()


@router.register("pull_request", action="closed")
async def delete_branch(event, gh, *args, **kwargs):
    """
    Delete the branch once miss-islington's PR is closed.
    Say thanks if it's merged.
    """
    if event.data["pull_request"]["user"]["login"] == "miss-islington":
        if event.data["pull_request"]["merged"]:
            issue_number = event.data['pull_request']['number']
            merged_by = event.data['pull_request']['merged_by']['login']
            if merged_by != "miss-islington":
                await util.leave_comment(gh, issue_number, f"Thanks, @{merged_by}!")
            else:
                await util.leave_comment(gh, issue_number, "Thanks!")

        branch_name = event.data['pull_request']['head']['ref']
        url = f"/repos/miss-islington/cpython/git/refs/heads/{branch_name}"
        await gh.delete(url)

