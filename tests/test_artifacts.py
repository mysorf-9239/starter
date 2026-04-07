"""Tests for the artifacts subsystem.

Covers:
- Public API shape
- ArtifactsConfig validation
- NullArtifactManager (no filesystem side effects)
- LocalBackend: save, load, resolve_path, list_artifacts, delete
- Versioning strategies: RUN_ID, EPOCH, TIMESTAMP, MANUAL
- Tracker integration (called after save, exceptions swallowed)
- RuntimeContext.artifact_manager integration
- Property-based tests via hypothesis
"""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from starter.artifacts import (
    ArtifactNotFoundError,
    ArtifactRecord,
    ArtifactsConfig,
    ArtifactType,
    NullArtifactManager,
    VersioningStrategy,
    build_artifact_manager,
)
from starter.artifacts.backends.local import LocalBackend
from starter.artifacts.core.validate import validate_artifacts_config

# ---------------------------------------------------------------------------
# Helpers / strategies
# ---------------------------------------------------------------------------

_VALID_NAME = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_-"),
    min_size=1,
    max_size=30,
)
_ARTIFACT_TYPE = st.sampled_from(ArtifactType)
_VERSION_STR = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_-"),
    min_size=1,
    max_size=30,
)
_RUN_ID = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_-"),
    min_size=1,
    max_size=30,
)
_EPOCH_INT = st.integers(min_value=0, max_value=9999)


def _make_paths_section(tmp_path: Path) -> object:
    """Create a minimal PathsSection-like object."""

    class _Paths:
        artifacts_dir = str(tmp_path / "artifacts")
        repo_root = str(tmp_path)
        config_root = str(tmp_path / "conf")
        output_dir = str(tmp_path / "outputs")
        cache_dir = str(tmp_path / ".cache")

    return _Paths()


# ---------------------------------------------------------------------------
# Public API shape
# ---------------------------------------------------------------------------


def test_public_api_exports() -> None:
    from starter.artifacts import (
        ArtifactManager,
        ArtifactNotFoundError,
        ArtifactRecord,
        ArtifactsConfig,
        ArtifactType,
        NullArtifactManager,
        build_artifact_manager,
        parse_artifacts_config,
    )

    assert callable(build_artifact_manager)
    assert callable(parse_artifacts_config)
    assert ArtifactManager is not None
    assert ArtifactNotFoundError is not None
    assert ArtifactRecord is not None
    assert ArtifactType is not None
    assert ArtifactsConfig is not None
    assert NullArtifactManager is not None
    assert VersioningStrategy is not None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_validate_valid_config_passes() -> None:
    cfg = ArtifactsConfig(backend="local", versioning_strategy="run_id")
    validate_artifacts_config(cfg)  # must not raise


def test_validate_invalid_backend_raises() -> None:
    cfg = ArtifactsConfig(backend="s3")
    with pytest.raises(ValueError, match="backend"):
        validate_artifacts_config(cfg)


def test_validate_invalid_strategy_raises() -> None:
    cfg = ArtifactsConfig(versioning_strategy="git_sha")
    with pytest.raises(ValueError, match="versioning_strategy"):
        validate_artifacts_config(cfg)


# Feature: artifacts-subsystem, Property 15: validate_artifacts_config từ chối config không hợp lệ
@given(
    st.text(min_size=1).filter(lambda s: s not in {"local", "disabled"}),
)
@settings(max_examples=100)
def test_property_validation_rejects_invalid_backend(backend: str) -> None:
    cfg = ArtifactsConfig(backend=backend)
    with pytest.raises(ValueError):
        validate_artifacts_config(cfg)


@given(
    st.text(min_size=1).filter(lambda s: s not in {"run_id", "epoch", "timestamp", "manual"}),
)
@settings(max_examples=100)
def test_property_validation_rejects_invalid_strategy(strategy: str) -> None:
    cfg = ArtifactsConfig(versioning_strategy=strategy)
    with pytest.raises(ValueError):
        validate_artifacts_config(cfg)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def test_build_artifact_manager_disabled_returns_null(tmp_path: Path) -> None:
    cfg = ArtifactsConfig(enabled=False)
    paths = _make_paths_section(tmp_path)
    mgr = build_artifact_manager(cfg, paths)  # type: ignore[arg-type]
    assert isinstance(mgr, NullArtifactManager)


