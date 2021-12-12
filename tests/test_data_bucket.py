#!/bin/python3
import json
from jericho.plugin.data_bucket import DataBucket

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
    assert databucket.get() == []

def test_get_size():
    databucket = DataBucket(100)
    assert databucket.save(('https://google.com', 'content')) == True

    # Serialized input ["https://google.com", "content"] in a list = [["https://google.com", "content"]] which is 35
    assert databucket.get_size() == 35

def test_get_size_is_same_as_get_content_size():
    databucket = DataBucket(100)
    assert databucket.save(('https://google.com', 'content')) == True

    assert len(json.dumps(databucket.get())) == databucket.get_size()