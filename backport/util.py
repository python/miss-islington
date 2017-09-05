import requests
import os

from gidgethub import sansio


def comment_on_pr(issue_number, message):
    """
    Leave a comment on a PR/Issue
    """
    request_headers = sansio.create_headers(
        "miss-islington",
        oauth_token=os.getenv('GH_AUTH'))
    issue_comment_url = f"https://api.github.com/repos/python/cpython/issues/{issue_number}/comments"
    data = {
        "body": message,
    }
    response = requests.post(issue_comment_url,
                             headers=request_headers,
                             json=data)
    if response.status_code == requests.codes.created:
        print(f"Commented at {response.json()['url']}")
    else:
        print(response.status_code)
        print(response.text)


def user_login(item):
    return item["user"]["login"]