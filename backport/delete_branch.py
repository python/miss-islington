import gidgethub.routing

from . import util

router = gidgethub.routing.Router()


@router.register("pull_request", action="closed")
async def delete_branch(event, gh, *args, **kwargs):
    """
    Delete the branch once PR is closed.
    Say thanks if it's merged.
    """
    if event.data["pull_request"]["merged"]:
        issue_number = event.data['pull_request']['number']
        merged_by = event.data['pull_request']['merged_by']['login']
        util.comment_on_pr(issue_number, f"Thanks, @{merged_by}!")

    branch_name = event.data['pull_request']['head']['ref']
    util.delete_branch(branch_name)