def test_build_artifact_manager_local_returns_local_backend(tmp_path: Path) -> None:
    cfg = ArtifactsConfig(backend="local", versioning_strategy="manual")
    paths = _make_paths_section(tmp_path)
    mgr = build_artifact_manager(cfg, paths)  # type: ignore[arg-type]
    assert isinstance(mgr, LocalBackend)


def test_build_artifact_manager_unsupported_backend_raises(tmp_path: Path) -> None:
    cfg = ArtifactsConfig(backend="s3")
    paths = _make_paths_section(tmp_path)
    with pytest.raises(ValueError):
        build_artifact_manager(cfg, paths)  # type: ignore[arg-type]


def test_build_artifact_manager_uses_cfg_base_dir(tmp_path: Path) -> None:
    custom = str(tmp_path / "custom_artifacts")
    cfg = ArtifactsConfig(backend="local", base_dir=custom, versioning_strategy="manual")
    paths = _make_paths_section(tmp_path)
    mgr = build_artifact_manager(cfg, paths)  # type: ignore[arg-type]
    assert isinstance(mgr, LocalBackend)
    assert mgr._base_dir == Path(custom)


# Feature: artifacts-subsystem, Property 11: build_artifact_manager trả về đúng loại instance
@given(st.booleans())
@settings(max_examples=100)
def test_property_factory_returns_correct_type(enabled: bool) -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        cfg = ArtifactsConfig(enabled=enabled, versioning_strategy="manual")
        paths = _make_paths_section(tmp)
        mgr = build_artifact_manager(cfg, paths)  # type: ignore[arg-type]
        if not enabled:
            assert isinstance(mgr, NullArtifactManager)
        else:
            assert isinstance(mgr, LocalBackend)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# NullArtifactManager
# ---------------------------------------------------------------------------


def test_null_manager_save_returns_record(tmp_path: Path) -> None:
    f = tmp_path / "model.pt"
    f.write_bytes(b"data")
    mgr = NullArtifactManager()
    record = mgr.save(f, "model", ArtifactType.CHECKPOINT, version="v1")
    assert isinstance(record, ArtifactRecord)
    assert record.name == "model"
    assert not f.parent.joinpath("checkpoint").exists()  # no filesystem write


def test_null_manager_list_returns_empty() -> None:
    mgr = NullArtifactManager()
    assert mgr.list_artifacts() == []


def test_null_manager_delete_does_not_raise() -> None:
    mgr = NullArtifactManager()
    mgr.delete("model", ArtifactType.CHECKPOINT, "v1")  # must not raise


# Feature: artifacts-subsystem, Property 14: NullArtifactManager không có filesystem side effects
@given(_VALID_NAME, _ARTIFACT_TYPE, _VERSION_STR)
@settings(max_examples=100)
def test_property_null_manager_no_side_effects(
    name: str, artifact_type: ArtifactType, version: str
) -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        f = tmp / "dummy.txt"
        f.write_text("x")
        mgr = NullArtifactManager()
        record = mgr.save(f, name, artifact_type, version=version)
        assert record is not None
        assert mgr.list_artifacts() == []
        mgr.delete(name, artifact_type, version)  # no raise
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# LocalBackend — resolve_path
# ---------------------------------------------------------------------------


def test_resolve_path_pure_function(tmp_path: Path) -> None:
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="manual")
    p1 = mgr.resolve_path("model", ArtifactType.CHECKPOINT, "v1")
    p2 = mgr.resolve_path("model", ArtifactType.CHECKPOINT, "v1")
    assert p1 == p2
    assert not p1.exists()


# Feature: artifacts-subsystem, Property 12: resolve_path là pure function nhất quán với save
@given(_VALID_NAME, _ARTIFACT_TYPE, _VERSION_STR)
@settings(max_examples=100)
def test_property_resolve_path_pure(name: str, artifact_type: ArtifactType, version: str) -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        mgr = LocalBackend(str(tmp / "arts"), versioning_strategy="manual")
        p1 = mgr.resolve_path(name, artifact_type, version)
        p2 = mgr.resolve_path(name, artifact_type, version)
        assert p1 == p2
        assert not p1.exists()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# LocalBackend — versioning
# ---------------------------------------------------------------------------


