import gidgethub.routing

router = gidgethub.routing.Router()


@router.register("pull_request", action="closed")
async def delete_branch(event, gh, *args, **kwargs):
    """
    Delete the branch once miss-islington's PR is closed.
    """
    if event.data["pull_request"]["user"]["login"] == "miss-islington":
        branch_name = event.data["pull_request"]["head"]["ref"]
        url = f"/repos/miss-islington/cpython/git/refs/heads/{branch_name}"
        await gh.delete(url)
