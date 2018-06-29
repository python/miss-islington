import re

from gidgethub import routing

from . import util

router = routing.Router()

TITLE_RE = re.compile(r"\[(?P<branch>\d+\.\d+)\].+?(?P<pr>\d+)\)")


@router.register("status")
async def check_status(event, gh, *args, **kwargs):
    """
    Check the state change
    """
    if (
        event.data["commit"].get("committer")
        and event.data["commit"]["committer"]["login"] == "miss-islington"
    ):
        sha = event.data["sha"]
        await check_ci_status_and_approval(gh, sha, leave_comment=True)


@router.register("pull_request", action="labeled")
async def pr_reviewed(event, gh, *args, **kwargs):
    if event.data["pull_request"]["user"]["login"] == "miss-islington":
        if util.pr_is_awaiting_merge(event.data["pull_request"]["labels"]):
            sha = event.data["pull_request"]["head"]["sha"]
            await check_ci_status_and_approval(gh, sha)


async def check_ci_status_and_approval(gh, sha, leave_comment=False):

    result = await gh.getitem(f"/repos/python/cpython/commits/{sha}/status")
    all_ci_status = [status["state"] for status in result["statuses"]]
    all_ci_context = [status["context"] for status in result["statuses"]]

    if (
        "pending" not in all_ci_status
        and "continuous-integration/travis-ci/pr" in all_ci_context
    ):
        async for ref in gh.getiter("/repos/miss-islington/cpython/git/refs/heads/"):
            if "backport-" in ref["ref"] and ref["object"]["sha"] == sha:
                backport_branch_name = ref["ref"].split("/")[-1]
                async for pr_response in gh.getiter(
                    f"/repos/python/cpython/pulls?state=open&head=miss-islington:{backport_branch_name}"
                ):
                    pr_number = pr_response["number"]
                    normalized_pr_title = util.normalize_title(
                        pr_response["title"], pr_response["body"]
                    )

                    title_match = TITLE_RE.match(normalized_pr_title)
                    if title_match:

                        if leave_comment:
                            original_pr_number = title_match.group("pr")
                            original_pr_url = (
                                f"/repos/python/cpython/pulls/{original_pr_number}"
                            )
                            original_pr_result = await gh.getitem(original_pr_url)
                            pr_author = original_pr_result["user"]["login"]
                            committer = original_pr_result["merged_by"]["login"]

                            participants = util.get_participants(pr_author, committer)
                            emoji = "✅" if result["state"] == "success" else "❌"

                            await util.leave_comment(
                                gh,
                                pr_number=pr_number,
                                message=f"{participants}: Backport status check is done, and it's a {result['state']} {emoji} .",
                            )

                        if result["state"] == "success":
                            pr = await gh.getitem(
                                f"/repos/python/cpython/pulls/{pr_number}"
                            )
                            if util.pr_is_awaiting_merge(pr["labels"]):
                                await merge_pr(gh, pr_number, sha)
                                break


async def merge_pr(gh, pr_number, sha):
    async for commit in gh.getiter(f"/repos/python/cpython/pulls/{pr_number}/commits"):
        if commit["sha"] == sha:
            pr_commit_msg = commit["commit"]["message"].split("\n")

            cleaned_up_title = f"{pr_commit_msg[0]}"
            await gh.put(
                f"/repos/python/cpython/pulls/{pr_number}/merge",
                data={
                    "commit_title": cleaned_up_title,
                    "commit_message": "\n".join(pr_commit_msg[1:]),
                    "sha": sha,
                    "merge_method": "squash",
                },
            )
            break
