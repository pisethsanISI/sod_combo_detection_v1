import pytest

from combo_detection.access import (
    build_user_tcode_roles,
    build_user_tcodes,
    expand_role_to_single_roles,
    load_composite_roles,
    load_role_tcodes,
)


def test_expand_role_returns_itself_when_not_composite():
    assert expand_role_to_single_roles("Z_BUYER", {}) == {"Z_BUYER"}


def test_expand_role_resolves_nested_composites():
    composite_children = {"Z_C_OUTER": {"Z_C_INNER"}, "Z_C_INNER": {"Z_BUYER"}}
    assert expand_role_to_single_roles("Z_C_OUTER", composite_children) == {"Z_BUYER"}


def test_expand_role_guards_against_circular_bundle():
    composite_children = {"Z_A": {"Z_B"}, "Z_B": {"Z_A"}}
    result = expand_role_to_single_roles("Z_A", composite_children)
    assert isinstance(result, set)


def test_build_user_tcodes_resolves_composite_role(tmp_path):
    role_tcodes = tmp_path / "role_tcodes.csv"
    role_tcodes.write_text("role_id,tcode\nZ_AP_FULL,FK01\nZ_AP_FULL,F110\n", encoding="utf-8")
    user_roles = tmp_path / "user_roles.csv"
    user_roles.write_text("user_id,role_id\nU1,Z_C_FULL\n", encoding="utf-8")
    composite_roles = tmp_path / "composite_roles.csv"
    composite_roles.write_text("composite_role_id,single_role_id\nZ_C_FULL,Z_AP_FULL\n", encoding="utf-8")

    access = build_user_tcodes(str(role_tcodes), str(user_roles), str(composite_roles))

    assert access["U1"] == {"FK01", "F110"}


def test_build_user_tcode_roles_traces_provenance(tmp_path):
    role_tcodes = tmp_path / "role_tcodes.csv"
    role_tcodes.write_text("role_id,tcode\nZ_AP_FULL,FK01\n", encoding="utf-8")
    user_roles = tmp_path / "user_roles.csv"
    user_roles.write_text("user_id,role_id\nU1,Z_AP_FULL\n", encoding="utf-8")

    user_tcode_roles = build_user_tcode_roles(str(role_tcodes), str(user_roles))

    assert user_tcode_roles["U1"]["FK01"] == {"Z_AP_FULL"}


def test_sample_data_produces_the_expected_demo_user():
    access = build_user_tcodes(
        "data/sample_role_tcodes.csv", "data/sample_user_roles.csv", "data/sample_composite_roles.csv"
    )
    assert access["U1"] == {"FK01", "FK02", "F110"}
    assert access["U2"] == {"FK01"}


def test_load_role_tcodes_raises_clear_error_on_missing_column(tmp_path):
    bad_csv = tmp_path / "role_tcodes.csv"
    bad_csv.write_text("role_id,wrong_column\nZ_AP_FULL,FK01\n", encoding="utf-8")

    with pytest.raises(ValueError, match="tcode"):
        load_role_tcodes(str(bad_csv))


def test_load_composite_roles_raises_clear_error_on_missing_column(tmp_path):
    bad_csv = tmp_path / "composite_roles.csv"
    bad_csv.write_text("composite_role_id,child\nZ_C_FULL,Z_AP_FULL\n", encoding="utf-8")

    with pytest.raises(ValueError, match="single_role_id"):
        load_composite_roles(str(bad_csv))


def test_build_user_tcode_roles_raises_clear_error_on_missing_user_roles_column(tmp_path):
    role_tcodes = tmp_path / "role_tcodes.csv"
    role_tcodes.write_text("role_id,tcode\nZ_AP_FULL,FK01\n", encoding="utf-8")
    bad_user_roles = tmp_path / "user_roles.csv"
    bad_user_roles.write_text("user,role_id\nU1,Z_AP_FULL\n", encoding="utf-8")

    with pytest.raises(ValueError, match="user_id"):
        build_user_tcode_roles(str(role_tcodes), str(bad_user_roles))
