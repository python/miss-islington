import http

import gidgethub
from gidgethub import sansio
from miss_islington import status_change
from miss_islington.util import AUTOMERGE_LABEL


class FakeGH:
    def __init__(
        self,
        *,
        getitem=None,
        getiter=None,
        put=None,
        post=None,
        patch=None,
        delete=None,
    ):
        self._getitem_return = getitem
        self._getiter_return = getiter
        self.getitem_url = None
        self.getiter_url = None
        self._put_return = put
        self._delete_return = put
        self._post_return = post
        self._patch_return = patch
        self.patch_url = self.patch_data = None

    async def getitem(self, url, accept=None):
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

    async def patch(self, url, *, data):
        self.patch_url = url
        self.patch_data = data
        return self._patch_return

    async def delete(self, url, *, data=b"", accept=None):
        self.delete_url = url
        return self._delete_return

    async def put(self, url, *, data):
        self.put_url = url
        self.put_data = data
        to_return = self._put_return
        if isinstance(to_return, Exception):
            raise to_return
        else:
            return to_return

    async def post(self, url, *, data):
        self.post_url = url
        self.post_data = data
        return self._post_return


async def test_ci_passed_with_awaiting_merge_label_pr_is_merged():
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
        "/repos/python/cpython/pulls/5547": {"labels": [{"name": "awaiting merge"}]},
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 1,
            "items": [
                {
                    "number": 5547,
                    "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                    "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
                    "labels": [{"name": "awaiting merge"}],
                }
            ],
        },
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "success",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                }
            ],
            "total_count": 1,
        },
    }

    getiter = {
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ]
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
    assert (
        gh.put_data["commit_message"]
        == "\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
    )


async def test_ci_and_check_run_passed_with_no_awaiting_merge_label_pr_is_not_merged():
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
        "/repos/python/cpython/pulls/5547": {
            "labels": [{"name": "awaiting core review"}]
        },
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 1,
            "items": [
                {
                    "number": 5547,
                    "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                    "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
                    "labels": [{"name": "awaiting core review"}],
                }
            ],
        },
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "success",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                }
            ],
            "total_count": 1,
        },
    }

    gh = FakeGH(getitem=getitem)
    await status_change.router.dispatch(event, gh)
    assert len(gh.post_data["body"]) is not None  # leaves a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_ci_not_passed_awaiting_merge_label_pr_is_not_merged():
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
        "/repos/python/cpython/pulls/5547": {"labels": [{"name": "awaiting merge"}]},
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 1,
            "items": [
                {
                    "number": 5547,
                    "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                    "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
                    "labels": [{"name": "awaiting merge"}],
                }
            ],
        },
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "success",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                }
            ],
            "total_count": 1,
        },
    }

    gh = FakeGH(getitem=getitem)
    await status_change.router.dispatch(event, gh)
    assert len(gh.post_data["body"]) is not None  # leaves a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_ci_passed_and_check_run_failure_awaiting_merge_label_pr_is_not_merged():
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
        "/repos/python/cpython/pulls/5547": {"labels": [{"name": "awaiting merge"}]},
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 1,
            "items": [
                {
                    "number": 5547,
                    "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                    "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
                    "labels": [{"name": "awaiting merge"}],
                }
            ],
        },
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "failure",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                },
                {"conclusion": "success", "name": "Docs", "status": "completed"},
            ],
            "total_count": 1,
        },
    }

    getiter = {
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ]
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert len(gh.post_data["body"]) is not None  # leaves a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_automerge_with_check_run_failure():
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
        "/repos/python/cpython/pulls/5547": {
            "user": {"login": "Mariatta"},
            "merged_by": None,
            "labels": [
                {"name": "awaiting merge"},
                {"name": AUTOMERGE_LABEL},
            ],
        },
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 1,
            "items": [
                {
                    "number": 5547,
                    "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                    "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
                    "labels": [
                        {"name": "awaiting merge"},
                        {"name": AUTOMERGE_LABEL},
                    ],
                }
            ],
        },
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "failure",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                },
                {"conclusion": "success", "name": "Docs", "status": "completed"},
            ],
            "total_count": 1,
        },
    }

    getiter = {
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ]
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert len(gh.post_data["body"]) is not None  # leaves a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_ci_passed_and_check_run_pending_awaiting_merge_label_pr_is_not_merged():
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
        "/repos/python/cpython/pulls/5547": {"labels": [{"name": "awaiting merge"}]},
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 1,
            "items": [
                {
                    "number": 5547,
                    "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                    "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
                    "labels": [{"name": "awaiting merge"}],
                }
            ],
        },
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": None,
                    "name": "Travis CI - Pull Request",
                    "status": "pending",
                },
                {"conclusion": "success", "name": "Docs", "status": "completed"},
            ],
            "total_count": 1,
        },
    }

    getiter = {
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ]
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert len(gh.post_data["body"]) is not None  # leaves a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_ci_passed_and_check_run_timed_out_awaiting_merge_label_pr_is_not_merged():
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
        "/repos/python/cpython/pulls/5547": {"labels": [{"name": "awaiting merge"}]},
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 1,
            "items": [
                {
                    "number": 5547,
                    "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                    "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
                    "labels": [{"name": "awaiting merge"}],
                }
            ],
        },
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "timed_out",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                },
                {"conclusion": "success", "name": "Docs", "status": "completed"},
            ],
            "total_count": 1,
        },
    }

    getiter = {
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ]
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert (
        gh.post_data["body"]
        == "@miss-islington and @Mariatta: Status check is done, and it's a failure or timed out ❌."
    )
    assert not hasattr(gh, "put_data")  # is not merged


