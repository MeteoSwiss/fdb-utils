"""This module provides a function for archiving files to FDB."""

import logging
import os

import cffi
from packaging.version import parse


_logger = logging.getLogger(__name__)


def check_fdb_version_greater_than(min_version: str = "5.11.99") -> None:
    """Raises RuntimeError if version of libFDB5 found is less than specified version."""

    import pyfdb

    ffi = cffi.FFI()

    tmp_str = ffi.new('char**')

    pyfdb.lib.fdb_version(tmp_str)
    lib_version = ffi.string(tmp_str[0]).decode('utf-8')

    if parse(lib_version) < parse(min_version):
        raise RuntimeError("Version of libFDB5 found is too old. {} < {}".format(lib_version, min_version))


def validate_environment() -> None:
    if not ('FDB5_CONFIG_FILE' in os.environ or 'FDB5_CONFIG' in os.environ):
        raise RuntimeError("FDB config is unset, set either FDB5_CONFIG_FILE or FDB5_CONFIG.")
    if not ('FDB5_HOME' in os.environ or 'FDB5_DIR' in os.environ):
        raise RuntimeError("Path to FDB5 library is undefined, set either FDB5_HOME or FDB5_DIR.")