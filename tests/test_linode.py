#!/bin/python3
import json
import asyncio
from jericho.plugin.linode import Linode
from aioresponses import aioresponses


async def test__analyze_for_errors_response_ok():
    linode = Linode({"token": ""})
    resp = await linode._analyze_for_errors({"response": "ok"})
    assert resp == False


async def test__analyze_for_errors_response_error():
    linode = Linode({"token": ""})
    resp = await linode._analyze_for_errors({"errors": [{"reason": "Invalid Token"}]})
    assert resp == True


def test_create():
    linode = Linode({"token": ""})
    loop = asyncio.new_event_loop()
    with aioresponses() as m:
        m.post(
            "https://api.linode.com/v4/linode/instances",
            status=200,
            body='{"test": "testing"}',
        )

        loop.run_until_complete(linode.create())

        assert len(linode.instances) == 1


def test_get_instances():
    linode = Linode({"token": ""})
    linode.instances = ["123-123-123-123"]
    loop = asyncio.new_event_loop()
    with aioresponses() as m:
        m.get(
            "https://api.linode.com/v4/linode/instances",
            status=200,
            body=json.dumps(
                {
                    "data": [
                        {"label": "jericho_123-123-123-123"},
                        {"label": "not_jericho"},
                    ]
                }
            ),
        )

        responses = loop.run_until_complete(linode.get_instances())

        assert responses == ["jericho_123-123-123-123"]


def test_get_ready():
    linode = Linode({"token": ""})
    linode.instances = ["123-123-123-123", "1234-1234-1234"]
    loop = asyncio.new_event_loop()
    with aioresponses() as m:
        m.get(
            "https://api.linode.com/v4/linode/instances",
            status=200,
            body=json.dumps(
                {
                    "data": [
                        {"label": "jericho_123-123-123-123", "status": "running"},
                        {"label": "jericho_1234-1234-1234", "status": "booting"},
                    ]
                }
            ),
        )

        response = loop.run_until_complete(linode.get_ready())

        assert response == 1


def test_get_delete():
    linode = Linode({"token": ""})
    linode.instances = ["123-123-123-123", "1234-1234-1234"]
    loop = asyncio.new_event_loop()
    with aioresponses() as m:
        m.get(
            "https://api.linode.com/v4/linode/instances",
            status=200,
            body=json.dumps(
                {
                    "data": [
                        {
                            "label": "jericho_123-123-123-123",
                            "status": "running",
                            "id": 1,
                        },
                        {
                            "label": "jericho_1234-1234-1234",
                            "status": "booting",
                            "id": 2,
                        },
                        {"label": "innocent_server", "status": "running", "id": 3},
                    ]
                }
            ),
        )
        m.delete("https://api.linode.com/v4/linode/instances/1", status=200, body="")
        m.delete("https://api.linode.com/v4/linode/instances/2", status=200, body="")

        response = loop.run_until_complete(linode.delete_instances())

        assert response == 2
