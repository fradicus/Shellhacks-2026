"""C28 consumer boundaries with synthetic producer output, never fixture location approval."""

import shutil
import sys
from copy import deepcopy
from types import ModuleType

import pytest

from common import REPO_ROOT, write_json
from national import load as loader
from national.build import OUTPUTS, load_snapshot, validate_snapshot_values

ACTIVE = "data/expansion/mid-atlantic/releases/active.json"


@pytest.fixture
def root(tmp_path):
    target = tmp_path / "data/national"
    target.mkdir(parents=True)
    for name in OUTPUTS:
        shutil.copyfile(REPO_ROOT / "data/national" / f"{name}.json", target / f"{name}.json")
    # Keep the real previously approved New England overlay in the integration boundary.
    target = tmp_path / "data/expansion/releases/active.json"
    target.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / "data/expansion/releases/active.json", target)
    return tmp_path


def install_hook(monkeypatch, root, module_name, path, hook):
    write_json(root / path, {})
    module = ModuleType(module_name)
    module.apply_release = hook
    monkeypatch.setitem(sys.modules, module_name, module)


def addition(snapshot, prefix):
    """One synthetic unlocated source/project, with valid national source-hash binding."""
    snapshot = deepcopy(snapshot)
    project = deepcopy(snapshot["projects"][0])
    source = deepcopy(next(s for s in snapshot["sources"] if s["_id"] == project["source_id"]))
    source.update(_id=f"{prefix}:synthetic", project_count=1)
    project.update(_id=f"{prefix}:synthetic:1", source_id=source["_id"], native_id="synthetic1",
                   center=None, location_review="unlocated", states=["36"])
    project.pop("location_verification", None)
    snapshot["sources"].append(source)
    snapshot["projects"].append(project)
    snapshot["coverage"][prefix.replace("-", "_")] = {"release_id": f"{prefix}-synthetic", "new_projects": 1}
    return snapshot


def test_only_fixed_active_path_imports_mid_atlantic(root, monkeypatch):
    baseline = load_snapshot(root)
    # Importing an unavailable producer is forbidden until its activation file exists.
    monkeypatch.setitem(sys.modules, "expansion.mid_atlantic", None)
    write_json(root / "data/expansion/mid-atlantic/batches/active.json", {"invalid": "candidate"})
    assert load_snapshot(root) == baseline
    write_json(root / ACTIVE, {})
    with pytest.raises(ModuleNotFoundError):
        load_snapshot(root)


def test_mid_atlantic_follows_previous_producers_and_preserves_their_records(root, monkeypatch):
    install_hook(monkeypatch, root, "southeast.publish", "data/southeast/releases/active.json",
                 lambda snapshot, root: addition(snapshot, "southeast"))
    baseline = load_snapshot(root)
    before = {p: p.read_bytes() for p in (root / "data/national").iterdir()}

    def apply(snapshot, received_root):
        assert received_root == root and snapshot == baseline
        assert validate_snapshot_values(snapshot) == []
        return addition(snapshot, "mid-atlantic")

    install_hook(monkeypatch, root, "expansion.mid_atlantic", ACTIVE, apply)
    result = load_snapshot(root)
    assert load_snapshot(root) == result
    assert validate_snapshot_values(result) == []
    assert result["projects"][:-1] == baseline["projects"]
    assert result["sources"][:-1] == baseline["sources"]
    for name in ("expansion", "southeast"):
        assert result["coverage"][name] == baseline["coverage"][name]
    assert result["coverage"]["mid_atlantic"]["new_projects"] == 1
    assert result["coverage"]["projects_total"] == baseline["coverage"]["projects_total"] + 1
    assert result["coverage"]["located_count"] == baseline["coverage"]["located_count"] == 414
    new_source = next(s for s in result["coverage"]["sources"] if s["source_id"] == "mid-atlantic:synthetic")
    assert new_source["project_count"] == 1 and new_source["located_count"] == 0
    assert before == {p: p.read_bytes() for p in before}


@pytest.mark.parametrize("failure", ["release", "assembled"])
def test_bad_mid_atlantic_fails_before_database_staging(root, monkeypatch, failure):
    def apply(snapshot, root):
        if failure == "release":
            raise ValueError("synthetic invalid Mid-Atlantic release")
        snapshot = addition(snapshot, "mid-atlantic")
        snapshot["projects"][-1]["evidence"]["source_sha256"] = "f" * 64
        return snapshot

    install_hook(monkeypatch, root, "expansion.mid_atlantic", ACTIVE, apply)
    monkeypatch.setattr(loader, "REPO_ROOT", root)
    monkeypatch.setattr(loader, "dataset_id", lambda: pytest.fail("invalid assembly must fail before dataset staging"))
    assert loader.main() == 1