def test_versioning_run_id(tmp_path: Path) -> None:
    f = tmp_path / "w.pt"
    f.write_bytes(b"x")
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="run_id", run_id="abc123")
    record = mgr.save(f, "model", ArtifactType.CHECKPOINT)
    assert record.version == "abc123"


def test_versioning_run_id_without_run_id_raises(tmp_path: Path) -> None:
    f = tmp_path / "w.pt"
    f.write_bytes(b"x")
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="run_id")
    with pytest.raises(ValueError, match="run_id"):
        mgr.save(f, "model", ArtifactType.CHECKPOINT)


def test_versioning_epoch(tmp_path: Path) -> None:
    f = tmp_path / "w.pt"
    f.write_bytes(b"x")
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="epoch")
    record = mgr.save(f, "model", ArtifactType.CHECKPOINT, version="5")
    assert record.version == "epoch_0005"


def test_versioning_epoch_without_version_raises(tmp_path: Path) -> None:
    f = tmp_path / "w.pt"
    f.write_bytes(b"x")
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="epoch")
    with pytest.raises(ValueError, match="EPOCH"):
        mgr.save(f, "model", ArtifactType.CHECKPOINT)


def test_versioning_timestamp(tmp_path: Path) -> None:
    f = tmp_path / "w.pt"
    f.write_bytes(b"x")
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="timestamp")
    record = mgr.save(f, "model", ArtifactType.CHECKPOINT)
    assert re.match(r"^\d{8}_\d{6}$", record.version)


def test_versioning_manual_without_version_raises(tmp_path: Path) -> None:
    f = tmp_path / "w.pt"
    f.write_bytes(b"x")
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="manual")
    with pytest.raises(ValueError, match="MANUAL"):
        mgr.save(f, "model", ArtifactType.CHECKPOINT)


# Feature: artifacts-subsystem, Property 5: Versioning strategy RUN_ID dùng run_id làm version
@given(_RUN_ID)
@settings(max_examples=100)
def test_property_versioning_run_id(run_id: str) -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        f = tmp / "w.pt"
        f.write_bytes(b"x")
        mgr = LocalBackend(str(tmp / "arts"), versioning_strategy="run_id", run_id=run_id)
        record = mgr.save(f, "model", ArtifactType.CHECKPOINT)
        assert record.version == run_id
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# Feature: artifacts-subsystem, Property 6: Versioning strategy EPOCH format đúng
@given(_EPOCH_INT)
@settings(max_examples=100)
def test_property_versioning_epoch_format(epoch: int) -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        f = tmp / "w.pt"
        f.write_bytes(b"x")
        mgr = LocalBackend(str(tmp / "arts"), versioning_strategy="epoch")
        record = mgr.save(f, "model", ArtifactType.CHECKPOINT, version=str(epoch))
        assert record.version == f"epoch_{epoch:04d}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# Feature: artifacts-subsystem, Property 7: Versioning strategy TIMESTAMP tạo version đúng format
@given(st.just(None))
@settings(max_examples=100)
def test_property_versioning_timestamp_format(_: None) -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        f = tmp / "w.pt"
        f.write_bytes(b"x")
        mgr = LocalBackend(str(tmp / "arts"), versioning_strategy="timestamp")
        record = mgr.save(f, "model", ArtifactType.CHECKPOINT)
        assert re.match(r"^\d{8}_\d{6}$", record.version)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# LocalBackend — save
# ---------------------------------------------------------------------------


def test_save_file_copies_to_correct_path(tmp_path: Path) -> None:
    src = tmp_path / "model.pt"
    src.write_bytes(b"weights")
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="manual")
    record = mgr.save(src, "model", ArtifactType.CHECKPOINT, version="v1")
    assert record.path.exists()
    assert record.path.read_bytes() == b"weights"
    assert record.size_bytes == len(b"weights")


def test_save_directory_copies_tree(tmp_path: Path) -> None:
    src_dir = tmp_path / "run_dir"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("hello")
    (src_dir / "b.txt").write_text("world")
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="manual")
    record = mgr.save(src_dir, "run", ArtifactType.OUTPUT, version="v1")
    assert record.path.is_dir()
    assert (record.path / "a.txt").read_text() == "hello"


