#!/bin/python3
import time
import threading
import json
from jericho.plugin.cluster import Cluster
from jericho.enums.cluster_response_type import ClusterResponseType


def send_three_messages(cluster):
    time.sleep(2)
    cluster.send_zmq_message(
        json.dumps(
            {
                "workload_uuid": "bah0",
                "endpoint": "https://google0.com",
                "content": "wow0",
            }
        )
    )
    cluster.send_zmq_message(
        json.dumps(
            {
                "workload_uuid": "bah1",
                "endpoint": "https://google1.com",
                "content": "wow1",
            }
        )
    )
    cluster.send_zmq_message(
        json.dumps(
            {
                "workload_uuid": "bah2",
                "endpoint": "https://google2.com",
                "content": "wow2",
            }
        )
    )
    cluster.send_zmq_message(ClusterResponseType.FINISHED.value)


def test_simple_sentence():
    cluster = Cluster(["127.0.0.1"])
    cluster.start_zmq_server()

    x = threading.Thread(target=send_three_messages, args=(cluster,))
    x.start()

    index = 0
    for result in cluster.receive_zmq_message():
        assert result == {
            "workload_uuid": f"bah{index}",
            "endpoint": f"https://google{index}.com",
            "content": f"wow{index}",
        }
        index = index + 1

    x.join()
