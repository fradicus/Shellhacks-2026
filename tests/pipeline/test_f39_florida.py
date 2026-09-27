"""Source completeness and identity safety checks, using explicit synthetic inputs."""
from copy import deepcopy

import pytest

from southeast.florida import parse_index, reconcile


INDEX = '''<table><tr><td><a href="/fixture">Fixture line</a></td>
<td>TA01-01</td><td>Fixture utility<br>and partner</td></tr></table>'''


def test_index_preserves_licensee_and_rejects_duplicates():
    row = parse_index(INDEX)[0]
    assert row["licensee_raw"] == "Fixture utility and partner"
    assert row["project_urls"] == ["https://floridadep.gov/fixture"]
    with pytest.raises(ValueError, match="duplicate"):
        parse_index(INDEX + INDEX)
    with pytest.raises(ValueError, match="missing"):
        parse_index("<html>No records</html>")


def test_gis_identity_reconciliation_is_not_project_or_location_approval():
    gis = {"features": [{"attributes": {"OBJECTID": i, "CERTIFICATION": "TA01-01"}} for i in [1, 2]]}
    ids = {"objectIdFieldName": "OBJECTID", "objectIds": [1, 2]}
    result = reconcile(parse_index(INDEX), gis, ids)
    assert result["gis_rows"] == 2
    assert result["gis_unique_certification_ids"] == 1
    assert result["publication_eligible"] is False
    assert all(r["center"] is None for r in result["observations"])
    assert result["new_confirmed_points"] == 0
    for bad in [dict(gis, exceededTransferLimit=True), {"features": gis["features"][:1]},
                {"features": [gis["features"][0], gis["features"][0]]}]:
        with pytest.raises(ValueError):
            reconcile(parse_index(INDEX), bad, ids)
    bad_ids = deepcopy(ids)
    bad_ids["objectIds"] = [1, 1, 2]
    with pytest.raises(ValueError):
        reconcile(parse_index(INDEX), gis, bad_ids)
