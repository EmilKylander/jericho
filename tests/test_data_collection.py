#!/bin/python3
from jericho.plugin.data_collection import DataBucket


def test_save_data_to_bucket():
    databucket = DataBucket(100)
    assert databucket.save(('https://google.com', 'content')) == True
    assert databucket.is_full() == False

def test_emptying_bucket():
    databucket = DataBucket(100)
    assert databucket.save(('https://google.com', 'content')) == True
    assert databucket.empty()
    assert databucket.is_empty() == True
    assert databucket.is_full() == False

def test_get_size():
    databucket = DataBucket(100)
    assert databucket.save(('https://google.com', 'content')) == True
    assert databucket.get_size() == 88
