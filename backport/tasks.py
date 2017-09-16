import celery
import os
import subprocess

from cherry_picker import cherry_picker

from . import util

app = celery.Celery('backport_cpython')

app.conf.update(BROKER_URL=os.environ['REDIS_URL'],
                CELERY_RESULT_BACKEND=os.environ['REDIS_URL'])



@app.task
def setup_cpython_repo():
    subprocess.check_output(
        f"git clone https://{os.environ.get('GH_AUTH')}:x-oauth-basic@github.com/miss-islington/cpython.git".split())
    subprocess.check_output("git config --global user.email 'mariatta.wijaya+miss-islington@gmail.com'".split())
    subprocess.check_output(["git", "config", "--global", "user.name", "'Miss Islington (bot)'"])
    os.chdir('./cpython')
    subprocess.check_output(
        f"git remote add upstream https://{os.environ.get('GH_AUTH')}:x-oauth-basic@github.com/python/cpython.git".split())
    print("Finished setting up CPython Repo")


@app.task
def backport_task(commit_hash, branch, *, issue_number, created_by, merged_by):
    """Backport a commit into a branch."""
    if not util.is_cpython_repo():
        # cd to cpython if we're not already in it
        if "cpython" in os.listdir('.'):
            os.chdir('./cpython')
        else:
            print(f"pwd: {os.pwd()}, listdir: {os.listdir('.')}")
            util.comment_on_pr(issue_number,
                               f"""{util.get_participants(created_by, merged_by)}, Something is wrong... I can't backport for now.
                               Please backport using [cherry_picker](https://pypi.org/project/cherry-picker/) on command line.""")
    cp = cherry_picker.CherryPicker('origin', commit_hash, [branch])
    try:
        cp.backport()
    except cherry_picker.BranchCheckoutException:
        util.comment_on_pr(issue_number,
                            f"""Sorry {util.get_participants(created_by, merged_by)}, I had trouble checking out the `{branch}` backport branch.
                            Please backport using [cherry_picker](https://pypi.org/project/cherry-picker/) on command line.""")
        cp.abort_cherry_pick()
    except cherry_picker.CherryPickException:
        util.comment_on_pr(issue_number,
                            f"""Sorry, {util.get_participants(created_by, merged_by)}, I could not cleanly backport this to `{branch}` due to a conflict. 
                            Please backport using [cherry_picker](https://pypi.org/project/cherry-picker/) on command line.""")
        cp.abort_cherry_pick()
