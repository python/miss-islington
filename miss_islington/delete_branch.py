import gidgethub.routing
from kombu import exceptions as kombu_ex
from redis import exceptions as redis_ex
import stamina

from . import tasks

router = gidgethub.routing.Router()


@router.register("pull_request", action="closed")
async def delete_branch(event, gh, *args, **kwargs):
    """
    Delete the branch once miss-islington's PR is closed.
    """
    if event.data["pull_request"]["user"]["login"] == "miss-islington":
        branch_name = event.data["pull_request"]["head"]["ref"]
        merged = event.data["pull_request"]["merged"]
        pr_url = event.data["pull_request"]["url"]
        installation_id = event.data["installation"]["id"]
        _queue_delete_task(branch_name, pr_url, merged, installation_id)


@stamina.retry(on=(redis_ex.ConnectionError, kombu_ex.OperationalError), timeout=30)
def _queue_delete_task(branch_name, pr_url, merged, installation_id):
    tasks.delete_branch_task.delay(
        branch_name,
        pr_url,
        merged,
        installation_id=installation_id
    )
