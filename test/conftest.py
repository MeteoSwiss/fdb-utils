import logging
import os
from pathlib import Path
import shutil
import os
import gc

import yaml
import pytest
from dotenv import dotenv_values

from fdb_utils.env import fdb_info

WORKDIR: Path = Path(os.path.dirname(os.path.realpath(__file__)))

def pytest_configure(config):

    # The below functions are required for setting up local tests only.
    config = dotenv_values()

    _set_local_eccodes_install_prefix(config)
    _set_local_fdb_install_prefix(config)
    _set_fdb_config()

    fdb_info()


@pytest.fixture
def data_dir() -> Path:
    """Test data directory."""
    pwd: Path = Path(os.path.dirname(os.path.realpath(__file__)))

    return pwd / 'resource' / 'data'

@pytest.fixture
def test_dir() -> Path:
    """Test directory."""
    pwd: Path = Path(os.path.dirname(os.path.realpath(__file__)))

    return pwd

def _set_local_eccodes_install_prefix(config: dict):
    try:
        import eccodes
    except RuntimeError as e:

        if 'ECCODES_DIR' in config:
            os.environ['ECCODES_DIR'] = config['ECCODES_DIR']

        lib = Path(os.getenv("ECCODES_DIR", '/unset')) / 'lib' / 'libeccodes.so'
        lib64 = Path(os.getenv("ECCODES_DIR", '/unset')) / 'lib64' / 'libeccodes.so'
        if lib.exists() or lib64.exists():
            print("ECCODES_DIR: %s" % os.getenv("ECCODES_DIR", 'unset'))
        else:
            logging.error("Set ECCODES_DIR in test/.env for local testing.")
            raise e


def _set_local_fdb_install_prefix(config: dict):
    try:
        import pyfdb
    except RuntimeError:
        if 'FDB5_DIR' in config:
            os.environ['FDB5_DIR'] = config['FDB5_DIR']
        else:
            raise pytest.UsageError("Missing FDB5_DIR environment variable. Set FDB5_DIR in test/.env for local testing.")

        lib =  Path(config['FDB5_DIR']) / 'lib' / 'libfdb5.so'
        lib64 = Path(config['FDB5_DIR']) / 'lib64' / 'libfdb5.so'
        binary = Path(config['FDB5_DIR']) / 'bin'

        if lib.exists() or lib64.exists():
            print("FDB5_DIR: %s" % os.getenv("FDB5_DIR", 'unset'))
        else:
            raise pytest.UsageError("Invalid FDB5_DIR path (%s): missing libfdb5.so" % config['FDB5_DIR'])


        if binary.exists():
            os.environ["PATH"] = str(binary) + ':' + os.environ["PATH"]


def _set_fdb_config():

    schema = WORKDIR / 'resource' / 'schema'
    fdb_root = WORKDIR / 'fdb-root'
    config_template = WORKDIR / 'resource' / 'config-template.yaml'
    new_config = WORKDIR / 'resource' /'config.yaml'

    if env_config := os.getenv("FDB5_CONFIG_FILE"):
        print(f"FDB5_CONFIG_FILE already set: {env_config}")
        config_template = env_config

    with open(config_template, 'r') as f:
        try:
            loaded = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            print(exc)

    if not env_config:
        loaded['schema']=str(schema)

    loaded['spaces'][0]['roots'][0]['path']=str(fdb_root)

    with open(new_config, 'w') as stream:
        try:
            yaml.dump(loaded, stream, default_flow_style=False)
        except yaml.YAMLError as exc:
            print(exc)

    os.environ['FDB5_CONFIG_FILE'] = str(new_config)

    print("FDB5_CONFIG_FILE: %s" % os.getenv("FDB5_CONFIG_FILE", 'unset'))



@pytest.fixture(scope="function")
def fdb(request, test_dir):

    fdb_root = test_dir / 'fdb-root'

    if not fdb_root.exists() or not os.path.isdir(fdb_root):
        os.mkdir(fdb_root)

    import pyfdb

    fdb = pyfdb.FDB()

    def teardown():
        try:
            del fdb
        except:
            pass
        gc.collect()

        print('Deleting fdb')
        shutil.rmtree(fdb_root)

    request.addfinalizer(teardown)

    yield fdb