async def test_awaiting_merge_label_added_and_ci_passed_pr_is_merged():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "labeled",
        "pull_request": {
            "user": {"login": "miss-islington"},
            "labels": [{"name": "awaiting merge"}],
            "head": {"sha": sha},
            "number": 5547,
            "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
            "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
        },
        "sender": {"login": "Mariatta"},
        "label": {"name": "awaiting merge"},
    }

    event = sansio.Event(data, event="pull_request", delivery_id="1")

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
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [],
            "total_count": 0,
        },
    }

    getiter = {
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ]
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
    assert (
        gh.put_data["commit_message"]
        == "\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
    )


async def test_awaiting_merge_webhook_ci_failure_pr_is_not_merged():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "labeled",
        "pull_request": {
            "user": {"login": "miss-islington"},
            "labels": [{"name": "awaiting merge"}],
            "head": {"sha": sha},
            "number": 5547,
            "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
            "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
        },
        "sender": {"login": "Mariatta"},
        "label": {"name": "awaiting merge"},
    }

    event = sansio.Event(data, event="pull_request", delivery_id="1")

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
        "/repos/python/cpython/pulls/5547": {"labels": [{"name": "awaiting merge"}]},
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 1,
            "items": [
                {
                    "number": 5547,
                    "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                    "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
                    "labels": [{"name": "awaiting merge"}],
                }
            ],
        },
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "failure",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                }
            ],
            "total_count": 1,
        },
    }

    gh = FakeGH(getitem=getitem)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_awaiting_core_review_label_added_is_not_merged():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "labeled",
        "pull_request": {
            "user": {"login": "miss-islington"},
            "labels": [{"name": "awaiting core review"}],
            "head": {"sha": sha},
        },
        "sender": {"login": "bedevere-bot"},
        "label": {"name": "awaiting core review"},
    }

    event = sansio.Event(data, event="pull_request", delivery_id="1")

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
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 1,
            "items": [
                {
                    "number": 5547,
                    "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                    "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
                    "labels": [{"name": "awaiting core review"}],
                }
            ],
        },
    }

    gh = FakeGH(getitem=getitem)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_awaiting_merge_label_ignore_non_miss_islingtons_pr():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "labeled",
        "pull_request": {
            "user": {"login": "Mariatta"},
            "labels": [{"name": "awaiting merge"}],
            "head": {"sha": sha},
            "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.",
            "url": "https://api.github.com/repos/python/cpython/pulls/5547",
        },
        "sender": {"login": "Mariatta"},
        "label": {"name": AUTOMERGE_LABEL},
    }

    event = sansio.Event(data, event="pull_request", delivery_id="1")

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
        },
        "/teams/42/memberships/Mariatta": True,
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "success",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                }
            ],
            "total_count": 1,
        },
    }

    getiter = {"/orgs/python/teams": [{"name": "python core", "id": 42}]}

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_ci_passed_with_awaiting_merge_label_not_miss_islington_is_not_merged():
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
        "/repos/python/cpython/pulls/5547": {"labels": [{"name": "awaiting merge"}]},
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 1,
            "items": [
                {
                    "number": 5547,
                    "title": "bpo-32720: Fixed the replacement field grammar documentation.",
                    "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
                    "labels": [{"name": "awaiting merge"}],
                }
            ],
        },
    }

    gh = FakeGH(getitem=getitem)
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
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "success",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                }
            ],
            "total_count": 1,
        },
    }

    getiter = {
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ]
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
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 1,
            "items": [
                {
                    "number": 5547,
                    "title": "bpo-32720: Fixed the replacement field grammar documentation.",
                    "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
                    "labels": [{"name": "awaiting merge"}],
                }
            ],
        },
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "success",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                }
            ],
            "total_count": 1,
        },
    }

    getiter = {
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ]
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_ci_passed_awaiting_core_review_is_not_merged():
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
        "/repos/python/cpython/pulls/5547": {
            "labels": [{"name": "awaiting core review"}]
        },
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 1,
            "items": [
                {
                    "number": 5547,
                    "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                    "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
                    "labels": [{"name": "awaiting core review"}],
                }
            ],
        },
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "success",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                }
            ],
            "total_count": 1,
        },
    }

    gh = FakeGH(getitem=getitem)
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
        "/repos/python/cpython/pulls/5547": {"labels": [{"name": "awaiting merge"}]},
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 1,
            "items": [
                {
                    "number": 5547,
                    "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                    "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
                    "labels": [{"name": "awaiting merge"}],
                }
            ],
        },
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "success",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                }
            ],
            "total_count": 1,
        },
    }

    getiter = {
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ]
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "put_data")  # is not merged


