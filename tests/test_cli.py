import pytest
from recordfuse.cli import run_cli, parse_args


def test_parse_args_help():
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--help"])
    assert exc_info.value.code == 0


def test_cli_reconcile_execution(tmp_path):
    f1 = tmp_path / "f1.csv"
    f2 = tmp_path / "f2.csv"
    f1.write_text("id,source,name,email,phone\n1,crm,John Smith,john@example.com,0400000000\n")
    f2.write_text("id,source,name,email,phone\n2,billing,John Smith,john@example.com,0400000000\n")

    exit_code = run_cli(["reconcile", str(f1), str(f2)])
    assert exit_code == 0
