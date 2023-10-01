import asyncio
import os
import subprocess

import aiohttp
import cachetools
import celery
from cherry_picker import cherry_picker
from celery import bootsteps
from gidgethub import aiohttp as gh_aiohttp
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration

from . import util


app = celery.Celery("backport_cpython")

app.conf.update(
    broker_url=os.environ["HEROKU_REDIS_MAROON_URL"],
    result_backend=os.environ["HEROKU_REDIS_MAROON_URL"],
)

cache = cachetools.LRUCache(maxsize=500)
sentry_sdk.init(os.environ.get("SENTRY_DSN"), integrations=[CeleryIntegration()])


CHERRY_PICKER_CONFIG = {
    "team": "python",
    "repo": "cpython",
    "check_sha": "7f777ed95a19224294949e1b4ce56bbffcb1fe9f",
    "fix_commit_msg": True,
    "default_branch": "main",
}


@app.task()
def setup_cpython_repo():
    print("Setting up CPython repository")  # pragma: nocover
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
        print("Finished setting up CPython Repo")
    else:
        print("cpython directory already exists")


@app.task()
def backport_task(commit_hash, branch, *, issue_number, created_by, merged_by):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        backport_task_asyncio(
            commit_hash,
            branch,
            issue_number=issue_number,
            created_by=created_by,
            merged_by=merged_by,
        )
    )


async def backport_task_asyncio(
    commit_hash, branch, *, issue_number, created_by, merged_by
):
    """Backport a commit into a branch."""

    oauth_token = os.environ.get("GH_AUTH")
    async with aiohttp.ClientSession() as session:
        gh = gh_aiohttp.GitHubAPI(
            session, "python/cpython", oauth_token=oauth_token, cache=cache
        )

        if not util.is_cpython_repo():
            # cd to cpython if we're not already in it
            if "cpython" in os.listdir("."):
                os.chdir("./cpython")
            else:
                print(f"pwd: {os.getcwd()}, listdir: {os.listdir('.')}")

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

        cp = cherry_picker.CherryPicker(
            "origin",
            commit_hash,
            [branch],
            config=CHERRY_PICKER_CONFIG,
            prefix_commit=False,
        )
        try:
            cp.backport()
        except cherry_picker.BranchCheckoutException:
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
            cp.abort_cherry_pick()
        except cherry_picker.CherryPickException:
            await util.comment_on_pr(
                gh,
                issue_number,
                f"""\
                Sorry, {util.get_participants(created_by, merged_by)}, I could not cleanly backport this to `{branch}` due to a conflict.
                Please backport using [cherry_picker](https://pypi.org/project/cherry-picker/) on command line.
                ```
                cherry_picker {commit_hash} {branch}
                ```
                """,
            )
            await util.assign_pr_to_core_dev(gh, issue_number, merged_by)
            cp.abort_cherry_pick()


class InitRepoStep(bootsteps.StartStopStep):
    def start(self, c):
        print("Initialize the repository.")
        setup_cpython_repo()


app.steps["worker"].add(InitRepoStep)
