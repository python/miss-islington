from unittest import mock


from backport import util


def test_title_normalization():
    title = "abcd"
    body = "1234"
    assert util.normalize_title(title, body) == title

    title = "[2.7] bpo-29243: Fix Makefile with respect to --enable-optimizations …"
    body = "…(GH-1478)\r\n\r\nstuff"
    expected = '[2.7] bpo-29243: Fix Makefile with respect to --enable-optimizations (GH-1478)'
    assert util.normalize_title(title, body) == expected

    title = "[2.7] bpo-29243: Fix Makefile with respect to --enable-optimizations …"
    body = "…(GH-1478)"
    assert util.normalize_title(title, body) == expected

    title = "[2.7] bpo-29243: Fix Makefile with respect to --enable-optimizations (GH-14…"
    body = "…78)"
    assert util.normalize_title(title, body) == expected


def test_get_participants_different_creator_and_committer():
    assert util.get_participants("miss-islington", "bedevere-bot") \
           == "@miss-islington and @bedevere-bot"


def test_get_participants_same_creator_and_committer():
    assert util.get_participants("miss-islington",
                            "miss-islington") == "@miss-islington"


@mock.patch('subprocess.check_output')
def test_is_cpython_repo_contains_first_cpython_commit(subprocess_check_output):
    mock_output = b"""commit 7f777ed95a19224294949e1b4ce56bbffcb1fe9f
Author: Guido van Rossum <guido@python.org>
Date:   Thu Aug 9 14:25:15 1990 +0000

    Initial revision"""
    subprocess_check_output.return_value = mock_output
    assert util.is_cpython_repo()


def test_is_not_cpython_repo():
    assert util.is_cpython_repo() == False
