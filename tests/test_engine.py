"""Tests fuer DF-CONST-AUTO-EXPANSION [CRUX-MK]."""
import json
from pathlib import Path

import pytest

from engine import (
    AuditLogger,
    ExistingScanner,
    K16Mutex,
    KlauselTemplateEngine,
    KonstDetector,
    TierTemplateEngine,
    run_expansion,
)


# ============================================================
# KonstDetector
# ============================================================

def test_konst_detector_finds_K_pattern(tmp_path: Path) -> None:
    py = tmp_path / "tables.py"
    py.write_text(
        'TIERS = {"K01": "Tier-1", "K02": "Tier-2", "K15": "Tier-3"}\n'
    )
    konsts = KonstDetector.detect(py)
    assert "K01" in konsts
    assert "K02" in konsts
    assert "K15" in konsts


def test_konst_detector_normalizes_padding(tmp_path: Path) -> None:
    """K1 + K01 -> dedupliziert auf K01."""
    py = tmp_path / "t.py"
    py.write_text('x = ["K1", "K01", "K2"]\n')
    konsts = KonstDetector.detect(py)
    assert "K01" in konsts
    assert "K02" in konsts
    # K1 normalisiert auf K01 -> nur einmal
    assert konsts.count("K01") == 1


def test_konst_detector_handles_missing_file(tmp_path: Path) -> None:
    konsts = KonstDetector.detect(tmp_path / "missing.py")
    assert konsts == []


def test_konst_detector_includes_konst_underscore(tmp_path: Path) -> None:
    py = tmp_path / "t.py"
    py.write_text('items = ["KONST_42", "K05"]\n')
    konsts = KonstDetector.detect(py)
    assert "KONST_42" in konsts
    assert "K05" in konsts


# ============================================================
# ExistingScanner
# ============================================================

def test_existing_scanner_detects_complete(tmp_path: Path) -> None:
    """Konst mit 5 Tiers + 50 Klauseln -> complete."""
    vert = tmp_path / "vert"
    klau = tmp_path / "klau"
    konst_v = vert / "K01"
    konst_v.mkdir(parents=True)
    for t in range(1, 6):
        (konst_v / f"tier-{t}.yaml").write_text("x")
    konst_k = klau / "K01"
    konst_k.mkdir(parents=True)
    for n in range(1, 51):
        (konst_k / f"klausel-{n:03d}.md").write_text("x")
    scanner = ExistingScanner(vert, klau)
    status = scanner.is_complete("K01")
    assert status["complete"] is True
    assert status["tiers_found"] == 5
    assert status["klauseln_found"] == 50


def test_existing_scanner_detects_incomplete(tmp_path: Path) -> None:
    vert = tmp_path / "v"
    klau = tmp_path / "k"
    (vert / "K02").mkdir(parents=True)
    scanner = ExistingScanner(vert, klau)
    status = scanner.is_complete("K02")
    assert status["complete"] is False
    assert status["tiers_found"] == 0


# ============================================================
# TierTemplateEngine
# ============================================================

def test_tier_template_engine_renders_skeleton() -> None:
    text = TierTemplateEngine.render("K05", 3)
    assert "konst_id: K05" in text
    assert "tier: Tier-3" in text
    assert "SKELETON" in text


def test_tier_template_engine_generates_5_files(tmp_path: Path) -> None:
    eng = TierTemplateEngine()
    tiers_dir = tmp_path / "K01"
    created = eng.generate_for_konst("K01", tiers_dir, tiers_count=5)
    assert len(created) == 5
    assert all((tiers_dir / f"tier-{i}.yaml").exists() for i in range(1, 6))


def test_tier_template_engine_no_overwrite(tmp_path: Path) -> None:
    """Bei overwrite=False werden existing files erhalten."""
    eng = TierTemplateEngine()
    tiers_dir = tmp_path / "K01"
    tiers_dir.mkdir()
    (tiers_dir / "tier-1.yaml").write_text("USER-CONTENT")
    eng.generate_for_konst("K01", tiers_dir, tiers_count=5, overwrite=False)
    # Existing file unveraendert
    assert (tiers_dir / "tier-1.yaml").read_text() == "USER-CONTENT"
    # Aber tier-2..5 erstellt
    assert (tiers_dir / "tier-5.yaml").exists()


