"""CLI 인자 오류 처리 (백로그 11): 트레이스백 없이 한국어 메시지 + 0 이 아닌 종료코드."""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

from tools.cad_training.cli import main

from .conftest import REPO


def test_out_pointing_to_existing_file_is_usage_error(tmp_path, capsys):
    f = tmp_path / "already.txt"
    f.write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main(["--out", str(f), "--no-preview"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--out 경로가 폴더가 아니라 파일입니다" in err
    assert "Traceback" not in err


def test_out_under_a_file_is_usage_error(tmp_path, capsys):
    f = tmp_path / "already.txt"
    f.write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main(["--out", str(f / "sub"), "--no-preview"])
    assert exc.value.code == 2
    assert "출력 폴더를 만들 수 없습니다" in capsys.readouterr().err


def test_cli_subprocess_has_no_traceback(tmp_path):
    f = tmp_path / "already.txt"
    f.write_text("x", encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, "-m", "tools.cad_training", "--out", str(f)],
                       cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode != 0
    assert "Traceback" not in r.stderr
    assert "파일입니다" in r.stderr
