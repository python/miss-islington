import asyncio

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
        if event.data["pull_request"]["merged"]:
            await gh.delete(url)
        else:
            # this is delayed to ensure that the bot doesn't remove the branch
            # if PR was closed and reopened to rerun checks (or similar)
            await asyncio.sleep(60)
            updated_data = await gh.getitem(event.data["pull_request"]["url"])
            if updated_data["state"] == "closed":
                await gh.delete(url)
