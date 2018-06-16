import http
import gidgethub

from gidgethub import sansio

from miss_islington import status_change


class FakeGH:
    def __init__(self, *, getitem=None, getiter=None, put=None):
        self._getitem_return = getitem
        self._getiter_return = getiter
        self.getitem_url = None
        self.getiter_url = None
        self._put_return = put
        self._post_return = put

    async def getitem(self, url):
        self.getitem_url = url
        to_return = self._getitem_return[self.getitem_url]
        if isinstance(to_return, Exception):
            raise to_return
        else:
            return to_return

    async def getiter(self, url):
        self.getiter_url = url
        to_iterate = self._getiter_return[url]
        for item in to_iterate:
            yield item

    async def put(self, url, *, data):
        self.put_url = url
        self.put_data = data
        return self._put_return

    async def post(self, url, *, data):
        self.post_url = url
        self.post_data = data
        return self._post_return


async def test_ci_passed_with_one_core_dev_review_pr_is_merged():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {"sha": sha, "commit": {"committer": {"login": "miss-islington"}}}
    event = sansio.Event(data, event="status", delivery_id="1")

    getitem = {
        f"/repos/python/cpython/commits/{sha}/status": {
            "state": "success",
            "statuses": [
                {
                    "state": "success",
                    "description": "Issue report skipped",
                    "context": "bedevere/issue-number",
                },
                {
                    "state": "success",
                    "description": "The Travis CI build passed",
                    "target_url": "https://travis-ci.org/python/cpython/builds/340259685?utm_source=github_status&utm_medium=notification",
                    "context": "continuous-integration/travis-ci/pr",
                },
            ],
        },
        "/repos/python/cpython/pulls/5544": {
            "user": {"login": "miss-islington"},
            "merged_by": {"login": "Mariatta"},
        },
        "/teams/42/memberships/Mariatta": True,
    }

    getiter = {
        "/repos/miss-islington/cpython/git/refs/heads/": [
            {"ref": f"refs/heads/backport-{sha[0:7]}-3.6", "object": {"sha": sha}},
            {
                "ref": "refs/heads/backport-63ae044-3.6",
                "object": {
                    "sha": "67a2b0b7713e40dea7762b7d7764ae18fe967561",
                    "type": "commit",
                    "url": "https://api.github.com/repos/miss-islington/cpython/git/commits/67a2b0b7713e40dea7762b7d7764ae18fe967561",
                },
            },
        ],
        f"/repos/python/cpython/pulls?state=open&head=miss-islington:backport-{sha[0:7]}-3.6": [
            {
                "number": 5547,
                "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
            }
        ],
        "/repos/python/cpython/pulls/5547/reviews": [
            {"user": {"login": "Mariatta"}, "state": "APPROVED"}
        ],
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ],
        "/orgs/python/teams": [{"name": "Python core", "id": 42}],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert len(gh.post_data["body"]) is not None  # leaves a comment
    assert gh.put_data["sha"] == sha  # is merged
    assert gh.put_data["merge_method"] == "squash"
    assert (
        gh.put_data["commit_title"]
        == "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)"
    )