def test_save_nonexistent_source_raises(tmp_path: Path) -> None:
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="manual")
    with pytest.raises(ArtifactNotFoundError):
        mgr.save(tmp_path / "ghost.pt", "model", ArtifactType.CHECKPOINT, version="v1")


# Feature: artifacts-subsystem, Property 1: Save tạo đúng cấu trúc đường dẫn
@given(_VALID_NAME, _ARTIFACT_TYPE, _VERSION_STR)
@settings(max_examples=100)
def test_property_save_path_structure(name: str, artifact_type: ArtifactType, version: str) -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        src = tmp / "src.txt"
        src.write_text("data")
        base = tmp / "arts"
        mgr = LocalBackend(str(base), versioning_strategy="manual")
        record = mgr.save(src, name, artifact_type, version=version)
        expected_dir = base / artifact_type.value / name / version
        assert record.path.parent == expected_dir
        assert record.path.exists()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# Feature: artifacts-subsystem, Property 2: Save trả về ArtifactRecord với metadata chính xác
@given(_VALID_NAME, _ARTIFACT_TYPE, _VERSION_STR)
@settings(max_examples=100)
def test_property_save_record_metadata(
    name: str, artifact_type: ArtifactType, version: str
) -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        src = tmp / "src.txt"
        src.write_text("hello")
        mgr = LocalBackend(str(tmp / "arts"), versioning_strategy="manual")
        record = mgr.save(src, name, artifact_type, version=version)
        assert record.name == name
        assert record.version == version
        assert record.artifact_type == artifact_type
        assert record.size_bytes > 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# LocalBackend — tracker integration
# ---------------------------------------------------------------------------


def test_tracker_called_after_save(tmp_path: Path) -> None:
    src = tmp_path / "m.pt"
    src.write_bytes(b"w")
    mock_tracker = MagicMock()
    mgr = LocalBackend(
        str(tmp_path / "arts"),
        versioning_strategy="manual",
        tracker=mock_tracker,
    )
    record = mgr.save(src, "model", ArtifactType.CHECKPOINT, version="v1")
    mock_tracker.log_artifact.assert_called_once_with(str(record.path), name="model")


def test_tracker_exception_does_not_propagate(tmp_path: Path) -> None:
    src = tmp_path / "m.pt"
    src.write_bytes(b"w")
    mock_tracker = MagicMock()
    mock_tracker.log_artifact.side_effect = RuntimeError("upload failed")
    mgr = LocalBackend(
        str(tmp_path / "arts"),
        versioning_strategy="manual",
        tracker=mock_tracker,
    )
    record = mgr.save(src, "model", ArtifactType.CHECKPOINT, version="v1")
    assert record is not None  # save succeeded despite tracker error


# Feature: artifacts-subsystem, Property 10: Tracker được gọi sau mỗi save thành công
@given(st.text(min_size=1))
@settings(max_examples=100)
def test_property_tracker_called_on_save(exc_msg: str) -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        src = tmp / "m.pt"
        src.write_bytes(b"w")
        mock_tracker = MagicMock()
        mock_tracker.log_artifact.side_effect = Exception(exc_msg)
        mgr = LocalBackend(
            str(tmp / "arts"),
            versioning_strategy="manual",
            tracker=mock_tracker,
        )
        record = mgr.save(src, "model", ArtifactType.CHECKPOINT, version="v1")
        assert record is not None
        mock_tracker.log_artifact.assert_called_once()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# LocalBackend — load
# ---------------------------------------------------------------------------


def test_load_existing_artifact(tmp_path: Path) -> None:
    src = tmp_path / "m.pt"
    src.write_bytes(b"w")
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="manual")
    mgr.save(src, "model", ArtifactType.CHECKPOINT, version="v1")
    path = mgr.load("model", ArtifactType.CHECKPOINT, version="v1")
    assert path.exists()


def test_load_nonexistent_raises(tmp_path: Path) -> None:
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="manual")
    with pytest.raises(ArtifactNotFoundError):
        mgr.load("ghost", ArtifactType.CHECKPOINT, version="v1")


def test_load_latest_version(tmp_path: Path) -> None:
    src = tmp_path / "m.pt"
    src.write_bytes(b"w")
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="manual")
    mgr.save(src, "model", ArtifactType.CHECKPOINT, version="v1")
    mgr.save(src, "model", ArtifactType.CHECKPOINT, version="v3")
    mgr.save(src, "model", ArtifactType.CHECKPOINT, version="v2")
    path = mgr.load("model", ArtifactType.CHECKPOINT)
    assert "v3" in str(path)


