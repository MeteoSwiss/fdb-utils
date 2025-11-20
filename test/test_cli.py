from typer.testing import CliRunner

import pytest

from fdb_utils.main import app
from .conftest import fdb
from unittest.mock import patch

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
    assert "Are you sure you want to list everything in FDB? (may take some time)." in result.stdout

def test_list_show(fdb):
    result = runner.invoke(app, ["list", "date,number,step"], input='Y')
    print(result.stdout)
    assert result.exit_code == 0
    assert "Keys/Values of date, number, step in FDB:" in result.stdout
    assert "number: Key not found" in result.stdout
    assert "step: Key not found" in result.stdout
    assert "date: Key not found" in result.stdout
    assert "No metadata found matching your request." in result.stdout

@patch("fdb_utils.main.list_all_values")
def test_list_all(mock_list_all_values):

    result = runner.invoke(app, ["list"], input='Y')

    mock_list_all_values.assert_called_once_with()

    assert result.exit_code == 0
    assert "Are you sure you want to list everything in FDB? (may take some time)." in result.stdout

@patch("fdb_utils.main.list_all_values")
def test_list_filter(mock_list_all_values):

    result = runner.invoke(app, ["list", "--filter", "date=20240606,number=0,step=0"], input='Y')

    mock_list_all_values.assert_called_once_with(date='20240606', number='0', step='0')

    assert result.exit_code == 0

@patch("fdb_utils.main.list_all_values")
def test_list_filter_alias(mock_list_all_values):

    result = runner.invoke(app, ["list", "-f", "date=20240606,number=0,step=0"], input='Y')

    mock_list_all_values.assert_called_once_with(date='20240606', number='0', step='0')

    assert result.exit_code == 0

@patch("fdb_utils.main.list_all_values")
def test_list_select(mock_list_all_values):

    result = runner.invoke(app, ["list", "date,number,step"], input='Y')

    mock_list_all_values.assert_called_once_with('date', 'number', 'step')

    assert result.exit_code == 0

@patch("fdb_utils.main.list_all_values")
def test_list_filter_and_select(mock_list_all_values):

    result = runner.invoke(
        app,
        ["list", "date,number,step", "--filter", "date=20240606,number=0,step=0"],
        input='Y'
        )

    mock_list_all_values.assert_called_once_with(
        'date',
        'number',
        'step',
        date='20240606',
        number='0',
        step='0'
        )

    assert result.exit_code == 0
