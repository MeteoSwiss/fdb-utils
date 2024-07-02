fdb-utils
###########

Python library for users and admins of `FDB <https://github.com/ecmwf/fdb>`_.


Installation 
--------------

Dependencies
============================
FDB Utils depends on the FDB and Eccodes libraries, these are not installed with pip. The following environment variables need to be set:

.. code-block:: console

    export FDB5_CONFIG_FILE=<path/to/fdb-config.yaml> 
    export FDB5_HOME=<path/to/fdb/home>
    export ECCODES_HOME=<path/to/eccodes/home>

See https://meteoswiss.atlassian.net/wiki/x/gY_XC for the environment variables to use for MeteoSwiss's realtime FDB (at CSCS).

Install the package from PyPI (MeteoSwiss Nexus)

.. code-block:: console

    pip install fdb-utils

.. code-block:: console

    fdb-utils --help


Development
--------------------


Setup virtual environment

.. code-block:: console

    cd fdb-utils
    poetry install


Run tests

.. code-block:: console

    poetry run pytest

Generate documentation

.. code-block:: console

    poetry run sphinx-build doc doc/_build

Then open the index.html file generated in *fdb-utils/build/_build/*

Build wheels

.. code-block:: console

    poetry build