async def test_ci_passed_with_no_core_dev_review_pr_is_not_merged():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {"sha": sha, "commit": {"committer": {"login": "miss-islington"}}}
    event = sansio.Event(data, event="status", delivery_id="1")

    getitem = {
        f"/repos/python/cpython/commits/{sha}/status": {
            "state": "success",
            "statuses": [
                {
                    "state": "success",
                    "description": "Issue report skipped",
                    "context": "bedevere/issue-number",
                },
                {
                    "state": "success",
                    "description": "The Travis CI build passed",
                    "target_url": "https://travis-ci.org/python/cpython/builds/340259685?utm_source=github_status&utm_medium=notification",
                    "context": "continuous-integration/travis-ci/pr",
                },
            ],
        },
        "/repos/python/cpython/pulls/5544": {
            "user": {"login": "miss-islington"},
            "merged_by": {"login": "Mariatta"},
        },
        "/teams/42/memberships/Mariatta": True,
    }

    getiter = {
        "/repos/miss-islington/cpython/git/refs/heads/": [
            {"ref": f"refs/heads/backport-{sha[0:7]}-3.6", "object": {"sha": sha}},
            {
                "ref": "refs/heads/backport-63ae044-3.6",
                "object": {
                    "sha": "67a2b0b7713e40dea7762b7d7764ae18fe967561",
                    "type": "commit",
                    "url": "https://api.github.com/repos/miss-islington/cpython/git/commits/67a2b0b7713e40dea7762b7d7764ae18fe967561",
                },
            },
        ],
        f"/repos/python/cpython/pulls?state=open&head=miss-islington:backport-{sha[0:7]}-3.6": [
            {
                "number": 5547,
                "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
            }
        ],
        "/repos/python/cpython/pulls/5547/reviews": [],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert len(gh.post_data["body"]) is not None  # leaves a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_ci_not_passed_with_core_dev_review_pr_is_not_merged():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {"sha": sha, "commit": {"committer": {"login": "miss-islington"}}}
    event = sansio.Event(data, event="status", delivery_id="1")

    getitem = {
        f"/repos/python/cpython/commits/{sha}/status": {
            "state": "failure",
            "statuses": [
                {
                    "state": "success",
                    "description": "Issue report skipped",
                    "context": "bedevere/issue-number",
                },
                {
                    "state": "failure",
                    "description": "The Travis CI build failed",
                    "target_url": "https://travis-ci.org/python/cpython/builds/340259685?utm_source=github_status&utm_medium=notification",
                    "context": "continuous-integration/travis-ci/pr",
                },
            ],
        },
        "/repos/python/cpython/pulls/5544": {
            "user": {"login": "miss-islington"},
            "merged_by": {"login": "Mariatta"},
        },
        "/teams/42/memberships/Mariatta": True,
    }

    getiter = {
        "/repos/miss-islington/cpython/git/refs/heads/": [
            {"ref": f"refs/heads/backport-{sha[0:7]}-3.6", "object": {"sha": sha}},
            {
                "ref": "refs/heads/backport-63ae044-3.6",
                "object": {
                    "sha": "67a2b0b7713e40dea7762b7d7764ae18fe967561",
                    "type": "commit",
                    "url": "https://api.github.com/repos/miss-islington/cpython/git/commits/67a2b0b7713e40dea7762b7d7764ae18fe967561",
                },
            },
        ],
        f"/repos/python/cpython/pulls?state=open&head=miss-islington:backport-{sha[0:7]}-3.6": [
            {
                "number": 5547,
                "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
            }
        ],
        "/orgs/python/teams": [{"name": "Python core", "id": 42}],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert len(gh.post_data["body"]) is not None  # leaves a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_pr_reviewed_webhook_ci_passed_pr_is_merged():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "submitted",
        "pull_request": {"user": {"login": "miss-islington"}},
        "review": {
            "commit_id": sha,
            "user": {"login": "Mariatta"},
            "state": "approved",
        },
    }

    event = sansio.Event(data, event="pull_request_review", delivery_id="1")

    getitem = {
        f"/repos/python/cpython/commits/{sha}/status": {
            "state": "success",
            "statuses": [
                {
                    "state": "success",
                    "description": "Issue report skipped",
                    "context": "bedevere/issue-number",
                },
                {
                    "state": "success",
                    "description": "The Travis CI build passed",
                    "target_url": "https://travis-ci.org/python/cpython/builds/340259685?utm_source=github_status&utm_medium=notification",
                    "context": "continuous-integration/travis-ci/pr",
                },
            ],
        },
        "/teams/42/memberships/Mariatta": True,
    }

    getiter = {
        "/repos/miss-islington/cpython/git/refs/heads/": [
            {"ref": f"refs/heads/backport-{sha[0:7]}-3.6", "object": {"sha": sha}},
            {
                "ref": f"refs/heads/backport-{sha[0:7]}-3.6",
                "object": {
                    "sha": sha,
                    "type": "commit",
                    "url": f"https://api.github.com/repos/miss-islington/cpython/git/commits/{sha}",
                },
            },
        ],
        f"/repos/python/cpython/pulls?state=open&head=miss-islington:backport-{sha[0:7]}-3.6": [
            {
                "number": 5547,
                "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
            }
        ],
        "/orgs/python/teams": [{"name": "Python core", "id": 42}],
        "/repos/python/cpython/pulls/5547/reviews": [
            {"user": {"login": "Mariatta"}, "state": "APPROVED"}
        ],
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert gh.put_data["sha"] == sha  # is merged
    assert gh.put_data["merge_method"] == "squash"
    assert (
        gh.put_data["commit_title"]
        == "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)"
    )


async def test_pr_reviewed_webhook_ci_failure_pr_is_not_merged():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "submitted",
        "pull_request": {"user": {"login": "miss-islington"}},
        "review": {
            "commit_id": sha,
            "user": {"login": "Mariatta"},
            "state": "approved",
        },
    }

    event = sansio.Event(data, event="pull_request_review", delivery_id="1")

    getitem = {
        f"/repos/python/cpython/commits/{sha}/status": {
            "state": "failure",
            "statuses": [
                {
                    "state": "success",
                    "description": "Issue report skipped",
                    "context": "bedevere/issue-number",
                },
                {
                    "state": "failure",
                    "description": "The Travis CI build failed",
                    "target_url": "https://travis-ci.org/python/cpython/builds/340259685?utm_source=github_status&utm_medium=notification",
                    "context": "continuous-integration/travis-ci/pr",
                },
            ],
        },
        "/teams/42/memberships/Mariatta": True,
    }

    getiter = {
        "/repos/miss-islington/cpython/git/refs/heads/": [
            {"ref": f"refs/heads/backport-{sha[0:7]}-3.6", "object": {"sha": sha}},
            {
                "ref": "refs/heads/backport-63ae044-3.6",
                "object": {
                    "sha": "67a2b0b7713e40dea7762b7d7764ae18fe967561",
                    "type": "commit",
                    "url": "https://api.github.com/repos/miss-islington/cpython/git/commits/67a2b0b7713e40dea7762b7d7764ae18fe967561",
                },
            },
        ],
        f"/repos/python/cpython/pulls?state=open&head=miss-islington:backport-{sha[0:7]}-3.6": [
            {
                "number": 5547,
                "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
            }
        ],
        "/orgs/python/teams": [{"name": "Python core", "id": 42}],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_pr_reviewed_changes_requested_pr_is_not_merged():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "submitted",
        "pull_request": {"user": {"login": "miss-islington"}},
        "review": {
            "commit_id": sha,
            "user": {"login": "Mariatta"},
            "state": "changes_requested",
        },
    }

    event = sansio.Event(data, event="pull_request_review", delivery_id="1")

    getitem = {
        f"/repos/python/cpython/commits/{sha}/status": {
            "state": "failure",
            "statuses": [
                {
                    "state": "success",
                    "description": "Issue report skipped",
                    "context": "bedevere/issue-number",
                },
                {
                    "state": "failure",
                    "description": "The Travis CI build failed",
                    "target_url": "https://travis-ci.org/python/cpython/builds/340259685?utm_source=github_status&utm_medium=notification",
                    "context": "continuous-integration/travis-ci/pr",
                },
            ],
        }
    }

    getiter = {"/orgs/python/teams": [{"name": "Python core", "id": 42}]}

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_pr_reviewed_ignore_non_miss_islingtons_pr():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "submitted",
        "pull_request": {"user": {"login": "Mariatta"}},
        "review": {
            "commit_id": sha,
            "user": {"login": "Mariatta"},
            "state": "approved",
        },
    }

    event = sansio.Event(data, event="pull_request_review", delivery_id="1")

    getitem = {
        f"/repos/python/cpython/commits/{sha}/status": {
            "state": "success",
            "statuses": [
                {
                    "state": "success",
                    "description": "Issue report skipped",
                    "context": "bedevere/issue-number",
                },
                {
                    "state": "success",
                    "description": "The Travis CI build failed",
                    "target_url": "https://travis-ci.org/python/cpython/builds/340259685?utm_source=github_status&utm_medium=notification",
                    "context": "continuous-integration/travis-ci/pr",
                },
            ],
        }
    }

    getiter = {"/orgs/python/teams": [{"name": "Python core", "id": 42}]}

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_ci_passed_with_one_core_dev_review_pr_is_merged_not_miss_islington():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {"sha": sha, "commit": {"committer": {"login": "Mariatta"}}}
    event = sansio.Event(data, event="status", delivery_id="1")

    getitem = {
        f"/repos/python/cpython/commits/{sha}/status": {
            "state": "success",
            "statuses": [
                {
                    "state": "success",
                    "description": "Issue report skipped",
                    "context": "bedevere/issue-number",
                },
                {
                    "state": "success",
                    "description": "The Travis CI build passed",
                    "target_url": "https://travis-ci.org/python/cpython/builds/340259685?utm_source=github_status&utm_medium=notification",
                    "context": "continuous-integration/travis-ci/pr",
                },
            ],
        },
        "/repos/python/cpython/pulls/5544": {
            "user": {"login": "miss-islington"},
            "merged_by": {"login": "Mariatta"},
        },
        "/teams/42/memberships/Mariatta": True,
    }

    getiter = {
        "/repos/miss-islington/cpython/git/refs/heads/": [
            {"ref": f"refs/heads/backport-{sha[0:7]}-3.6", "object": {"sha": sha}},
            {
                "ref": "refs/heads/backport-63ae044-3.6",
                "object": {
                    "sha": "67a2b0b7713e40dea7762b7d7764ae18fe967561",
                    "type": "commit",
                    "url": "https://api.github.com/repos/miss-islington/cpython/git/commits/67a2b0b7713e40dea7762b7d7764ae18fe967561",
                },
            },
        ],
        f"/repos/python/cpython/pulls?state=open&head=miss-islington:backport-{sha[0:7]}-3.6": [
            {
                "number": 5547,
                "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
            }
        ],
        "/repos/python/cpython/pulls/5547/reviews": [
            {"user": {"login": "Mariatta"}, "state": "APPROVED"}
        ],
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ],
        "/orgs/python/teams": [{"name": "Python core", "id": 42}],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_ci_pending():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {"sha": sha, "commit": {"committer": {"login": "miss-islington"}}}
    event = sansio.Event(data, event="status", delivery_id="1")

    getitem = {
        f"/repos/python/cpython/commits/{sha}/status": {
            "state": "pending",
            "statuses": [
                {
                    "state": "pending",
                    "description": "Issue report skipped",
                    "context": "bedevere/issue-number",
                },
                {
                    "state": "success",
                    "description": "The Travis CI build passed",
                    "target_url": "https://travis-ci.org/python/cpython/builds/340259685?utm_source=github_status&utm_medium=notification",
                    "context": "continuous-integration/travis-ci/pr",
                },
            ],
        },
        "/repos/python/cpython/pulls/5544": {
            "user": {"login": "miss-islington"},
            "merged_by": {"login": "Mariatta"},
        },
        "/teams/42/memberships/Mariatta": True,
    }

    getiter = {
        "/repos/miss-islington/cpython/git/refs/heads/": [
            {"ref": f"refs/heads/backport-{sha[0:7]}-3.6", "object": {"sha": sha}},
            {
                "ref": "refs/heads/backport-63ae044-3.6",
                "object": {
                    "sha": "67a2b0b7713e40dea7762b7d7764ae18fe967561",
                    "type": "commit",
                    "url": "https://api.github.com/repos/miss-islington/cpython/git/commits/67a2b0b7713e40dea7762b7d7764ae18fe967561",
                },
            },
        ],
        f"/repos/python/cpython/pulls?state=open&head=miss-islington:backport-{sha[0:7]}-3.6": [
            {
                "number": 5547,
                "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
            }
        ],
        "/repos/python/cpython/pulls/5547/reviews": [
            {"user": {"login": "Mariatta"}, "state": "APPROVED"}
        ],
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ],
        "/orgs/python/teams": [{"name": "Python core", "id": 42}],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_travis_not_done():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {"sha": sha, "commit": {"committer": {"login": "miss-islington"}}}
    event = sansio.Event(data, event="status", delivery_id="1")

    getitem = {
        f"/repos/python/cpython/commits/{sha}/status": {
            "state": "success",
            "statuses": [
                {
                    "state": "success",
                    "description": "Issue report skipped",
                    "context": "bedevere/issue-number",
                }
            ],
        },
        "/repos/python/cpython/pulls/5544": {
            "user": {"login": "miss-islington"},
            "merged_by": {"login": "Mariatta"},
        },
        "/teams/42/memberships/Mariatta": True,
    }

    getiter = {
        "/repos/miss-islington/cpython/git/refs/heads/": [
            {"ref": f"refs/heads/backport-{sha[0:7]}-3.6", "object": {"sha": sha}},
            {
                "ref": "refs/heads/backport-63ae044-3.6",
                "object": {
                    "sha": "67a2b0b7713e40dea7762b7d7764ae18fe967561",
                    "type": "commit",
                    "url": "https://api.github.com/repos/miss-islington/cpython/git/commits/67a2b0b7713e40dea7762b7d7764ae18fe967561",
                },
            },
        ],
        f"/repos/python/cpython/pulls?state=open&head=miss-islington:backport-{sha[0:7]}-3.6": [
            {
                "number": 5547,
                "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
            }
        ],
        "/repos/python/cpython/pulls/5547/reviews": [
            {"user": {"login": "Mariatta"}, "state": "APPROVED"}
        ],
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ],
        "/orgs/python/teams": [{"name": "Python core", "id": 42}],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_pr_title_does_not_match():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {"sha": sha, "commit": {"committer": {"login": "miss-islington"}}}
    event = sansio.Event(data, event="status", delivery_id="1")

    getitem = {
        f"/repos/python/cpython/commits/{sha}/status": {
            "state": "success",
            "statuses": [
                {
                    "state": "success",
                    "description": "Issue report skipped",
                    "context": "bedevere/issue-number",
                },
                {
                    "state": "success",
                    "description": "The Travis CI build passed",
                    "target_url": "https://travis-ci.org/python/cpython/builds/340259685?utm_source=github_status&utm_medium=notification",
                    "context": "continuous-integration/travis-ci/pr",
                },
            ],
        },
        "/repos/python/cpython/pulls/5544": {
            "user": {"login": "miss-islington"},
            "merged_by": {"login": "Mariatta"},
        },
        "/teams/42/memberships/Mariatta": True,
    }

    getiter = {
        "/repos/miss-islington/cpython/git/refs/heads/": [
            {"ref": f"refs/heads/backport-{sha[0:7]}-3.6", "object": {"sha": sha}},
            {
                "ref": "refs/heads/backport-63ae044-3.6",
                "object": {
                    "sha": "67a2b0b7713e40dea7762b7d7764ae18fe967561",
                    "type": "commit",
                    "url": "https://api.github.com/repos/miss-islington/cpython/git/commits/67a2b0b7713e40dea7762b7d7764ae18fe967561",
                },
            },
        ],
        f"/repos/python/cpython/pulls?state=open&head=miss-islington:backport-{sha[0:7]}-3.6": [
            {
                "number": 5547,
                "title": "bpo-32720: Fixed the replacement field grammar documentation.",
                "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
            }
        ],
        "/repos/python/cpython/pulls/5547/reviews": [
            {"user": {"login": "Mariatta"}, "state": "APPROVED"}
        ],
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ],
        "/orgs/python/teams": [{"name": "Python core", "id": 42}],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_ci_passed_approved_by_non_core_dev_review_pr_is_not_merged():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {"sha": sha, "commit": {"committer": {"login": "miss-islington"}}}
    event = sansio.Event(data, event="status", delivery_id="1")

    getitem = {
        f"/repos/python/cpython/commits/{sha}/status": {
            "state": "success",
            "statuses": [
                {
                    "state": "success",
                    "description": "Issue report skipped",
                    "context": "bedevere/issue-number",
                },
                {
                    "state": "success",
                    "description": "The Travis CI build passed",
                    "target_url": "https://travis-ci.org/python/cpython/builds/340259685?utm_source=github_status&utm_medium=notification",
                    "context": "continuous-integration/travis-ci/pr",
                },
            ],
        },
        "/repos/python/cpython/pulls/5544": {
            "user": {"login": "miss-islington"},
            "merged_by": {"login": "Mariatta"},
        },
        "/teams/42/memberships/Mariatta": gidgethub.BadRequest(
            status_code=http.HTTPStatus(404)
        ),
    }

    getiter = {
        "/repos/miss-islington/cpython/git/refs/heads/": [
            {"ref": f"refs/heads/backport-{sha[0:7]}-3.6", "object": {"sha": sha}},
            {
                "ref": "refs/heads/backport-63ae044-3.6",
                "object": {
                    "sha": "67a2b0b7713e40dea7762b7d7764ae18fe967561",
                    "type": "commit",
                    "url": "https://api.github.com/repos/miss-islington/cpython/git/commits/67a2b0b7713e40dea7762b7d7764ae18fe967561",
                },
            },
        ],
        f"/repos/python/cpython/pulls?state=open&head=miss-islington:backport-{sha[0:7]}-3.6": [
            {
                "number": 5547,
                "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
            }
        ],
        "/repos/python/cpython/pulls/5547/reviews": [
            {"user": {"login": "Mariatta"}, "state": "APPROVED"}
        ],
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ],
        "/orgs/python/teams": [{"name": "Python core", "id": 42}],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "put_data")  # is not merged


