"""CAD 교육자료 생성기 테스트 공용 픽스처 (MIDAS·네트워크 불필요).

생성은 비용이 커서 세션당 한 번: 미리보기 포함 1회(out).
결정성 비교용으로는 별도 프로세스 2회를 서로 다른 PYTHONHASHSEED(0, 4)로 생성한다(seed_outs).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools.cad_training.cli import main

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("cad_training")
    assert main(["--out", str(d)]) == 0
    return d


@pytest.fixture(scope="session")
def seed_outs(tmp_path_factory):
    outs = []
    # 0 과 4 는 고정 전 코드에서 CLASSES 순서가 실제로 달랐던 시드 쌍 (1·2 는 우연히 같음)
    for seed in ("0", "4"):
        d = tmp_path_factory.mktemp(f"cad_training_seed{seed}")
        env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONIOENCODING="utf-8")
        subprocess.run([sys.executable, "-m", "tools.cad_training", "--out", str(d), "--no-preview"],
                       cwd=REPO, env=env, check=True, capture_output=True)
        outs.append(d)
    return outs
