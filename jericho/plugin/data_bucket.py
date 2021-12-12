import logging
from sys import getsizeof


class DataBucket:
    def __init__(self, max_size):
        logging.debug(f"Setting the data bucket size to {max_size}")
        self.max_size = max_size
        self.bucket = []

    def save(self, data_to_save: tuple):
        logging.info(f"Saving {getsizeof(data_to_save)} bytes to bucket ({getsizeof(self.bucket)} total size)")
        self.bucket.append(data_to_save)
        return True

    def get(self):
        logging.debug("Getting data from the bucket")
        return self.bucket

    def empty(self):
        logging.debug("Emptying bucket")
        self.bucket = []
        return True

    def is_empty(self):
        logging.debug("Checking if bucket is empty")
        return self.bucket == []

    def is_full(self):
        bucket_is_full = getsizeof(self.bucket) >= self.max_size
        logging.debug(f"Checking if bucket is full: {bucket_is_full}")
        return bucket_is_full

    def get_size(self):
        size = getsizeof(self.bucket)
        logging.debug(f"Getting size of data bucket: {size}")
        return size
