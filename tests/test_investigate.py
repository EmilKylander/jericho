#!/bin/python3
from jericho.plugin.investigate import Investigate


def test_is_git_config_html():
    bogus = open("tests/assets/branch.io.html").read()
    investigate = Investigate()
    assert investigate.run("http://get.venmo.com/.git/config", bogus, "TEXT") is False


def test_is_html_sample_xml():
    bogus = open("tests/assets/sample.html").read()
    investigate = Investigate()
    assert (
        investigate.run(
            "https://radio1nodigtuit-supernova.events.vrt.be/wp-includes/wlwmanifest.xml",
            bogus,
            "XML",
        )
        is False
    )


def test_ignore_taobao_403_page():
    investigate = Investigate()
    assert (
        investigate.run(
            "http://chenghuigy.cn.alibaba.com/phptest.php",
            '<a id="a-link" href="https://market.m.taobao.com/app/bsop-static/bsop-punish-test-webapp/deny_pc.html?uuid=9d0eba55297bd7732b1c617634fa9777&action=deny"></a> <script>document.getElementById("a-link").click();</script>',
            "TEXT",
        )
        == False
    )


def test_ignore_ok_string_response():
    investigate = Investigate()
    assert (
        investigate.run("http://chenghuigy.cn.alibaba.com/phptest.php", "ok", "")
        is False
    )


def test_ignore_uppercase_ok_string_response():
    investigate = Investigate()
    assert (
        investigate.run("http://chenghuigy.cn.alibaba.com/phptest.php", "OK", "")
        is False
    )


def test_ignore_empty_string_response():
    investigate = Investigate()
    assert (
        investigate.run("http://chenghuigy.cn.alibaba.com/phptest.php", "", "") is False
    )


def test_ignore_empty_json_response():
    investigate = Investigate()
    assert (
        investigate.run("http://chenghuigy.cn.alibaba.com/phptest.php", "{}", "")
        is False
    )
