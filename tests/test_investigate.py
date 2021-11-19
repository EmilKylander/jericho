#!/bin/python3
from jericho.plugin.investigate import Investigate


class MockEndpointsLookup:
    def get(self):
        return [
            {"endpoint": "/.babelrc", "pattern": "TEXT"},
            {"endpoint": "/.git/config", "pattern": "TEXT"},
            {"endpoint": "/config", "pattern": "TEXT"},
            {"endpoint": "/wp-includes/wlwmanifest.xml", "pattern": "XML"},
        ]


def test_is_git_config_html():
    bogus = open("tests/assets/branch.io.html").read()
    endpoints_lookup = MockEndpointsLookup()
    investigate = Investigate(endpoints_lookup)
    assert investigate.run("http://get.venmo.com/.git/config", bogus) is False


def test_is_html_sample_xml():
    bogus = open("tests/assets/sample.html").read()
    endpoints_lookup = MockEndpointsLookup()
    investigate = Investigate(endpoints_lookup)
    assert (
        investigate.run(
            "https://radio1nodigtuit-supernova.events.vrt.be/wp-includes/wlwmanifest.xml",
            bogus,
        )
        is False
    )


def test_ignore_taobao_403_page():
    endpoints_lookup = MockEndpointsLookup()
    investigate = Investigate(endpoints_lookup)
    assert (
        investigate.run(
            "http://chenghuigy.cn.alibaba.com/phptest.php",
            '<a id="a-link" href="https://market.m.taobao.com/app/bsop-static/bsop-punish-test-webapp/deny_pc.html?uuid=9d0eba55297bd7732b1c617634fa9777&action=deny"></a> <script>document.getElementById("a-link").click();</script>',
        )
        == False
    )


def test_ignore_ok_string_response():
    endpoints_lookup = MockEndpointsLookup()
    investigate = Investigate(endpoints_lookup)
    assert (
        investigate.run("http://chenghuigy.cn.alibaba.com/phptest.php", "ok") is False
    )


def test_ignore_uppercase_ok_string_response():
    endpoints_lookup = MockEndpointsLookup()
    investigate = Investigate(endpoints_lookup)
    assert (
        investigate.run("http://chenghuigy.cn.alibaba.com/phptest.php", "OK") is False
    )


def test_ignore_empty_string_response():
    endpoints_lookup = MockEndpointsLookup()
    investigate = Investigate(endpoints_lookup)
    assert investigate.run("http://chenghuigy.cn.alibaba.com/phptest.php", "") is False


def test_ignore_empty_json_response():
    endpoints_lookup = MockEndpointsLookup()
    investigate = Investigate(endpoints_lookup)
    assert (
        investigate.run("http://chenghuigy.cn.alibaba.com/phptest.php", "{}") is False
    )