async def test_awaiting_merge_label_added_not_miss_islingtons_pr():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "labeled",
        "pull_request": {
            "user": {"login": "Mariatta"},
            "labels": [{"name": "awaiting merge"}],
            "head": {"sha": sha},
            "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.",
            "url": "https://api.github.com/repos/python/cpython/pulls/5547",
        },
        "sender": {"login": "Mariatta"},
        "label": {"name": AUTOMERGE_LABEL},
    }

    event = sansio.Event(data, event="pull_request", delivery_id="1")

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
        "/repos/python/cpython/pulls/5547": {"labels": [{"name": "awaiting merge"}]},
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
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ],
        "/orgs/python/teams": [{"name": "python core", "id": 42}],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "put_data")  # is not merged


async def test_awaiting_core_review_label_added_miss_islingtons_pr():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "labeled",
        "pull_request": {
            "user": {"login": "miss-islington"},
            "labels": [{"name": "awaiting core review"}],
            "head": {"sha": sha},
            "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.",
            "url": "https://api.github.com/repos/python/cpython/pulls/5547",
        },
        "sender": {"login": "Mariatta"},
        "label": {"name": AUTOMERGE_LABEL},
    }

    event = sansio.Event(data, event="pull_request", delivery_id="1")

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
        "/repos/python/cpython/pulls/5547": {
            "labels": [{"name": "awaiting core review"}]
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
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>"
                },
            }
        ],
        "/orgs/python/teams": [{"name": "python core", "id": 42}],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "put_data")  # is not merged


