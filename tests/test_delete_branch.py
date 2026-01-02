import os
from unittest import mock

from gidgethub import sansio
import pytest

os.environ.setdefault("HEROKU_REDIS_MAROON_URL", "someurl")

from miss_islington import delete_branch, tasks


class FakeGH:
    pass


async def test_branch_deletion_queued_when_pr_merged():
    data = {
        "action": "closed",
        "pull_request": {
            "number": 5722,
            "user": {"login": "miss-islington"},
            "merged": True,
            "head": {"ref": "backport-17ab8f0-3.7"},
            "url": "https://api.github.com/repos/python/cpython/pulls/5722",
        },
        "installation": {"id": 123},
    }
    event = sansio.Event(data, event="pull_request", delivery_id="1")

    gh = FakeGH()
    with mock.patch.object(tasks.delete_branch_task, "delay") as mock_delay:
        await delete_branch.router.dispatch(event, gh)
        mock_delay.assert_called_once_with(
            "backport-17ab8f0-3.7",
            "https://api.github.com/repos/python/cpython/pulls/5722",
            True,
            installation_id=123
        )


async def test_branch_deletion_queued_when_pr_closed_not_merged():
    data = {
        "action": "closed",
        "pull_request": {
            "number": 5722,
            "user": {"login": "miss-islington"},
            "merged": False,
            "head": {"ref": "backport-17ab8f0-3.7"},
            "url": "https://api.github.com/repos/python/cpython/pulls/5722",
        },
        "installation": {"id": 456},
    }
    event = sansio.Event(data, event="pull_request", delivery_id="1")

    gh = FakeGH()
    with mock.patch.object(tasks.delete_branch_task, "delay") as mock_delay:
        await delete_branch.router.dispatch(event, gh)
        mock_delay.assert_called_once_with(
            "backport-17ab8f0-3.7",
            "https://api.github.com/repos/python/cpython/pulls/5722",
            False,
            installation_id=456
        )


async def test_ignore_non_miss_islington_prs():
    data = {
        "action": "closed",
        "pull_request": {
            "number": 5722,
            "user": {"login": "Mariatta"},
            "merged": True,
            "head": {"ref": "backport-17ab8f0-3.7"},
            "url": "https://api.github.com/repos/python/cpython/pulls/5722",
        },
        "installation": {"id": 123},
    }
    event = sansio.Event(data, event="pull_request", delivery_id="1")

    gh = FakeGH()
    with mock.patch.object(tasks.delete_branch_task, "delay") as mock_delay:
        await delete_branch.router.dispatch(event, gh)
        mock_delay.assert_not_called()


def test_git_delete_branch_success():
    with mock.patch("subprocess.check_output") as mock_subprocess:
        tasks._git_delete_branch("backport-17ab8f0-3.7")
        mock_subprocess.assert_called_once_with(
            ["git", "push", "origin", "--delete", "backport-17ab8f0-3.7"],
            stderr=mock.ANY
        )


def test_git_delete_branch_failure():
    with mock.patch("subprocess.check_output") as mock_subprocess:
        import subprocess
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            1, "git", output=b"error: unable to delete"
        )
        with pytest.raises(subprocess.CalledProcessError):
            tasks._git_delete_branch("backport-17ab8f0-3.7")
