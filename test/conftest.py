import logging
import os
from pathlib import Path
import subprocess
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

    _set_grib_definitions_path()
    _set_local_eccodes_install_prefix(config)
    _set_local_fdb_install_prefix(config)
    _set_fdb_config(config)

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


def _set_grib_definitions_path():

    if 'GRIB_DEFINITION_PATH' not in os.environ:

        definitions_dir = WORKDIR / 'resource'

        if not os.path.exists(definitions_dir / 'eccodes') and not os.path.exists(definitions_dir / 'eccodes-cosmo-resources'):

            eccodes_dir = f"{WORKDIR / 'eccodes'}"
            eccodes_cosmo_dir = f"{WORKDIR / 'eccodes-cosmo-resources'}"
            
            if os.path.exists(eccodes_dir) and os.path.isdir(eccodes_dir):
                shutil.rmtree(eccodes_dir)
            if os.path.exists(eccodes_cosmo_dir) and os.path.isdir(eccodes_cosmo_dir):
                shutil.rmtree(eccodes_cosmo_dir)

            subprocess.run(["git", "clone", "--depth", "1", "-b", "2.35.0",
                            "https://github.com/ecmwf/eccodes.git", f"{eccodes_dir}"])
            subprocess.run(["git", "clone", "--depth", "1", "-b", "v2.35.0.1dm1",
                            "https://github.com/COSMO-ORG/eccodes-cosmo-resources.git", f"{eccodes_cosmo_dir}"])
            
            for i in ('eccodes-cosmo-resources', 'eccodes'):
                # Keep only definitions folder from eccodes/eccodes-cosmo-resources
                definitions_src = WORKDIR / i 
                definitions_dest = definitions_dir / i / 'definitions'
                shutil.copytree(definitions_src / 'definitions', definitions_dest)
                shutil.rmtree(definitions_src)

        os.environ["GRIB_DEFINITION_PATH"] = f"{definitions_dir / 'eccodes-cosmo-resources' / 'definitions' }:{definitions_dir / 'eccodes' / 'definitions'}"

    print("GRIB_DEFINITION_PATH: %s" % os.getenv("GRIB_DEFINITION_PATH", 'unset'))

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
            logging.error("Set ECCODES_DIR in fdb-data-poller/test/.env for local testing.")
            raise e
        

def _set_local_fdb_install_prefix(config: dict):
    try:
        import pyfdb
    except RuntimeError as e:
        if 'FDB5_HOME' in config:
            os.environ['FDB5_HOME'] = config['FDB5_HOME']

        lib =  Path(os.getenv("FDB5_HOME", '/unset'))/ 'lib' / 'libfdb5.so'
        lib64 = Path(os.getenv("FDB5_HOME", '/unset')) / 'lib64' / 'libfdb5.so'
        bin = Path(os.getenv("FDB5_HOME", '/unset'))/ 'bin'
        if lib.exists() or lib64.exists():
            print("FDB5_HOME: %s" % os.getenv("FDB5_HOME", 'unset'))
        else:
            logging.error("Set FDB5_HOME in fdb-data-poller/test/.env for local testing.")
            raise e
        if bin.exists():
            os.environ["PATH"] = str(bin) + ':' + os.environ["PATH"] 


def _set_fdb_config(config: dict):


    schema = WORKDIR / 'resource' / 'schema'
    fdb_root = WORKDIR / 'fdb-root'
    config = WORKDIR / 'resource' / 'config-template.yaml'
    new_config = WORKDIR / 'resource' /'config.yaml'

    with open(config, 'r') as f:
        try:
            loaded = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            print(exc)

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