async def test_no_pr_containing_sha():
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
        "/repos/python/cpython/pulls/5547": {"labels": [{"name": "awaiting merge"}]},
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 0,
            "items": [],
        },
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "success",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                }
            ],
            "total_count": 1,
        },
    }

    gh = FakeGH(getitem=getitem)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave any comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_ci_passed_automerge():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {"sha": sha, "commit": {"committer": None, "author": None}}
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
        "/repos/python/cpython/pulls/5547": {
            "user": {"login": "bedevere-bot"},
            "merged_by": None,
            "labels": [
                {"name": "awaiting merge"},
                {"name": AUTOMERGE_LABEL},
            ],
        },
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 1,
            "items": [
                {
                    "number": 5547,
                    "title": "bpo-32720: Fixed the replacement field grammar documentation.",
                    "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
                    "labels": [
                        {"name": "awaiting merge"},
                        {"name": AUTOMERGE_LABEL},
                    ],
                }
            ],
        },
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "success",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                }
            ],
            "total_count": 1,
        },
    }

    getiter = {
        "/repos/python/cpython/pulls/5547/commits": [
            {
                "sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
                "commit": {
                    "message": "bpo-32720: Fixed the replacement field grammar documentation."
                },
            }
        ]
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert len(gh.post_data["body"]) is not None  # leaves a comment
    assert gh.put_data["sha"] == sha  # is merged
    assert gh.put_data["merge_method"] == "squash"
    assert (
        gh.put_data["commit_title"]
        == "bpo-32720: Fixed the replacement field grammar documentation. (GH-5547)"
    )


async def test_ci_passed_not_automerge():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {"sha": sha, "commit": {"committer": None, "author": None}}
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
        "/repos/python/cpython/pulls/5547": {
            "user": {"login": "bedevere-bot"},
            "merged_by": None,
            "labels": [{"name": "awaiting merge"}],
        },
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 1,
            "items": [
                {
                    "number": 5547,
                    "title": "bpo-32720: Fixed the replacement field grammar documentation.",
                    "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.",
                    "labels": [{"name": "awaiting merge"}],
                }
            ],
        },
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "success",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                }
            ],
            "total_count": 1,
        },
    }

    gh = FakeGH(getitem=getitem)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_awaiting_merge_label_and_automerge_label_added_not_miss_islingtons_pr():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "labeled",
        "pull_request": {
            "user": {"login": "Mariatta"},
            "labels": [
                {"name": "awaiting merge"},
                {"name": AUTOMERGE_LABEL},
            ],
            "head": {"sha": sha},
            "number": 5547,
            "title": "bpo-32720: Fixed the replacement field grammar documentation.",
            "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.",
            "url": "https://api.github.com/repos/python/cpython/pulls/5547",
        },
        "sender": {"login": "Mariatta"},
        "label": {"name": AUTOMERGE_LABEL},
    }

    event = sansio.Event(data, event="pull_request", delivery_id="1")

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
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "success",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                }
            ],
            "total_count": 1,
        },
    }

    getiter = {
        "/repos/python/cpython/pulls/5547/commits": [{"sha": sha}],
        "/orgs/python/teams": [{"name": "python core", "id": 42}],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment

    assert gh.put_data["sha"] == sha  # is merged
    assert gh.put_data["merge_method"] == "squash"
    assert (
        gh.put_data["commit_title"]
        == "bpo-32720: Fixed the replacement field grammar documentation. (GH-5547)"
    )
    assert (
        gh.put_data["commit_message"]
        == "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`."
    )


async def test_automerge_but_not_awaiting_merge():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "labeled",
        "pull_request": {
            "user": {"login": "Mariatta"},
            "labels": [{"name": "awaiting review"}, {"name": AUTOMERGE_LABEL}],
            "head": {"sha": sha},
            "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.",
            "url": "https://api.github.com/repos/python/cpython/pulls/5547",
        },
        "sender": {"login": "Mariatta"},
        "label": {"name": AUTOMERGE_LABEL},
    }

    event = sansio.Event(data, event="pull_request", delivery_id="1")

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
        "/repos/python/cpython/pulls/5547": {
            "user": {"login": "Mariatta"},
            "merged_by": None,
            "labels": [{"name": "awaiting review"}, {"name": AUTOMERGE_LABEL}],
        },
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 1,
            "items": [
                {
                    "number": 5547,
                    "title": "bpo-32720: Fixed the replacement field grammar documentation.",
                    "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.",
                    "labels": [{"name": "awaiting merge"}, {"name": AUTOMERGE_LABEL}],
                }
            ],
        },
        "/teams/42/memberships/Mariatta": True,
    }

    getiter = {
        "/repos/python/cpython/pulls/5547/commits": [{"sha": sha}],
        "/orgs/python/teams": [{"name": "python core", "id": 42}],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # does not leave a comment


async def test_pr_not_found_for_commit():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {"sha": sha, "commit": {"committer": None, "author": None}}

    event = sansio.Event(data, event="status", delivery_id="1")

    getitem = {
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 0,
            "items": [],
        }
    }

    gh = FakeGH(getitem=getitem)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # does not leave a comment


