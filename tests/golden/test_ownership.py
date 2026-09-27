import importlib.util

import pytest

from common import REPO_ROOT

_spec = importlib.util.spec_from_file_location("check_ownership", REPO_ROOT / "scripts/check_ownership.py")
co = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(co)

ROADMAP, FEATURES = co.load_specs(REPO_ROOT)


def test_committed_specs_lint_clean():
    assert co.lint_specs(ROADMAP, FEATURES) == []


@pytest.mark.parametrize("frozen", ROADMAP["frozen_paths"])
def test_every_frozen_path_exists(frozen):
    parent, _, stem = frozen.rstrip("/").rpartition("/")
    base = REPO_ROOT / parent
    assert any(p.name.startswith(stem) for p in base.iterdir()), frozen


def test_roadmap_parsed():
    assert "web/lib/types.ts" in ROADMAP["frozen_paths"]
    assert ROADMAP["contract_owner"] == "technical-lead"
    assert FEATURES["F05"][0]["owns"] == ["web/app/page.tsx", "web/app/map/", "web/components/map/", "web/components/list/"]
    assert FEATURES["F00"][0]["bootstrap"] is True


@pytest.mark.parametrize("title,path,ok", [
    ("[F05] Map + ranked list", "pipeline/x.py", False),
    ("[F05] Map + ranked list", "web/components/map/a.tsx", True),
    ("[F05] part 1/2", "changes/F05.md", True),
    ("[F05] Map", "changes/F06.md", False),
    ("[F05] Map", "specs/decisions/F05-tiles.md", True),
    ("[F05] Map", "specs/features/F05-map-list/spec.md", True),
    ("[F05] Map", "specs/features/F06-atlas-api/spec.md", False),
    ("[F05] Map", "web/lib/types.ts", False),
    ("[FIX-F05] list crash", "web/components/list/Row.tsx", True),
    ("[C1] add optional field", "schemas/match.schema.json", True),
    ("[C1] add optional field", "web/components/map/a.tsx", False),
    ("[C2] spec fix", "specs/roadmap.md", True),
    ("[F00] Bootstrap", "anything/at/all.txt", True),
])
def test_title_rules(title, path, ok):
    assert (co.violations(title, [path], ROADMAP, FEATURES) == []) is ok


def test_revert_only_touches_reverted_files():
    files = ["web/components/map/a.tsx"]
    assert co.violations("[REVERT-abc1234] x", files, ROADMAP, FEATURES, revert_files=files) == []
    assert co.violations("[REVERT-abc1234] x", ["web/lib/data.ts"], ROADMAP, FEATURES, revert_files=files) != []


def test_unknown_prefix_rejected():
    with pytest.raises(ValueError):
        co.violations("Fix stuff", ["a"], ROADMAP, FEATURES)
    with pytest.raises(ValueError):
        co.violations("[F99] nope", ["a"], ROADMAP, FEATURES)


def test_lint_catches_prefix_overlap_and_bad_dep():
    features = {
        "F1": [{"id": "F1", "owns": ["web/app/"], "depends_on": [], "_path": "a"}],
        "F2": [{"id": "F2", "owns": ["web/app/x/"], "depends_on": ["F9"], "_path": "b"}],
        "F3": [{"id": "F3", "owns": ["schemas/extra"], "depends_on": [], "_path": "c"}],
    }
    errs = co.lint_specs({"frozen_paths": ["schemas/"]}, features)
    assert any("F1" in e and "F2" in e for e in errs)
    assert any("F9" in e for e in errs)
    assert any("frozen" in e for e in errs)


def test_front_matter_parser():
    fm = co.front_matter('---\nid: F1\nowns: [a/, b]   # note\nflag: true\nlist:\n  - x\n  - "y#z"\nmap:\n  k: v\n---\nbody')
    assert fm == {"id": "F1", "owns": ["a/", "b"], "flag": True, "list": ["x", "y#z"], "map": []}
