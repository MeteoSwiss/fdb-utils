import logging
import os
from pathlib import Path
import requests
import shutil
import os
import gc
import tarfile
import io

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

def _truncate_path(name: str, cutoff: str) -> str:
    parts = Path(name).parts
    i = parts.index(cutoff) + 1
    return str(Path(*parts[i:]))

@pytest.fixture(scope="session")
def cosmo_definitions(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("cosmo") / "definitions"
    tag = "2.38.3-1"
    name = f"eccodes_definitions.edzw-{tag}.tar.bz2"
    url = f"https://opendata.dwd.de/weather/lib/grib/{name}"
    response = requests.get(url)
    response.raise_for_status()
    with tarfile.open(name, "r:bz2", io.BytesIO(response.content)) as tar:
        members = [
            member.replace(name=_truncate_path(member.name, f"definitions.edzw-{tag}"))
            for member in tar.getmembers()
            if "definitions" in member.name
        ]
        tar.extractall(path, members=members, filter="data")

    return path


@pytest.fixture(scope="session")
def mars_definitions(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("mars") / "definitions"
    name = "v0.0.2.tar.gz"
    url = f"https://github.com/MeteoSwiss/eccodes-cosmo-mars/archive/refs/tags/{name}"
    response = requests.get(url)
    response.raise_for_status()
    with tarfile.open(name, "r:gz", io.BytesIO(response.content)) as tar:
        members = [
            member.replace(name=_truncate_path(member.name, "definitions"))
            for member in tar.getmembers()
            if "definitions" in member.name
        ]
        tar.extractall(path, members=members, filter="data")

    return path


@pytest.fixture(scope="session", autouse=True)
def eccodes_definitions(mars_definitions, cosmo_definitions):
    import eccodes
    vendor = eccodes.codes_definition_path()
    definitions = f"{cosmo_definitions}:{mars_definitions}:{vendor}"
    eccodes.codes_set_definitions_path(definitions)
    os.environ["GRIB_DEFINITION_PATH"] = definitions
    print(f"GRIB_DEFINITION_PATH: {os.environ['GRIB_DEFINITION_PATH']}")

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
        if 'FDB5_HOME' in config:
            os.environ['FDB5_HOME'] = config['FDB5_HOME']
        else:
            raise pytest.UsageError("Missing FDB5_HOME environment variable. Set FDB5_HOME in test/.env for local testing.")
        
        lib =  Path(config['FDB5_HOME']) / 'lib' / 'libfdb5.so'
        lib64 = Path(config['FDB5_HOME']) / 'lib64' / 'libfdb5.so'
        binary = Path(config['FDB5_HOME']) / 'bin'
        
        if lib.exists() or lib64.exists():
            print("FDB5_HOME: %s" % os.getenv("FDB5_HOME", 'unset'))
        else:
            raise pytest.UsageError("Invalid FDB5_HOME path (%s): missing libfdb5.so" % config['FDB5_HOME'])


        if bin.exists():
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
