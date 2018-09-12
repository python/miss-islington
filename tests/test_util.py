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


def test_message_normalization():
    message = "<!-- This is an HTML comment -->And this is the part we want"
    assert util.normalize_message(message) == "\n\nAnd this is the part we want"

    message = "<!-- HTML comment -->Part we want<!-- HTML comment 2 -->"
    assert util.normalize_message(message) == "\n\nPart we want"

    message = "\r\nParts <!--comment--> we want\r\nincluded"
    assert util.normalize_message(message) == "\n\nParts  we want\r\nincluded"


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


def test_pr_is_awaiting_merge():
    labels = [{"name": "CLA Signed"}, {"name": "awaiting merge"}]
    assert util.pr_is_awaiting_merge(labels) is True


def test_pr_is_automerge():
    labels = [
        {"name": "CLA Signed"},
        {"name": util.AUTOMERGE_LABEL},
        {"name": "awaiting review"},
    ]
    assert util.pr_is_automerge(labels) is True


def test_pr_is_not_awaiting_merge():
    labels = [
        {"name": "CLA Signed"},
        {"name": "skip issue"},
        {"name": "awaiting review"},
    ]
    assert util.pr_is_awaiting_merge(labels) is False


def test_pr_is_not_automerge():
    labels = [{"name": "CLA Signed"}, {"name": "awaiting merge"}]
    assert util.pr_is_automerge(labels) is False


def test_comment_on_pr_success(requests_mock):
    issue_number = 100
    message = "Thanks for the PR!"
    post_url = (
        f"https://api.github.com/repos/python/cpython/issues/{issue_number}/comments"
    )
    requests_mock.post(
        post_url,
        json={
            "html_url": "https://github.com/python/cpython/pull/{issue_number}#issuecomment-401309376"
        },
        status_code=201,
    )
    response = util.comment_on_pr(issue_number, message)
    assert response.status_code == 201


def test_comment_on_pr_failure(requests_mock):
    issue_number = 100
    message = "Thanks for the PR!"
    post_url = (
        f"https://api.github.com/repos/python/cpython/issues/{issue_number}/comments"
    )
    requests_mock.post(post_url, status_code=400)
    response = util.comment_on_pr(issue_number, message)
    assert response.status_code == 400


def test_assign_pr_to_coredev_success(requests_mock):

    issue_number = 100
    coredev_login = "Mariatta"
    patch_url = f"https://api.github.com/repos/python/cpython/issues/{issue_number}"
    requests_mock.patch(patch_url, status_code=201)
    response = util.assign_pr_to_core_dev(issue_number, coredev_login)
    assert response.status_code == 201


def test_assign_pr_to_coredev_failed(requests_mock):
    issue_number = 100
    coredev_login = "Mariatta"
    patch_url = f"https://api.github.com/repos/python/cpython/issues/{issue_number}"
    requests_mock.patch(patch_url, status_code=400)
    response = util.assign_pr_to_core_dev(issue_number, coredev_login)
    assert response.status_code == 400


async def test_get_pr_for_commit():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    gh = FakeGH(
        getitem={
            f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
                "total_count": 1,
                "items": [
                    {
                        "number": 5547,
                        "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
                        "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
                    }
                ],
            }
        }
    )
    result = await util.get_pr_for_commit(gh, sha)
    assert result == {
        "number": 5547,
        "title": "[3.6] bpo-32720: Fixed the replacement field grammar documentation. (GH-5544)",
        "body": "\n\n`arg_name` and `element_index` are defined as `digit`+ instead of `integer`.\n(cherry picked from commit 7a561afd2c79f63a6008843b83733911d07f0119)\n\nCo-authored-by: Mariatta <Mariatta@users.noreply.github.com>",
    }


async def test_get_pr_for_commit_not_found():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    gh = FakeGH(
        getitem={
            f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
                "total_count": 0,
                "items": [],
            }
        }
    )
    result = await util.get_pr_for_commit(gh, sha)

    assert result is None
