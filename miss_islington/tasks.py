import asyncio
import logging
import os
import ssl
import subprocess

import aiohttp
import cachetools
import celery
from cherry_picker import cherry_picker
from celery import bootsteps
from gidgethub import aiohttp as gh_aiohttp
from gidgethub import apps
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration

from . import util

logger = logging.getLogger(__name__)

app = celery.Celery("backport_cpython")

app.conf.update(
    broker_url=os.environ.get("REDIS_URL", os.environ.get("HEROKU_REDIS_MAROON_URL", "")),
    result_backend=os.environ.get("REDIS_URL", os.environ.get("HEROKU_REDIS_MAROON_URL", "")),
    broker_connection_retry_on_startup=True,
    broker_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE},
    redis_backend_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE},
)

cache = cachetools.LRUCache(maxsize=500)
sentry_sdk.init(os.environ.get("SENTRY_DSN"), integrations=[CeleryIntegration()])

CHERRY_PICKER_CONFIG = {
    "team": "python",
    "repo": "cpython",
    "check_sha": "7f777ed95a19224294949e1b4ce56bbffcb1fe9f",
    "fix_commit_msg": True,
    "default_branch": "main",
    "require_version_in_branch_name": True,
    "draft_pr": False,
}


@app.task()
def setup_cpython_repo():
    logger.info("setting up CPython repository")  # pragma: nocover
    if "cpython" not in os.listdir("."):
        subprocess.check_output(
            f"git clone https://{os.environ.get('GH_AUTH')}:x-oauth-basic@github.com/miss-islington/cpython.git".split()
        )
        subprocess.check_output(
            "git config --global user.email 'mariatta.wijaya+miss-islington@gmail.com'".split()
        )
        subprocess.check_output(
            ["git", "config", "--global", "user.name", "'Miss Islington (bot)'"]
        )
        os.chdir("./cpython")
        subprocess.check_output(
            f"git remote add upstream https://{os.environ.get('GH_AUTH')}:x-oauth-basic@github.com/python/cpython.git".split()
        )
        logger.info("finished setting up CPython repository")
    else:
        logger.info("cpython directory already exists")


@app.task()
def backport_task(commit_hash, branch, *, issue_number, created_by, merged_by, installation_id):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        backport_task_asyncio(
            commit_hash,
            branch,
            issue_number=issue_number,
            created_by=created_by,
            merged_by=merged_by,
            installation_id=installation_id
        )
    )


