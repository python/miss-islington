import http
import textwrap

import pytest
import gidgethub

from unittest import mock


from miss_islington import util


class FakeGH:
    def __init__(self, *, getitem=None, post=None, patch=None):
        self._getitem_return = getitem
        self._post_return = post
        self._patch_return = patch
        self.getitem_url = None
        self.patch_url = self.patch_data = None
        self.post_url = self.post_data = None

    async def getitem(self, url):
        self.getitem_url = url
        return self._getitem_return[self.getitem_url]

    async def patch(self, url, *, data):
        self.patch_url = url
        self.patch_data = data
        return self._patch_return

    async def post(self, url, *, data):
        self.post_url = url
        self.post_data = data
        print(type(self._post_return))
        if isinstance(self._post_return, Exception):
            print("raising")
            raise self._post_return
        else:
            return self._post_return


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



async def test_get_gh_participants_different_creator_and_committer():
    gh = FakeGH(
        getitem={
            "/repos/python/cpython/pulls/5544": {
                "user": {"login": "miss-islington"},
                "merged_by": {"login": "bedevere-bot"},
            }
        }
    )
    result = await util.get_gh_participants(gh, 5544)
    assert result == "@miss-islington and @bedevere-bot"


async def test_get_gh_participants_same_creator_and_committer():
    gh = FakeGH(
        getitem={
            "/repos/python/cpython/pulls/5544": {
                "user": {"login": "bedevere-bot"},
                "merged_by": {"login": "bedevere-bot"},
            }
        }
    )
    result = await util.get_gh_participants(gh, 5544)
    assert result == "@bedevere-bot"


async def test_get_gh_participants_pr_not_merged():
    gh = FakeGH(
        getitem={
            "/repos/python/cpython/pulls/5544": {
                "user": {"login": "bedevere-bot"},
                "merged_by": None,
            }
        }
    )
    result = await util.get_gh_participants(gh, 5544)
    assert result == "@bedevere-bot"


async def test_get_gh_participants_merged_by_miss_islington():
    gh = FakeGH(
        getitem={
            "/repos/python/cpython/pulls/5544": {
                "user": {"login": "bedevere-bot"},
                "merged_by": {"login": "miss-islington"},
            }
        }
    )
    result = await util.get_gh_participants(gh, 5544)
    assert result == "@bedevere-bot"


def test_get_participants_different_creator_and_committer():
    assert (
        util.get_participants("miss-islington", "bedevere-bot")
        == "@miss-islington and @bedevere-bot"
    )


def test_get_participants_merged_by_miss_islington():
    assert util.get_participants("bedevere-bot", "miss-islington") == "@bedevere-bot"


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




async def test_comment_on_pr_success():
    issue_number = 100
    message = "Thanks for the PR!"

    gh = FakeGH(
        post={
            "html_url": f"https://github.com/python/cpython/pull/{issue_number}#issuecomment-401309376"
        }
    )

    await util.comment_on_pr(gh, issue_number, message)
    assert gh.post_url == f"/repos/python/cpython/issues/{issue_number}/comments"
    assert gh.post_data == {"body": message}


async def test_comment_on_pr_failure():
    issue_number = 100
    message = "Thanks for the PR!"
    gh = FakeGH(post=gidgethub.BadRequest(status_code=http.HTTPStatus(400)))

    with pytest.raises(gidgethub.BadRequest):
        await util.comment_on_pr(gh, issue_number, message)


async def test_assign_pr_to_coredev():

    issue_number = 100
    coredev_login = "Mariatta"
    gh = FakeGH()

    await util.assign_pr_to_core_dev(gh, issue_number, coredev_login)
    assert gh.patch_url == f"/repos/python/cpython/issues/{issue_number}"