async def test_automerge_multi_commits_in_pr():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "labeled",
        "pull_request": {
            "user": {"login": "Mariatta"},
            "labels": [
                {"name": "awaiting merge"},
                {"name": AUTOMERGE_LABEL},
            ],
            "head": {"sha": sha},
            "number": 5547,
            "title": "bpo-32720: Fixed the replacement field grammar documentation.",
            "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.",
            "url": "https://api.github.com/repos/python/cpython/pulls/5547",
        },
        "sender": {"login": "Mariatta"},
        "label": {"name": AUTOMERGE_LABEL},
    }

    event = sansio.Event(data, event="pull_request", delivery_id="1")

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
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "success",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                }
            ],
            "total_count": 1,
        },
    }

    getiter = {
        "/repos/python/cpython/pulls/5547/commits": [
            {"sha": "5f007046b5d4766f971272a0cc99f8461215c1ec"},
            {"sha": sha},
        ],
        "/orgs/python/teams": [{"name": "python core", "id": 42}],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment

    assert gh.put_data["sha"] == sha  # is merged
    assert gh.put_data["merge_method"] == "squash"
    assert (
        gh.put_data["commit_title"]
        == "bpo-32720: Fixed the replacement field grammar documentation. (GH-5547)"
    )
    assert (
        gh.put_data["commit_message"]
        == "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`."
    )


async def test_automerge_commit_not_found():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "labeled",
        "pull_request": {
            "user": {"login": "Mariatta"},
            "labels": [
                {"name": "awaiting merge"},
                {"name": AUTOMERGE_LABEL},
            ],
            "head": {"sha": sha},
            "number": 5547,
            "title": "bpo-32720: Fixed the replacement field grammar documentation.",
            "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.",
            "url": "https://api.github.com/repos/python/cpython/pulls/5547",
        },
        "sender": {"login": "Mariatta"},
        "label": {"name": AUTOMERGE_LABEL},
    }

    event = sansio.Event(data, event="pull_request", delivery_id="1")

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
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "success",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                }
            ],
            "total_count": 1,
        },
    }

    getiter = {
        "/repos/python/cpython/pulls/5547/commits": [],
        "/orgs/python/teams": [{"name": "python core", "id": 42}],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # does not merge


async def test_automerge_failed():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "labeled",
        "pull_request": {
            "user": {"login": "Mariatta"},
            "labels": [
                {"name": "awaiting merge"},
                {"name": AUTOMERGE_LABEL},
            ],
            "head": {"sha": sha},
            "number": 5547,
            "title": "bpo-32720: Fixed the replacement field grammar documentation.",
            "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.",
            "url": "https://api.github.com/repos/python/cpython/pulls/5547",
        },
        "sender": {"login": "Mariatta"},
        "label": {"name": AUTOMERGE_LABEL},
    }

    event = sansio.Event(data, event="pull_request", delivery_id="1")

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
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "success",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                }
            ],
            "total_count": 1,
        },
    }

    getiter = {
        "/repos/python/cpython/pulls/5547/commits": [
            {"sha": "5f007046b5d4766f971272a0cc99f8461215c1ec"},
            {"sha": sha},
        ],
        "/orgs/python/teams": [{"name": "python core", "id": 42}],
    }

    gh = FakeGH(
        getitem=getitem,
        getiter=getiter,
        put=gidgethub.BadRequest(status_code=http.HTTPStatus(400)),
        post={
            "html_url": f"https://github.com/python/cpython/pull/5547#issuecomment-401309376"
        },
    )

    await status_change.router.dispatch(event, gh)

    assert gh.put_data["sha"] == sha
    assert gh.put_data["merge_method"] == "squash"
    assert (
        gh.put_data["commit_title"]
        == "bpo-32720: Fixed the replacement field grammar documentation. (GH-5547)"
    )
    assert (
        gh.put_data["commit_message"]
        == "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`."
    )

    assert "Sorry, I can't merge this PR" in gh.post_data["body"]


