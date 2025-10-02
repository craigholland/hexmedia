from hexmedia.common.strings.splitters import csv_to_list


def test_csv_to_list_none():
    assert csv_to_list(None) == []


def test_csv_to_list_list_input():
    assert csv_to_list([" a ", "b", "", "  "]) == ["a", "b"]


def test_csv_to_list_string_input():
    assert csv_to_list(" a, b ,c ,, d ") == ["a", "b", "c", "d"]
