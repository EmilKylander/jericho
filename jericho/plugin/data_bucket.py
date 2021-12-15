import logging
import typing
import json


class DataBucket:
    def __init__(self, max_size: int):
        logging.debug("Setting the data bucket size to %s", max_size)
        self.max_size: int = max_size
        self.bucket_size: int = 0
        self.bucket: typing.List = []

    def save(self, data_to_save: typing.Any) -> bool:
        dict_size: int = len(json.dumps(data_to_save))
        self.bucket_size = self.bucket_size + dict_size

        logging.debug(
            "Saving %s bytes to bucket (%s) max size", dict_size, self.max_size
        )
        self.bucket.append(data_to_save)
        return True

    def get(self) -> typing.List:
        logging.debug("Getting data from the bucket")
        return self.bucket

    def empty(self) -> bool:
        logging.debug("Emptying bucket - current size (%s)", self.bucket_size)
        self.bucket = []
        self.bucket_size = 0
        return True

    def is_empty(self) -> bool:
        logging.debug("Checking if bucket is empty")
        return self.bucket == []

    def is_full(self) -> bool:
        bucket_is_full = self.bucket_size >= self.max_size
        logging.debug("Checking if bucket is full: %s", bucket_is_full)
        return bucket_is_full

    def get_size(self) -> int:
        logging.debug("Getting size of data bucket: %s", self.bucket_size)
        # Get the calculated bucket size = All the object sizes + the len of the json objects minus one
        # (Representing the commas joining the objects + beginning and ending bracket)
        return self.bucket_size + (len(self.bucket) - 1) + 2
