#!/bin/python3
from jericho.enums.cluster_roles import ClusterRole
from jericho.helpers import (
    load_yaml_file,
    logger_convert,
    get_domain_from_endpoint,
    merge_domains_with_endpoints,
    chunks,
    split_array_by,
    is_not_same_domain,
    get_endpoint,
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


def test_get_domain_from_endpoint():
    assert get_domain_from_endpoint("https://google.com/asd") == "https://google.com"


def test_merge_domains_with_endpoints():
    arr1 = [{"endpoint": "/phpinfo.php"}, {"endpoint": "/test.php"}]
    arr2 = [f"https://{i}" for i in range(0, 20)]
    test = merge_domains_with_endpoints(arr1, arr2)

    assert len(test) == 40
    assert test[0:20] == [f"https://{i}/phpinfo.php" for i in range(0, 20)]
    assert test[20:40] == [f"https://{i}/test.php" for i in range(0, 20)]


def test_chunks():
    chunks_iter = chunks([1, 2, 3, 4], 2)
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


def test_is_not_same_domain_same_domain_return_true():
    assert (
        is_not_same_domain("https://google.com/asdasd", "http://google.com/aaaaa")
        is False
    )


def test_is_not_same_domain_same_domain_return_false():
    assert (
        is_not_same_domain("https://yahoo.com/asdasd", "http://google.com/aaaaa")
        is True
    )


def test_get_endpoint():
    assert get_endpoint("https://google.com/test.php") == "/test.php"
