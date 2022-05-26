miss-islington
==============

.. image:: https://github.com/python/miss-islington/actions/workflows/ci.yml/badge.svg?event=push
    :target: https://github.com/python/miss-islington/actions
.. image:: https://codecov.io/gh/python/miss-islington/branch/main/graph/badge.svg
    :target: https://codecov.io/gh/python/miss-islington
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black

🐍🍒⛏🤖

Bot for backporting and merging `CPython <https://github.com/python/cpython/>`_ Pull Requests.

miss-islington requires Python 3.6+.

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

If a Python core developer approved a PR made by anyone and added the "🤖 automerge" label,
it will be automatically merged once all the CI checks pass.


Setup Info
==========

Requires Python 3.6+

Create virtual environment and activate it:
.. code-block:: shell
   $ python3 -m venv venv
   $ source venv/bin/activate

Install development or production dependencies:
.. code-block:: shell
   (venv) $ pip install -r dev-requirements.txt  # for development
   (venv) $ pip install -r requirements.txt  # for production

Run the test code:
.. code-block:: shell
   (venv) $ pytest


**Aside**: where does the name come from?
=========================================

According to Wikipedia, Miss Islington is the name of the witch in the
`Monty Python and the Holy Grail <https://www.youtube.com/watch?v=yp_l5ntikaU>`_
sketch.
