#!/bin/python3
import types
from jericho.enums.cluster_roles import ClusterRole
from jericho.helpers import (
    load_yaml_file,
    logger_convert,
    add_missing_schemes_to_domain_list,
    get_domain_from_endpoint,
    parse_cluster_settings,
    merge_array_to_iterator,
    _chunks,
    split_array_by,
)


def test_load_yaml_file_not_exists():
    assert load_yaml_file("config/configuration.sample.yaaaml") == {}


def test_load_yaml_real_yaml():
    assert load_yaml_file("tests/assets/yml/test.yml") == {"test": "testing"}


def test_load_yaml_not_real_yaml():
    assert load_yaml_file("tests/assets/yml/not_yaml.yml") == {}


def test_logger_convert_debug():
    assert logger_convert("debug") == 10


def test_logger_convert_info():
    assert logger_convert("info") == 20


def test_logger_convert_warning():
    assert logger_convert("warn") == 30


def test_logger_convert_error():
    assert logger_convert("error") == 40


def test_logger_convert_fatal():
    assert logger_convert("fatal") == 50


def test_logger_convert_critical():
    assert logger_convert("critical") == 50


def test_add_missing_schemes_to_domain_list_no_scheme():
    assert add_missing_schemes_to_domain_list(["127.0.0.1"]) == [
        "https://127.0.0.1",
        "http://127.0.0.1",
    ]


def test_add_missing_schemes_to_domain_list_with_scheme():
    assert add_missing_schemes_to_domain_list(["http://127.0.0.1"], True) == [
        "https://127.0.0.1",
        "http://127.0.0.1",
    ]


def test_add_missing_schemes_to_domain_list_with_scheme_multiple():
    dup_array = ["http://127.0.0.1", "http://127.0.0.1"]
    assert add_missing_schemes_to_domain_list(dup_array, True) == [
        "https://127.0.0.1",
        "http://127.0.0.1",
    ]

def test_add_missing_schemes_to_domain_list_with_scheme_no_double():
    assert add_missing_schemes_to_domain_list(["http://127.0.0.1"]) == [
        "http://127.0.0.1",
    ]


def test_add_missing_schemes_to_domain_list_with_scheme_multiple_no_double():
    dup_array = ["http://127.0.0.1", "http://127.0.0.1"]
    assert add_missing_schemes_to_domain_list(dup_array) == [
        "http://127.0.0.1",
    ]


def test_get_domain_from_endpoint():
    assert get_domain_from_endpoint("https://google.com/asd") == "https://google.com"


def test_parse_cluster_settings_replica():
    assert parse_cluster_settings(1, 2) == ClusterRole.REPLICA


def test_parse_cluster_settings_source():
    assert parse_cluster_settings(0, 2) == ClusterRole.SOURCE


def test_parse_cluster_settings_no_role():
    assert parse_cluster_settings(0, 1) == ClusterRole.DISABLED


def test_merge_array_to_iterator():
    arr1 = [{"endpoint": "/phpinfo.php"}, {"endpoint": "/test.php"}]
    arr2 = [f"https://{i}" for i in range(0, 200)]
    test = merge_array_to_iterator(arr1, arr2, domains_batch_size=100)

    i = 0
    for x in test:
        if i == 0:
            assert len(x) == 100
            assert x == [f"https://{i}/phpinfo.php" for i in range(0, 100)]

        if i == 1:
            assert len(x) == 100
            assert x == [f"https://{i}/phpinfo.php" for i in range(100, 200)]

        if i == 2:
            assert len(x) == 100
            assert x == [f"https://{i}/test.php" for i in range(0, 100)]

        if i == 3:
            assert len(x) == 100
            assert x == [f"https://{i}/test.php" for i in range(100, 200)]

        i = i + 1

    assert i == 4


def test__chunks():
    chunks_iter = _chunks([1, 2, 3, 4], 2)
    first = last = next(chunks_iter, "defaultvalue")
    for last in chunks_iter:
        pass
    assert first == [1, 2]
    assert last == [3, 4]


def test_split_array_by_even():
    assert split_array_by([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_split_array_by_uneven():
    assert split_array_by([1, 2, 3, 4, 5], 2) == [[1, 2, 3], [4, 5]]


def test_split_array_by_uneven_larger_list():
    assert split_array_by([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], 2) == [
        [1, 2, 3, 4, 5, 6],
        [7, 8, 9, 10, 11],
    ]


def test_split_array_by_uneven_larger_list_uneven_parts():
    assert split_array_by([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], 3) == [
        [1, 2, 3, 4],
        [5, 6, 7, 8],
        [9, 10, 11],
    ]