async def test_branch_sha_not_matched_pr_not_merged():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {"sha": sha, "commit": {"committer": {"login": "miss-islington"}}}
    event = sansio.Event(data, event="status", delivery_id="1")

    getitem = {
        f"/repos/python/cpython/commits/{sha}/status": {
            "state": "success",
            "statuses": [
                {
                    "state": "success",
                    "description": "Issue report skipped",
                    "context": "bedevere/issue-number",
                },
                {
                    "state": "success",
                    "description": "The Travis CI build passed",
                    "target_url": "https://travis-ci.org/python/cpython/builds/340259685?utm_source=github_status&utm_medium=notification",
                    "context": "continuous-integration/travis-ci/pr",
                },
            ],
        },
        "/repos/python/cpython/pulls/5544": {
            "user": {"login": "miss-islington"},
            "merged_by": {"login": "Mariatta"},
        },
        "/teams/42/memberships/Mariatta": True,
    }

    getiter = {
        "/repos/miss-islington/cpython/git/refs/heads/": [
            {"ref": f"refs/heads/backport-{sha[0:7]}-3.6", "object": {"sha": sha}},
            {
                "ref": "refs/heads/backport-63ae044-3.6",
                "object": {
                    "sha": "67a2b0b7713e40dea7762b7d7764ae18fe967561",
                    "type": "commit",
                    "url": "https://api.github.com/repos/miss-islington/cpython/git/commits/67a2b0b7713e40dea7762b7d7764ae18fe967561",
                },
            },
        ],
        f"/repos/python/cpython/pulls?state=open&head=miss-islington:backport-{sha[0:7]}-3.6": [
            {
                "number": 5547,
                "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
            }
        ],
        "/repos/python/cpython/pulls/5547/reviews": [
            {"user": {"login": "Mariatta"}, "state": "APPROVED"}
        ],
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ],
        "/orgs/python/teams": [{"name": "Python core", "id": 42}],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "put_data")  # is not merged
