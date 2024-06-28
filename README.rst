=============================
fdb-utils
=============================

Python library for users and admins of FDB.

Setup virtual environment

.. code-block:: console

    $ cd fdb-utils
    $ poetry install


Run tests

.. code-block:: console

    $ poetry run pytest

Generate documentation

.. code-block:: console

    $ poetry run sphinx-build doc doc/_build

Then open the index.html file generated in *fdb-utils/build/_build/*

Build wheels

.. code-block:: console

    $ poetry build