async def backport_task_asyncio(
    commit_hash, branch, *, issue_number, created_by, merged_by, installation_id
):
    """Backport a commit into a branch."""
    async with aiohttp.ClientSession() as session:
        gh = gh_aiohttp.GitHubAPI(
            session, "python/cpython", cache=cache
        )
        # This path only works on GitHub App
        installation_access_token = await apps.get_installation_access_token(
            gh,
            installation_id=installation_id,
            app_id=os.environ.get("GH_APP_ID"),
            private_key=os.environ.get("GH_PRIVATE_KEY")
        )
        gh.oauth_token = installation_access_token["token"]
        if not util.is_cpython_repo():
            # cd to cpython if we're not already in it
            if "cpython" in os.listdir("."):
                os.chdir("./cpython")
            else:
                logger.warning(
                    "cpython directory not found",
                    extra={
                        "pwd": os.getcwd(),
                        "listdir": os.listdir("."),
                        "branch": branch,
                        "commit_hash": commit_hash,
                        "issue_number": issue_number,
                    },
                )

                await util.comment_on_pr(
                    gh,
                    issue_number,
                    f"""\
                    {util.get_participants(created_by, merged_by)}, I can't backport for now.  Please try again later or
                    backport using [cherry_picker](https://pypi.org/project/cherry-picker/) on command line.
                    ```
                    cherry_picker {commit_hash} {branch}
                    ```
                    """,
                )
                await util.assign_pr_to_core_dev(gh, issue_number, merged_by)

        # Ensure that we don't have any changes lying around
        subprocess.check_output(['git', 'reset', '--hard'])
        subprocess.check_output(['git', 'clean', '-fxd'])
        # Clear any leftover cherry-picker state from a previously interrupted
        # run; otherwise CherryPicker() init raises InvalidRepoException and
        # every subsequent backport on this worker silently fails.
        subprocess.run(
            ['git', 'config', '--local', '--remove-section', 'cherry-picker'],
            stderr=subprocess.DEVNULL,
            check=False,
        )

        try:
            cp = cherry_picker.CherryPicker(
                "origin",
                commit_hash,
                [branch],
                config=CHERRY_PICKER_CONFIG,
                prefix_commit=False,
            )
            cp.backport()
        except cherry_picker.InvalidRepoException as ire:
            await util.comment_on_pr(
                gh,
                issue_number,
                f"""\
                Sorry {util.get_participants(created_by, merged_by)}, I had trouble backporting to `{branch}`.
                Please retry by removing and re-adding the "needs backport to {branch}" label.
                Alternatively, you can backport using [cherry_picker](https://pypi.org/project/cherry-picker/) on the command line.
                ```
                cherry_picker {commit_hash} {branch}
                ```
                """,
            )
            await util.assign_pr_to_core_dev(gh, issue_number, merged_by)
            logger.exception(
                "backport failed: invalid repo state",
                extra={
                    "branch": branch,
                    "commit_hash": commit_hash,
                    "issue_number": issue_number,
                },
            )
        except cherry_picker.BranchCheckoutException as bce:
            await util.comment_on_pr(
                gh,
                issue_number,
                f"""\
                Sorry {util.get_participants(created_by, merged_by)}, I had trouble checking out the `{branch}` backport branch.
                Please retry by removing and re-adding the "needs backport to {branch}" label.
                Alternatively, you can backport using [cherry_picker](https://pypi.org/project/cherry-picker/) on the command line.
                ```
                cherry_picker {commit_hash} {branch}
                ```
                """,
            )
            await util.assign_pr_to_core_dev(gh, issue_number, merged_by)
            bce_state = cp.get_state_and_verify()
            logger.exception(
                "backport failed: branch checkout error",
                extra={
                    "branch": branch,
                    "commit_hash": commit_hash,
                    "issue_number": issue_number,
                    "state": bce_state.name,
                },
            )
            cp.abort_cherry_pick()
        except cherry_picker.CherryPickException as cpe:
            await util.comment_on_pr(
                gh,
                issue_number,
                f"""\
                Sorry, {util.get_participants(created_by, merged_by)}, I could not cleanly backport this to `{branch}` due to a conflict.

                Please backport manually with [cherry_picker](https://pypi.org/project/cherry-picker/), see the [devguide](https://devguide.python.org/getting-started/git-boot-camp/#backporting-merged-changes) for more information.
                ```
                cherry_picker {commit_hash} {branch}
                ```
                """,
            )
            await util.assign_pr_to_core_dev(gh, issue_number, merged_by)
            cpe_state = cp.get_state_and_verify()
            logger.exception(
                "backport failed: cherry-pick conflict",
                extra={
                    "branch": branch,
                    "commit_hash": commit_hash,
                    "issue_number": issue_number,
                    "state": cpe_state.name,
                },
            )
            cp.abort_cherry_pick()
        except cherry_picker.GitHubException as ghe:
            await util.comment_on_pr(
                gh,
                issue_number,
                f"""\
                Sorry {util.get_participants(created_by, merged_by)}, I had trouble completing the backport.

                Please retry by removing and re-adding the "needs backport to {branch}" label.
                If that does not work, please backport manually with [cherry_picker](https://pypi.org/project/cherry-picker/), see the [devguide](https://devguide.python.org/getting-started/git-boot-camp/#backporting-merged-changes) for more information.
                ```
                cherry_picker {commit_hash} {branch}
                ```
                """,
            )
            await util.assign_pr_to_core_dev(gh, issue_number, merged_by)
            ghe_state = cp.get_state_and_verify()
            logger.exception(
                "backport failed: github error",
                extra={
                    "branch": branch,
                    "commit_hash": commit_hash,
                    "issue_number": issue_number,
                    "state": ghe_state.name,
                },
            )
            cp.abort_cherry_pick()


@app.task()
def delete_branch_task(branch_name, pr_url, merged, *, installation_id):
    """Delete a branch from the miss-islington/cpython fork."""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        _delete_branch_task_asyncio(
            branch_name, pr_url, merged, installation_id=installation_id
        )
    )


async def _delete_branch_task_asyncio(branch_name, pr_url, merged, *, installation_id):
    """Delete a branch, with delayed deletion for non-merged PRs."""
    if not util.is_cpython_repo():
        if "cpython" in os.listdir("."):
            os.chdir("./cpython")
        else:
            logger.warning(
                "cannot delete branch: cpython repo not found",
                extra={
                    "branch": branch_name,
                    "pwd": os.getcwd(),
                    "listdir": os.listdir("."),
                },
            )
            return

    if merged:
        _git_delete_branch(branch_name)
    else:
        await asyncio.sleep(60)
        async with aiohttp.ClientSession() as session:
            gh = gh_aiohttp.GitHubAPI(session, "python/cpython", cache=cache)
            installation_access_token = await apps.get_installation_access_token(
                gh,
                installation_id=installation_id,
                app_id=os.environ.get("GH_APP_ID"),
                private_key=os.environ.get("GH_PRIVATE_KEY")
            )
            gh.oauth_token = installation_access_token["token"]
            updated_data = await gh.getitem(pr_url)
            if updated_data["state"] == "closed":
                _git_delete_branch(branch_name)


def _git_delete_branch(branch_name):
    """Delete a branch from the origin remote using git."""
    try:
        subprocess.check_output(
            ["git", "push", "origin", "--delete", branch_name],
            stderr=subprocess.STDOUT
        )
        logger.info("deleted branch", extra={"branch": branch_name})
    except subprocess.CalledProcessError as e:
        logger.exception(
            "failed to delete branch",
            extra={"branch": branch_name, "output": e.output.decode()},
        )
        raise


class InitRepoStep(bootsteps.StartStopStep):
    def start(self, c):
        logger.info("initializing the repository")
        setup_cpython_repo()


app.steps["worker"].add(InitRepoStep)
