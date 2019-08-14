miss-islington
==============

.. image:: https://travis-ci.org/python/miss-islington.svg?branch=master
    :target: https://travis-ci.org/python/miss-islington
.. image:: https://codecov.io/gh/python/miss-islington/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/python/miss-islington
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black

🐍🍒⛏🤖

Bot for backporting and merging `CPython <https://github.com/python/cpython/>`_ Pull Requests.

miss-islington requires Python 3.6. Python 3.7 is not yet supported.


Backporting a PR on CPython
===========================

Prior to merging a PR, a Python core developer should apply the
``needs backport to X.Y`` label to the pull request.
Once the pull request has been merged, `@miss-islington <https://github.com/miss-islington>`_
will prepare the backport PR.

If `@miss-islington <https://github.com/miss-islington>`_ encountered any issue while backporting,
it will leave a comment about it, and the PR will be assigned to the core developer
who merged the PR. The PR then needs to be backported manually.


Merging the Backport PR
=======================

If a Python core developer approved the backport PR made by miss-islington, it will be
automatically merged once all the CI checks passed.


Merging PRs
===========

If a Python core developer approved a PR made by anyone and added an "automerge" label,
it will be autmatically merged once all the CI checks pass. This works for PRs from
anyone.


**Aside**: where does the name come from?
=========================================

According to Wikipedia, Miss Islington is the name of the witch in the
`Monty Python and the Holy Grail <https://www.youtube.com/watch?v=yp_l5ntikaU>`_
sketch.
