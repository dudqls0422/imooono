"""CAD 교육자료 생성기 테스트 공용 픽스처 (MIDAS·네트워크 불필요).

생성은 비용이 커서 세션당 한 번: 미리보기 포함 1회(out), 결정성 비교용 --no-preview 1회(out2).
"""
from __future__ import annotations

import pytest

from tools.cad_training.cli import main


@pytest.fixture(scope="session")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("cad_training")
    assert main(["--out", str(d)]) == 0
    return d


@pytest.fixture(scope="session")
def out2(tmp_path_factory):
    d = tmp_path_factory.mktemp("cad_training_again")
    assert main(["--out", str(d), "--no-preview"]) == 0
    return d
