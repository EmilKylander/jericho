import logging
import typing
import json
import shutil
import uuid
import os
from zipfile import ZipFile
from os.path import basename

class DataBucket:
    def __init__(self, max_size):
        logging.debug("Setting the data bucket size to %s", max_size)

        if max_size == "ALL":
            _, _, free = shutil.disk_usage("/")
            self.max_size = int(free - (free * (1 - 0.70))) # Could be unreliable to fill the entire disk
        else:
            self.max_size = max_size

        self.bucket_size: int = 0
        self.bucket: typing.List = []
        self.temporary_directory = f'/tmp/{uuid.uuid4()}'

        os.mkdir(self.temporary_directory)

    def save(self, data_to_save: typing.Any) -> bool:
        dict_size: int = len(json.dumps(data_to_save))
        self.bucket_size = self.bucket_size + dict_size

        logging.debug(
            "Saving %s bytes to bucket (%s) max size", dict_size, self.max_size
        )


        safe_name = data_to_save[0].replace("/", "_SLASH_")
        file = open(f"{self.temporary_directory}/{safe_name}", "w", encoding="utf-8")
        file.write(data_to_save[1])
        file.close()

        return True

    def get(self) -> str:
        logging.debug("Getting data from the bucket")
        self._zip_directory(f"{self.temporary_directory}.zip", self.temporary_directory)
        return f"{self.temporary_directory}.zip"

    def get_uuid(self) -> str:
        logging.debug("Getting uuid from the bucket")
        return self.temporary_directory.replace("/tmp/", "")

    def empty(self) -> bool:
        logging.debug("Emptying bucket - current size (%s)", self.bucket_size)
        shutil.rmtree(self.temporary_directory)
        self.temporary_directory = f'/tmp/{uuid.uuid4()}'
        os.mkdir(self.temporary_directory)

        return True

    def is_empty(self) -> bool:
        logging.debug("Checking if bucket is empty")
        return len(os.listdir(self.temporary_directory)) == 0

    def is_full(self) -> bool:
        bucket_is_full = self.get_size() >= self.max_size

        logging.debug("Checking if bucket is full: %s", bucket_is_full)
        return bucket_is_full

    def get_size(self) -> int:
        total_size = 0
        for dirpath, _, filenames in os.walk(self.temporary_directory):
            for file in filenames:
                file_path = os.path.join(dirpath, file)
                if not os.path.islink(file_path):
                    total_size += os.path.getsize(file_path)

        return total_size

    def _zip_directory(self, filename: str, dirname: str):
        with ZipFile(filename, 'w') as zipObj:
            for folderName, _, filenames in os.walk(dirname):
                for filename in filenames:
                    filePath = os.path.join(folderName, filename)
                    zipObj.write(filePath, basename(filePath))