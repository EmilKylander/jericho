#!/bin/python3
from jericho.plugin.diff import Diff


def test_simple_sentence():
    diff = Diff()
    assert diff.check("hello there", "hello ther") == 9


def test_different_sentence():
    diff = Diff()
    assert diff.check("hello there", "see ya along") == 83


def test_different_html():
    diff = Diff()

    f = open("tests/assets/nutanix.html", "r")
    bogus = f.read()

    f = open("tests/assets/nutanix1.html", "r")
    bogus1 = f.read()

    assert diff.check(bogus, bogus1) == 0


def test_different_html_vrt():
    diff = Diff()
    f = open("tests/assets/marconi.lab.vrt.be1.html", "r")
    bogus = f.read()

    f = open("tests/assets/marconi.lab.vrt.be2.html", "r")
    bogus1 = f.read()

    assert diff.check(bogus, bogus1) == 1
