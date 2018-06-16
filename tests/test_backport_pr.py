import os


from unittest import mock
from gidgethub import sansio

os.environ["REDIS_URL"] = "someurl"
from miss_islington import backport_pr


class FakeGH:
    def __init__(self, *, getitem=None, post=None):
        self._getitem_return = getitem
        self.getitem_url = None
        self.getiter_url = None
        self._post_return = post

    async def getitem(self, url, url_vars={}):
        self.getitem_url = sansio.format_url(url, url_vars)
        return self._getitem_return[self.getitem_url]

    async def post(self, url, *, data):
        self.post_url = url
        self.post_data = data
        return self._post_return


async def test_unmerged_pr_is_ignored():
    data = {"action": "closed", "pull_request": {"merged": False}}
    event = sansio.Event(data, event="pull_request", delivery_id="1")
    gh = FakeGH()
    await backport_pr.router.dispatch(event, gh)
    assert gh.getitem_url is None


async def test_labeled_on_unmerged_pr_is_ignored():
    data = {"action": "labeled", "pull_request": {"merged": False}}
    event = sansio.Event(data, event="pull_request", delivery_id="1")
    gh = FakeGH()
    await backport_pr.router.dispatch(event, gh)
    assert gh.getitem_url is None


async def test_labeled_on_merged_pr_no_backport_label():
    data = {
        "action": "labeled",
        "pull_request": {
            "merged": True,
            "number": 1,
            "merged_by": {"login": "Mariatta"},
            "user": {"login": "Mariatta"},
            "merge_commit_sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
        },
        "repository": {
            "issues_url": "https://api.github.com/repos/python/cpython/issues{/number}"
        },
        "label": {"name": "CLA signed"},
    }
    event = sansio.Event(data, event="pull_request", delivery_id="1")

    gh = FakeGH()
    await backport_pr.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")
    assert not hasattr(gh, "post_url")


async def test_merged_pr_no_backport_label():
    data = {
        "action": "closed",
        "pull_request": {
            "merged": True,
            "number": 1,
            "merged_by": {"login": "Mariatta"},
            "user": {"login": "Mariatta"},
            "merge_commit_sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
        },
        "repository": {
            "issues_url": "https://api.github.com/repos/python/cpython/issues/1"
        },
    }
    event = sansio.Event(data, event="pull_request", delivery_id="1")

    getitem = {
        "https://api.github.com/repos/python/cpython/issues/1": {
            "labels_url": "https://api.github.com/repos/python/cpython/issues/1/labels{/name}"
        },
        "https://api.github.com/repos/python/cpython/issues/1/labels": [
            {"name": "CLA signed"}
        ],
    }

    gh = FakeGH(getitem=getitem)
    await backport_pr.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")
    assert not hasattr(gh, "post_url")


async def test_merged_pr_with_backport_label():
    data = {
        "action": "closed",
        "pull_request": {
            "merged": True,
            "number": 1,
            "merged_by": {"login": "Mariatta"},
            "user": {"login": "Mariatta"},
            "merge_commit_sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
        },
        "repository": {
            "issues_url": "https://api.github.com/repos/python/cpython/issues/1"
        },
    }
    event = sansio.Event(data, event="pull_request", delivery_id="1")

    getitem = {
        "https://api.github.com/repos/python/cpython/issues/1": {
            "labels_url": "https://api.github.com/repos/python/cpython/issues/1/labels{/name}"
        },
        "https://api.github.com/repos/python/cpython/issues/1/labels": [
            {"name": "CLA signed"},
            {"name": "needs backport to 3.7"},
        ],
    }

    gh = FakeGH(getitem=getitem)
    with mock.patch("miss_islington.tasks.backport_task.delay"):
        await backport_pr.router.dispatch(event, gh)
        assert "I'm working now to backport this PR to: 3.7" in gh.post_data["body"]
        assert gh.post_url == "/repos/python/cpython/issues/1/comments"


async def test_merged_pr_with_backport_label_thank_pr_author():
    data = {
        "action": "closed",
        "pull_request": {
            "merged": True,
            "number": 1,
            "merged_by": {"login": "Mariatta"},
            "user": {"login": "gvanrossum"},
            "merge_commit_sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
        },
        "repository": {
            "issues_url": "https://api.github.com/repos/python/cpython/issues/1"
        },
    }
    event = sansio.Event(data, event="pull_request", delivery_id="1")

    getitem = {
        "https://api.github.com/repos/python/cpython/issues/1": {
            "labels_url": "https://api.github.com/repos/python/cpython/issues/1/labels{/name}"
        },
        "https://api.github.com/repos/python/cpython/issues/1/labels": [
            {"name": "CLA signed"},
            {"name": "needs backport to 3.7"},
        ],
    }

    gh = FakeGH(getitem=getitem)
    with mock.patch("miss_islington.tasks.backport_task.delay"):
        await backport_pr.router.dispatch(event, gh)
        assert "I'm working now to backport this PR to: 3.7" in gh.post_data["body"]
        assert "Thanks @gvanrossum for the PR" in gh.post_data["body"]
        assert gh.post_url == "/repos/python/cpython/issues/1/comments"


async def test_easter_egg():
    data = {
        "action": "closed",
        "pull_request": {
            "merged": True,
            "number": 1,
            "merged_by": {"login": "Mariatta"},
            "user": {"login": "gvanrossum"},
            "merge_commit_sha": "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9",
        },
        "repository": {
            "issues_url": "https://api.github.com/repos/python/cpython/issues/1"
        },
    }
    event = sansio.Event(data, event="pull_request", delivery_id="1")

    getitem = {
        "https://api.github.com/repos/python/cpython/issues/1": {
            "labels_url": "https://api.github.com/repos/python/cpython/issues/1/labels{/name}"
        },
        "https://api.github.com/repos/python/cpython/issues/1/labels": [
            {"name": "CLA signed"},
            {"name": "needs backport to 3.7"},
        ],
    }

    gh = FakeGH(getitem=getitem)
    with mock.patch("miss_islington.tasks.backport_task.delay"), mock.patch(
        "random.random", return_value=0.1
    ):
        await backport_pr.router.dispatch(event, gh)
        assert "I'm working now to backport this PR to: 3.7" in gh.post_data["body"]
        assert "Thanks @gvanrossum for the PR" in gh.post_data["body"]
        assert "I'm not a witch" not in gh.post_data["body"]
        assert gh.post_url == "/repos/python/cpython/issues/1/comments"

    with mock.patch("miss_islington.tasks.backport_task.delay"), mock.patch(
        "random.random", return_value=0.01
    ):
        await backport_pr.router.dispatch(event, gh)
        assert "I'm working now to backport this PR to: 3.7" in gh.post_data["body"]
        assert "Thanks @gvanrossum for the PR" in gh.post_data["body"]
        assert "I'm not a witch" in gh.post_data["body"]
        assert gh.post_url == "/repos/python/cpython/issues/1/comments"
