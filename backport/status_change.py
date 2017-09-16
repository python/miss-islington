import requests
import os
import re

from gidgethub import sansio, routing

from . import util

router = routing.Router()

TITLE_RE = re.compile(r'\[(?P<branch>\d+\.\d+)\].+?(?P<pr>\d+)\)')



@router.register("status")
async def check_status(event, gh, *args, **kwargs):
    """
    Check the state change
    """
    if event.data["commit"]["committer"]["login"] == "miss-islington":
        sha = event.data["sha"]
        status_url = f"https://api.github.com/repos/python/cpython/commits/{sha}/status"
        request_headers = sansio.create_headers(
            "miss-islington",
            oauth_token=os.getenv('GH_AUTH'))
        response = requests.get(status_url,
                                 headers=request_headers)
        result = response.json()

        if result["state"] != "pending":
            url = "https://api.github.com/repos/miss-islington/cpython/git/refs/heads/"
            response = requests.get(url, headers=request_headers)
            for ref in response.json():
                print("ref obj")
                print(ref)
                if "backport-" in ref["ref"] and ref["object"]["sha"] == sha:
                    backport_branch_name = ref["ref"].split("/")[-1]
                    pr_url = f"https://api.github.com/repos/python/cpython/pulls?state=open&head=miss-islington:{backport_branch_name}"
                    pr_response = requests.get(pr_url, headers=request_headers).json()
                    print("pr respponse")
                    print(pr_response)
                    if pr_response:
                        pr_number = pr_response[0]["number"]
                        normalized_pr_title = util.normalize_title(pr_response[0]["title"],
                                                                   pr_response[0]["body"])

                        title_match = TITLE_RE.match(normalized_pr_title)
                        if title_match:
                            original_pr_number = title_match.group('pr')
                            original_pr_url = f"https://api.github.com/repos/python/cpython/pulls/{original_pr_number}"
                            original_pr_result = requests.get(original_pr_url,
                                                              headers=request_headers).json()
                            pr_author = original_pr_result["user"]["login"]
                            committer = original_pr_result["merged_by"]["login"]

                            participants = util.get_participants(
                                pr_author, committer)
                            util.comment_on_pr(
                                pr_number,
                                message=f"{participants}: Backport status check is done, and the result is {result['state']}.")
