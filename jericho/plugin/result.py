#!/bin/python3
import logging
import asyncio
import uuid
from jericho.plugin.result_is_relevant import ResultRelevant
from jericho.plugin.notifications import Notifications
from jericho.enums.cluster_roles import ClusterRole
from jericho.repositories.result_lookup import ResultLookup


class Result:
    def __init__(
        self,
        result_relevant: ResultRelevant,
        notifications_configuration: dict,
        notifications: Notifications,
        cluster_role: ClusterRole,
        result_lookup: ResultLookup,
        workload_uuid: uuid.uuid4,
    ):
        self.result_relevant = result_relevant
        self.notifications_configuration = notifications_configuration
        self.notifications = notifications
        self.result_lookup = result_lookup
        self.cluster_role = cluster_role
        self.workload_uuid = workload_uuid

    def process(self, url: str, html: str, endpoints) -> bool:
        if not self.result_relevant.check(url, html, endpoints):
            return False

        if self.notifications:
            logging.debug("Sending the notifications..")
            asyncio.run(self.notifications.run_all(url))

        logging.debug("Saving result..")
        self.result_lookup.save(self.workload_uuid, url, html)
