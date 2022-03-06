#!/bin/python3
import os
from jericho.plugin.data_bucket import DataBucket


def test_save_data_to_bucket():
    databucket = DataBucket(100)
    assert databucket.save(("https://google.com", "content")) == True
    assert databucket.is_full() == False


def test_emptying_bucket():
    databucket = DataBucket(100)
    assert databucket.save(("https://google.com", "content")) == True
    assert databucket.empty()
    assert databucket.is_empty() == True
    assert databucket.is_full() == False


def test_get_size():
    databucket = DataBucket(100)
    assert databucket.save(("https://google.com", "content")) == True

    assert databucket.get_size() == 7

def test_content_is_ok():
    databucket = DataBucket(100)
    assert databucket.save(("https://google.com", "content")) == True

    f = open(f"{databucket.get().replace('.zip', '')}/https:_SLASH__SLASH_google.com", "r")
    assert f.read() == "content"

def test_zip_file_exist():
    databucket = DataBucket(100)
    assert databucket.save(("https://google.com", "content")) == True
    assert os.path.isfile(databucket.get()) == True