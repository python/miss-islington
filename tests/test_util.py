import http
import pytest
import gidgethub

from unittest import mock


from miss_islington import util


class FakeGH:
    def __init__(self, *, getiter=None, getitem=None, post=None):
        self._getitem_return = getitem
        self._getiter_return = getiter
        self._post_return = post
        self.getitem_url = None
        self.getiter_url = None
        self.post_url = self.post_data = None

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


def test_title_normalization():
    title = "abcd"
    body = "1234"
    assert util.normalize_title(title, body) == title

    title = "[2.7] bpo-29243: Fix Makefile with respect to --enable-optimizations …"
    body = "…(GH-1478)\r\n\r\nstuff"
    expected = (
        "[2.7] bpo-29243: Fix Makefile with respect to --enable-optimizations (GH-1478)"
    )
    assert util.normalize_title(title, body) == expected

    title = "[2.7] bpo-29243: Fix Makefile with respect to --enable-optimizations …"
    body = "…(GH-1478)"
    assert util.normalize_title(title, body) == expected

    title = (
        "[2.7] bpo-29243: Fix Makefile with respect to --enable-optimizations (GH-14…"
    )
    body = "…78)"
    assert util.normalize_title(title, body) == expected


def test_get_participants_different_creator_and_committer():
    assert (
        util.get_participants("miss-islington", "bedevere-bot")
        == "@miss-islington and @bedevere-bot"
    )


def test_get_participants_same_creator_and_committer():
    assert (
        util.get_participants("miss-islington", "miss-islington") == "@miss-islington"
    )


@mock.patch("subprocess.check_output")
def test_is_cpython_repo_contains_first_cpython_commit(subprocess_check_output):
    mock_output = b"""commit 7f777ed95a19224294949e1b4ce56bbffcb1fe9f
Author: Guido van Rossum <guido@python.org>
Date:   Thu Aug 9 14:25:15 1990 +0000

    Initial revision"""
    subprocess_check_output.return_value = mock_output
    assert util.is_cpython_repo()


def test_is_not_cpython_repo():
    assert util.is_cpython_repo() == False


async def test_is_core_dev():
    teams = [{"name": "not Python core"}]
    gh = FakeGH(getiter={"/orgs/python/teams": teams})
    with pytest.raises(ValueError):
        await util.is_core_dev(gh, "mariatta")

    teams = [{"name": "python core", "id": 42}]
    getitem = {"/teams/42/memberships/mariatta": True}
    gh = FakeGH(getiter={"/orgs/python/teams": teams}, getitem=getitem)
    assert await util.is_core_dev(gh, "mariatta")
    assert gh.getiter_url == "/orgs/python/teams"

    teams = [{"name": "python core", "id": 42}]
    getitem = {
        "/teams/42/memberships/miss-islington": gidgethub.BadRequest(
            status_code=http.HTTPStatus(404)
        )
    }
    gh = FakeGH(getiter={"/orgs/python/teams": teams}, getitem=getitem)
    assert not await util.is_core_dev(gh, "miss-islington")

    teams = [{"name": "python core", "id": 42}]
    getitem = {
        "/teams/42/memberships/miss-islington": gidgethub.BadRequest(
            status_code=http.HTTPStatus(400)
        )
    }
    gh = FakeGH(getiter={"/orgs/python/teams": teams}, getitem=getitem)
    with pytest.raises(gidgethub.BadRequest):
        await util.is_core_dev(gh, "miss-islington")
