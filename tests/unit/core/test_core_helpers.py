from app.core.ids import new_id
from app.core.time import utc_now_iso


def test_new_id_has_prefix():
    value = new_id("proj")
    assert value.startswith("proj_")
    assert len(value) > len("proj_")


def test_utc_now_iso_has_timezone():
    value = utc_now_iso()
    assert value.endswith("+00:00")
