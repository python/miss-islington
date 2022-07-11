import http

import gidgethub
from gidgethub import sansio
from tests.test_status_change import FakeGH

from miss_islington import check_run
from miss_islington.util import AUTOMERGE_LABEL


async def test_check_run_completed_ci_passed_with_awaiting_merge_label_pr_is_merged():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "completed",
        "check_run": {"head_sha": sha},
        "sender": {"login": "miss-islington"},
    }
    event = sansio.Event(data, event="check_run", delivery_id="1")

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
    await check_run.router.dispatch(event, gh)
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


async def test_check_run_completed_other_check_run_pending_with_awaiting_merge_label_pr_is_not_merged():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "completed",
        "check_run": {"head_sha": sha},
        "sender": {"login": "miss-islington"},
    }
    event = sansio.Event(data, event="check_run", delivery_id="1")

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
                },
                {"conclusion": None, "name": "Docs", "status": "queued"},
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
    await check_run.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_check_run_completed_other_check_run_queued_with_awaiting_merge_label_pr_is_not_merged():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "completed",
        "check_run": {"head_sha": sha},
        "sender": {"login": "miss-islington"},
    }
    event = sansio.Event(data, event="check_run", delivery_id="1")

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
                },
                {"conclusion": None, "name": "Docs", "status": "queued"},
            ],
            "total_count": 1,
        },
    }

    gh = FakeGH(getitem=getitem)
    await check_run.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_check_run_completed_failure_with_awaiting_merge_label_pr_is_not_merged():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "completed",
        "check_run": {"head_sha": sha},
        "sender": {"login": "miss-islington"},
    }
    event = sansio.Event(data, event="check_run", delivery_id="1")

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
                },
                {"conclusion": "failure", "name": "Docs", "status": "completed"},
            ],
            "total_count": 1,
        },
    }

    gh = FakeGH(getitem=getitem)
    await check_run.router.dispatch(event, gh)
    assert len(gh.post_data["body"]) is not None  # leaves a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_check_run_completed_timed_out_with_awaiting_merge_label_pr_is_not_merged():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "completed",
        "check_run": {"head_sha": sha},
        "sender": {"login": "miss-islington"},
    }
    event = sansio.Event(data, event="check_run", delivery_id="1")

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
                },
                {"conclusion": "timed_out", "name": "Docs", "status": "completed"},
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
    await check_run.router.dispatch(event, gh)
    assert len(gh.post_data["body"]) is not None  # leaves a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_check_run_created_with_awaiting_merge_label_pr_is_not_merged():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "created",
        "check_run": {"head_sha": sha},
        "sender": {"login": "miss-islington"},
    }
    event = sansio.Event(data, event="check_run", delivery_id="1")

    gh = FakeGH()
    await check_run.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_check_run_completed_with_awaiting_merge_label_not_miss_islington_is_not_merged():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "completed",
        "check_run": {"head_sha": sha},
        "sender": {"login": "Mariatta"},
    }
    event = sansio.Event(data, event="check_run", delivery_id="1")

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
    await check_run.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # is not merged


async def test_pr_not_found_for_commit():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "completed",
        "check_run": {"head_sha": sha},
        "sender": {"login": "Mariatta"},
    }
    event = sansio.Event(data, event="check_run", delivery_id="1")

    getitem = {
        f"/search/issues?q=type:pr+repo:python/cpython+sha:{sha}": {
            "total_count": 0,
            "items": [],
        }
    }

    gh = FakeGH(getitem=getitem)
    await check_run.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # does not leave a comment


async def test_ci_passed_automerge():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "completed",
        "check_run": {"head_sha": sha},
        "sender": {"login": "Mariatta"},
    }
    event = sansio.Event(data, event="check_run", delivery_id="1")

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
    await check_run.router.dispatch(event, gh)
    assert len(gh.post_data["body"]) is not None  # leaves a comment
    assert gh.put_data["sha"] == sha  # is merged
    assert gh.put_data["merge_method"] == "squash"
    assert (
        gh.put_data["commit_title"]
        == "bpo-32720: Fixed the replacement field grammar documentation. (GH-5547)"
    )


async def test_ci_passed_not_automerge():
    sha = "f2393593c99dd2d3ab8bfab6fcc5ddee540518a9"
    data = {
        "action": "completed",
        "check_run": {"head_sha": sha},
        "sender": {"login": "Mariatta"},
    }
    event = sansio.Event(data, event="check_run", delivery_id="1")

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
                    "message": "bpo-32720: Fixed the replacement field grammar documentation."
                },
            }
        ]
    }

    gh = FakeGH(getitem=getitem, getiter=getiter)
    await check_run.router.dispatch(event, gh)
    assert not hasattr(gh, "post_data")  # does not leave a comment
    assert not hasattr(gh, "put_data")  # does not leave a comment
