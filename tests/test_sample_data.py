import os

from combo_detection.sample_data import any_sample_data_paths, is_sample_data_path

PROJECT_ROOT = os.path.abspath(".")


def test_is_sample_data_path_true_for_bundled_sample_csv():
    assert is_sample_data_path("data/sample_role_tcodes.csv", PROJECT_ROOT)
    assert is_sample_data_path("data/sample_user_roles.csv", PROJECT_ROOT)
    assert is_sample_data_path("data/sample_composite_roles.csv", PROJECT_ROOT)


def test_is_sample_data_path_true_for_absolute_form_of_the_same_file():
    absolute = os.path.join(PROJECT_ROOT, "data", "sample_role_tcodes.csv")
    assert is_sample_data_path(absolute, PROJECT_ROOT)


def test_is_sample_data_path_false_for_a_real_data_csv():
    assert not is_sample_data_path("../SOD_Detection/data/from_manual_export/role_tcodes.csv", PROJECT_ROOT)


def test_is_sample_data_path_false_for_empty_or_none():
    assert not is_sample_data_path("", PROJECT_ROOT)
    assert not is_sample_data_path(None, PROJECT_ROOT)


def test_is_sample_data_path_false_for_a_similarly_named_but_different_file():
    assert not is_sample_data_path("data/sample_role_tcodes_v2.csv", PROJECT_ROOT)


def test_any_sample_data_paths_true_if_any_one_matches():
    assert any_sample_data_paths(
        ["real_export/role_tcodes.csv", "data/sample_user_roles.csv", ""],
        PROJECT_ROOT,
    )


def test_any_sample_data_paths_false_when_none_match():
    assert not any_sample_data_paths(
        ["real_export/role_tcodes.csv", "real_export/user_roles.csv", ""],
        PROJECT_ROOT,
    )
