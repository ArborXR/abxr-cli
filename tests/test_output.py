import json

import yaml

from abxr.output import print_formatted


def test_json_format(capsys):
    print_formatted("json", {"foo": "bar"})
    captured = capsys.readouterr()
    assert json.loads(captured.out.strip()) == {"foo": "bar"}


def test_yaml_format(capsys):
    print_formatted("yaml", {"foo": "bar"})
    captured = capsys.readouterr()
    assert yaml.safe_load(captured.out) == {"foo": "bar"}


def test_invalid_format(capsys):
    print_formatted("xml", {"foo": "bar"})
    captured = capsys.readouterr()
    assert "Invalid output format" in captured.out


def test_yaml_list(capsys):
    print_formatted("yaml", [{"id": 1}, {"id": 2}])
    captured = capsys.readouterr()
    assert yaml.safe_load(captured.out) == [{"id": 1}, {"id": 2}]