# ============================================================
# KlauselTemplateEngine
# ============================================================

def test_klausel_template_engine_renders() -> None:
    text = KlauselTemplateEngine.render("K01", 7)
    assert "K01-K007" in text
    assert "SKELETON" in text
    assert "[CRUX-MK]" in text


def test_klausel_template_engine_generates_50(tmp_path: Path) -> None:
    eng = KlauselTemplateEngine()
    klau_dir = tmp_path / "K01"
    created = eng.generate_for_konst("K01", klau_dir, klauseln_count=50)
    assert len(created) == 50


# ============================================================
# K16-Mutex
# ============================================================

def test_k16_mutex(tmp_path: Path) -> None:
    m = K16Mutex(tmp_path / ".l")
    assert m.acquire()
    m2 = K16Mutex(tmp_path / ".l")
    assert not m2.acquire()
    m.release()


# ============================================================
# AuditLogger
# ============================================================

def test_audit_logger_appends(tmp_path: Path) -> None:
    log = tmp_path / "audit.jsonl"
    logger = AuditLogger(log)
    logger.log({"x": 1})
    logger.log({"x": 2})
    lines = log.read_text().splitlines()
    assert len(lines) == 2


# ============================================================
# Integration
# ============================================================

def test_run_expansion_creates_skeleton(tmp_path: Path) -> None:
    """run_expansion erkennt K01+K02 und erstellt 5+50 Skelette pro Konst."""
    py_path = tmp_path / "tables.py"
    py_path.write_text('TIERS = {"K01": "Tier-1", "K02": "Tier-2"}\n')
    config = {
        "paths": {
            "python_table_path": "tables.py",
            "vertrags_root": "v/",
            "klauseln_root": "k/",
            "audit_log": "audit.jsonl",
        },
        "k16_concurrent_spawn_mutex": {"lock_dir": str(tmp_path / ".l")},
        "generation": {
            "tiers_per_konst": 5,
            "klauseln_per_konst": 50,
            "skeleton_only": True,
            "overwrite_existing": False,
        },
    }
    result = run_expansion(tmp_path, config)
    assert "K01" in result.konsts_detected
    assert "K02" in result.konsts_detected
    assert result.tier_files_created == 10  # 2 Konsts * 5 Tiers
    assert result.klausel_files_created == 100  # 2 Konsts * 50 Klauseln


def test_run_expansion_idempotent(tmp_path: Path) -> None:
    """Zweiter Run ueber gleiche Konsts erstellt 0 neue Files."""
    py_path = tmp_path / "tables.py"
    py_path.write_text('TIERS = {"K01": "Tier-1"}\n')
    config = {
        "paths": {
            "python_table_path": "tables.py",
            "vertrags_root": "v/",
            "klauseln_root": "k/",
            "audit_log": "audit.jsonl",
        },
        "k16_concurrent_spawn_mutex": {"lock_dir": str(tmp_path / ".l")},
        "generation": {
            "tiers_per_konst": 5,
            "klauseln_per_konst": 50,
            "skeleton_only": True,
            "overwrite_existing": False,
        },
    }
    result1 = run_expansion(tmp_path, config)
    assert result1.tier_files_created == 5
    # Run 2: 0 neue Files
    result2 = run_expansion(tmp_path, config)
    assert result2.tier_files_created == 0
    assert result2.klausel_files_created == 0


def test_run_expansion_stop_flag(tmp_path: Path) -> None:
    config = {
        "paths": {
            "python_table_path": "tables.py",
            "vertrags_root": "v/",
            "klauseln_root": "k/",
            "audit_log": "audit.jsonl",
        },
        "k16_concurrent_spawn_mutex": {"lock_dir": str(tmp_path / ".l")},
        "generation": {
            "tiers_per_konst": 5,
            "klauseln_per_konst": 50,
            "skeleton_only": True,
            "overwrite_existing": False,
        },
    }
    stop = tmp_path / "STOP.flag"
    stop.write_text("x")
    result = run_expansion(tmp_path, config, stop_flag=stop)
    assert result.skipped_due_to_stop_flag is True
