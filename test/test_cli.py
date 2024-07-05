from typer.testing import CliRunner

import pytest

from fdb_utils.main import app
from .conftest import fdb

runner = CliRunner()


def test_info():
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "Version" in result.stdout
    assert "Config" in result.stdout
    assert "Schema" in result.stdout

def test_list_all_abort():
    result = runner.invoke(app, ["list"], input='N')
    assert result.exit_code == 1
    assert "Are you sure you want list everything in FDB? (may take some time)." in result.stdout

def test_list_all():
    result = runner.invoke(app, ["list"], input='Y')
    assert result.exit_code == 0
    assert "Are you sure you want list everything in FDB? (may take some time)." in result.stdout

def test_list_filter():
    result = runner.invoke(app, ["list", "--filter", "date=20240606,number=0,step=0"], input='Y')
    assert result.exit_code == 0
    assert "Keys/Values in FDB for {'date': '20240606', 'number': '0', 'step': '0'}:" in result.stdout

def test_list_show(fdb):
    result = runner.invoke(app, ["list", "--show", "date,number,step"], input='Y')
    print(result.stdout)
    assert result.exit_code == 0
    assert "Keys/Values of date, number, step in FDB:" in result.stdout
    assert "number: Key not found" in result.stdout
    assert "step: Key not found" in result.stdout
    assert "date: Key not found" in result.stdout
    assert "No metadata found matching your request." in result.stdout