async def test_automerge_label_added_by_non_core_dev():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "labeled",
        "pull_request": {
            "user": {"login": "miss-islington"},
            "labels": [
                {"name": "awaiting merge"},
                {"name": AUTOMERGE_LABEL},
            ],
            "head": {"sha": sha},
            "number": 5547,
            "title": "bpo-32720: Fixed the replacement field grammar documentation.",
            "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.",
            "url": "https://api.github.com/repos/python/cpython/pulls/5547",
            "issue_url": "https://api.github.com/repos/python/cpython/issues/5547",
        },
        "sender": {"login": "miss-islington"},
        "label": {"name": AUTOMERGE_LABEL},
    }

    event = sansio.Event(data, event="pull_request", delivery_id="1")

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
        "/teams/42/memberships/miss-islington": gidgethub.BadRequest(
            status_code=http.HTTPStatus(404)
        ),
    }

    getiter = {
        "/repos/python/cpython/pulls/5547/commits": [{"sha": sha}],
        "/orgs/python/teams": [{"name": "python core", "id": 42}],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert (
        gh.delete_url == f'{data["pull_request"]["issue_url"]}/labels/{AUTOMERGE_LABEL}'
    )
    assert not hasattr(gh, "post_data")  # does not leave a comment

    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # does not merge


async def test_automerge_label_triggered_by_added_to_pr():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "labeled",
        "pull_request": {
            "user": {"login": "miss-islington"},
            "labels": [
                {"name": "awaiting merge"},
                {"name": AUTOMERGE_LABEL},
            ],
            "head": {"sha": sha},
            "number": 5547,
            "title": "bpo-32720: Fixed the replacement field grammar documentation.",
            "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.",
            "url": "https://api.github.com/repos/python/cpython/pulls/5547",
            "issue_url": "https://api.github.com/repos/python/cpython/issues/5547",
        },
        "sender": {"login": "Mariatta"},
        "label": {"name": AUTOMERGE_LABEL},
    }

    event = sansio.Event(data, event="pull_request", delivery_id="1")

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
        f"/repos/python/cpython/commits/{sha}/check-runs": {
            "check_runs": [
                {
                    "conclusion": "success",
                    "name": "Travis CI - Pull Request",
                    "status": "completed",
                }
            ],
            "total_count": 1,
        },
    }

    getiter = {
        "/repos/python/cpython/pulls/5547/commits": [{"sha": sha}],
        "/orgs/python/teams": [{"name": "python core", "id": 42}],
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await status_change.router.dispatch(event, gh)
    assert gh.patch_url == f'{data["pull_request"]["url"]}'
    assert gh.patch_data == {
        "body": f"{data['pull_request']['body']}\n\nAutomerge-Triggered-By: GH:Mariatta"
    }