# Feature: artifacts-subsystem, Property 3: Round-trip save → load
@given(_VALID_NAME, _ARTIFACT_TYPE, _VERSION_STR)
@settings(max_examples=100)
def test_property_save_load_roundtrip(name: str, artifact_type: ArtifactType, version: str) -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        src = tmp / "src.txt"
        src.write_text("roundtrip")
        mgr = LocalBackend(str(tmp / "arts"), versioning_strategy="manual")
        record = mgr.save(src, name, artifact_type, version=version)
        loaded = mgr.load(name, artifact_type, version=version)
        assert loaded.exists()
        assert loaded == record.path.parent or loaded == record.path
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# LocalBackend — list_artifacts
# ---------------------------------------------------------------------------


def test_list_artifacts_empty_dir_returns_empty(tmp_path: Path) -> None:
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="manual")
    assert mgr.list_artifacts() == []


def test_list_artifacts_returns_all(tmp_path: Path) -> None:
    src = tmp_path / "f.txt"
    src.write_text("x")
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="manual")
    mgr.save(src, "a", ArtifactType.CHECKPOINT, version="v1")
    mgr.save(src, "b", ArtifactType.DATASET, version="v1")
    records = mgr.list_artifacts()
    assert len(records) == 2


def test_list_artifacts_filter_by_type(tmp_path: Path) -> None:
    src = tmp_path / "f.txt"
    src.write_text("x")
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="manual")
    mgr.save(src, "a", ArtifactType.CHECKPOINT, version="v1")
    mgr.save(src, "b", ArtifactType.DATASET, version="v1")
    records = mgr.list_artifacts(artifact_type=ArtifactType.CHECKPOINT)
    assert all(r.artifact_type == ArtifactType.CHECKPOINT for r in records)
    assert len(records) == 1


def test_list_artifacts_sorted_by_created_at(tmp_path: Path) -> None:
    src = tmp_path / "f.txt"
    src.write_text("x")
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="manual")
    mgr.save(src, "a", ArtifactType.CHECKPOINT, version="v1")
    mgr.save(src, "b", ArtifactType.CHECKPOINT, version="v1")
    records = mgr.list_artifacts()
    for i in range(len(records) - 1):
        assert records[i].created_at <= records[i + 1].created_at


# ---------------------------------------------------------------------------
# LocalBackend — delete
# ---------------------------------------------------------------------------


def test_delete_existing_artifact(tmp_path: Path) -> None:
    src = tmp_path / "m.pt"
    src.write_bytes(b"w")
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="manual")
    mgr.save(src, "model", ArtifactType.CHECKPOINT, version="v1")
    mgr.delete("model", ArtifactType.CHECKPOINT, "v1")
    with pytest.raises(ArtifactNotFoundError):
        mgr.load("model", ArtifactType.CHECKPOINT, version="v1")


def test_delete_nonexistent_raises(tmp_path: Path) -> None:
    mgr = LocalBackend(str(tmp_path / "arts"), versioning_strategy="manual")
    with pytest.raises(ArtifactNotFoundError):
        mgr.delete("ghost", ArtifactType.CHECKPOINT, "v1")


# Feature: artifacts-subsystem, Property 13: Round-trip save → delete → load raise error
@given(_VALID_NAME, _ARTIFACT_TYPE, _VERSION_STR)
@settings(max_examples=100)
def test_property_delete_then_load_raises(
    name: str, artifact_type: ArtifactType, version: str
) -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        src = tmp / "src.txt"
        src.write_text("data")
        mgr = LocalBackend(str(tmp / "arts"), versioning_strategy="manual")
        mgr.save(src, name, artifact_type, version=version)
        mgr.delete(name, artifact_type, version)
        with pytest.raises(ArtifactNotFoundError):
            mgr.load(name, artifact_type, version=version)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# RuntimeContext integration
# ---------------------------------------------------------------------------


def test_bootstrap_includes_artifact_manager() -> None:
    from starter.runtime import bootstrap

    ctx = bootstrap(["artifacts.enabled=false"])
    assert ctx.artifact_manager is not None
    assert isinstance(ctx.artifact_manager, NullArtifactManager)
