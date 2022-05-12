import asyncio

from gidgethub import sansio

from miss_islington import delete_branch


class FakeGH:
    def __init__(self, *, getitem=None):
        self._getitem_return = getitem
        self.getitem_url = None
        self.post_data = None

    async def getitem(self, url):
        self.getitem_url = url
        to_return = self._getitem_return[self.getitem_url]
        return to_return

    async def delete(self, url):
        self.delete_url = url


async def noop_sleep(delay, result=None):
    pass


async def test_branch_deleted_when_pr_merged():
    data = {
        "action": "closed",
        "pull_request": {
            "number": 5722,
            "user": {"login": "miss-islington"},
            "merged": True,
            "merged_by": {"login": "miss-islington"},
            "head": {"ref": "backport-17ab8f0-3.7"},
        },
    }
    event = sansio.Event(data, event="pull_request", delivery_id="1")

    gh = FakeGH()
    await delete_branch.router.dispatch(event, gh)
    assert gh.post_data is None  # does not leave a comment
    assert (
        gh.delete_url
        == f"/repos/miss-islington/cpython/git/refs/heads/{data['pull_request']['head']['ref']}"
    )


async def test_branch_deleted_and_thank_committer():
    data = {
        "action": "closed",
        "pull_request": {
            "number": 5722,
            "user": {"login": "miss-islington"},
            "merged": True,
            "merged_by": {"login": "Mariatta"},
            "head": {"ref": "backport-17ab8f0-3.7"},
        },
    }
    event = sansio.Event(data, event="pull_request", delivery_id="1")

    gh = FakeGH()
    await delete_branch.router.dispatch(event, gh)
    assert gh.post_data is None  # does not leave a comment
    assert (
        gh.delete_url
        == f"/repos/miss-islington/cpython/git/refs/heads/{data['pull_request']['head']['ref']}"
    )


async def test_branch_deleted_and_thanks():
    data = {
        "action": "closed",
        "pull_request": {
            "number": 5722,
            "user": {"login": "miss-islington"},
            "merged": True,
            "merged_by": {"login": "miss-islington"},
            "head": {"ref": "backport-17ab8f0-3.7"},
        },
    }
    event = sansio.Event(data, event="pull_request", delivery_id="1")

    gh = FakeGH()
    await delete_branch.router.dispatch(event, gh)
    assert gh.post_data is None  # does not leave a comment
    assert (
        gh.delete_url
        == f"/repos/miss-islington/cpython/git/refs/heads/{data['pull_request']['head']['ref']}"
    )


async def test_branch_deleted_when_pr_closed(monkeypatch):
    data = {
        "action": "closed",
        "pull_request": {
            "number": 5722,
            "user": {"login": "miss-islington"},
            "merged": False,
            "merged_by": {"login": None},
            "head": {"ref": "backport-17ab8f0-3.7"},
            "url": "https://api.github.com/repos/python/cpython/pulls/5722",
        },
    }
    event = sansio.Event(data, event="pull_request", delivery_id="1")
    getitem = {
        "https://api.github.com/repos/python/cpython/pulls/5722": {"state": "closed"},
    }

    monkeypatch.setattr(asyncio, "sleep", noop_sleep)
    gh = FakeGH(getitem=getitem)
    await delete_branch.router.dispatch(event, gh)
    assert gh.post_data is None  # does not leave a comment
    assert (
        gh.delete_url
        == f"/repos/miss-islington/cpython/git/refs/heads/{data['pull_request']['head']['ref']}"
    )


async def test_branch_not_deleted_when_pr_closed_and_reopened(monkeypatch):
    data = {
        "action": "closed",
        "pull_request": {
            "number": 5722,
            "user": {"login": "miss-islington"},
            "merged": False,
            "merged_by": {"login": None},
            "head": {"ref": "backport-17ab8f0-3.7"},
            "url": "https://api.github.com/repos/python/cpython/pulls/5722",
        },
    }
    event = sansio.Event(data, event="pull_request", delivery_id="1")
    getitem = {
        "https://api.github.com/repos/python/cpython/pulls/5722": {"state": "opened"},
    }

    monkeypatch.setattr(asyncio, "sleep", noop_sleep)
    gh = FakeGH(getitem=getitem)
    await delete_branch.router.dispatch(event, gh)
    assert gh.post_data is None  # does not leave a comment
    assert not hasattr(gh, "delete_url")


async def test_ignore_non_miss_islingtons_prs():
    data = {
        "action": "closed",
        "pull_request": {
            "number": 5722,
            "user": {"login": "Mariatta"},
            "merged": True,
            "merged_by": {"login": "Mariatta"},
            "head": {"ref": "backport-17ab8f0-3.7"},
        },
    }
    event = sansio.Event(data, event="pull_request", delivery_id="1")
    gh = FakeGH()
    await delete_branch.router.dispatch(event, gh)
    assert gh.post_data is None  # does not leave a comment
    assert not hasattr(gh, "delete_url")
