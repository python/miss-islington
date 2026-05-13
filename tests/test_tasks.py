import os
import subprocess
from unittest import mock

from cherry_picker import cherry_picker

os.environ.setdefault("HEROKU_REDIS_MAROON_URL", "someurl")

from miss_islington import tasks


async def test_invalid_repo_exception_posts_comment_and_clears_state():
    """A stuck cherry-picker.state in git config used to wedge every
    subsequent backport: CherryPicker() init raised InvalidRepoException
    and the task crashed with no comment posted. The task now wipes
    stale state pre-flight and posts an error comment if init still fails.
    """
    with (
        mock.patch("miss_islington.tasks.aiohttp.ClientSession"),
        mock.patch(
            "miss_islington.tasks.apps.get_installation_access_token",
            new=mock.AsyncMock(return_value={"token": "test-token"}),
        ),
        mock.patch("miss_islington.tasks.util.is_cpython_repo", return_value=True),
        mock.patch("miss_islington.tasks.subprocess.check_output"),
        mock.patch("miss_islington.tasks.subprocess.run") as run_mock,
        mock.patch(
            "miss_islington.tasks.cherry_picker.CherryPicker",
            side_effect=cherry_picker.InvalidRepoException("stuck state"),
        ),
        mock.patch(
            "miss_islington.tasks.util.comment_on_pr", new=mock.AsyncMock()
        ) as comment_mock,
        mock.patch(
            "miss_islington.tasks.util.assign_pr_to_core_dev", new=mock.AsyncMock()
        ) as assign_mock,
    ):
        await tasks.backport_task_asyncio(
            "7a4c6dfb8839eb05fb87baf70364680e45001dd4",
            "3.15",
            issue_number=130749,
            created_by="medmunds",
            merged_by="bitdancer",
            installation_id=42958231,
        )

    run_mock.assert_any_call(
        ["git", "config", "--local", "--remove-section", "cherry-picker"],
        stderr=subprocess.DEVNULL,
        check=False,
    )

    comment_mock.assert_awaited_once()
    posted_message = comment_mock.await_args.args[2]
    assert "3.15" in posted_message
    assert "@bitdancer" in posted_message

    assign_mock.assert_awaited_once()
    assert assign_mock.await_args.args[1] == 130749
    assert assign_mock.await_args.args[2] == "bitdancer"