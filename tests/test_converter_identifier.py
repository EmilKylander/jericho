import pytest
import unittest
from jericho.converters.identifier import Identifier


def test_check_successful_conversion():
    a = Identifier()

    result = a.run(
        "123.123.132.123",
        "https://google.com",
        200,
        {"test": "aaa"},
        "<b>my content here</b><title>testing</title><a href='tel:+46234234'>aa</a><a href='mailto:test@test.com'>asd</a><a href='https://yahoo.com'>asd</a><script>ga('create', 'trackingcode', 'auto');</script><meta name='description' content='desc'><meta name='generator' content='ametys'>",
    )

    assert result["headers"] == {"test": "aaa"}
    assert result["domain"] == "https://google.com"
    assert result["title"] == "testing"
    assert result["description"] == "desc"
    assert result["google_tracking_code"] == "trackingcode"
    assert result["text_content"] == "my content here testingaaasdasd"
    assert result["bytes"] == 281
    assert result["emails"] == ["test@test.com"]
    assert result["phones"] == ["+46234234"]
    assert result["domains_found"] == ["https://yahoo.com"]

    for technology in result["tech"]:
        if technology["technology"] == "Ametys":
            assert technology == {
                "technology": "Ametys",
                "version": "",
                "theme": "",
                "plugins": "",
            }

        if technology["technology"] == "Java":
            assert technology == {
                "technology": "Java",
                "version": "",
                "theme": "",
                "plugins": "",
            }


def test_check_successful_conversion_with_version():
    a = Identifier()

    result = a.run(
        "123.123.132.123",
        "https://google.com",
        200,
        {"test": "aaa"},
        "<b>my content here</b><title>testing</title><a href='tel:+46234234'>aa</a><a href='mailto:test@test.com'>asd</a><a href='https://yahoo.com'>asd</a><script>ga('create', 'trackingcode', 'auto');</script><meta name='description' content='desc'><meta name='generator' content='Wordpress 1.2.3'>",
    )

    assert result["headers"] == {"test": "aaa"}
    assert result["domain"] == "https://google.com"
    assert result["title"] == "testing"
    assert result["description"] == "desc"
    assert result["google_tracking_code"] == "trackingcode"
    assert result["text_content"] == "my content here testingaaasdasd"
    assert result["bytes"] == 290
    assert result["emails"] == ["test@test.com"]
    assert result["phones"] == ["+46234234"]
    assert result["domains_found"] == ["https://yahoo.com"]
    assert len(result["tech"]) == 3

    for technology in result["tech"]:
        if technology["technology"] == "Wordpress":
            assert technology == {
                "technology": "Wordpress",
                "version": "1.2.3",
                "theme": "",
                "plugins": "",
            }

        if technology["technology"] == "PHP":
            assert technology == {
                "technology": "PHP",
                "version": "",
                "theme": "",
                "plugins": "",
            }

        if technology["technology"] == "MySQL":
            assert technology == {
                "technology": "MySQL",
                "version": "",
                "theme": "",
                "plugins": "",
            }
