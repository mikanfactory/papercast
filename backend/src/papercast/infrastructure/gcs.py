import asyncio
import pathlib
from typing import List

from google.cloud import storage

from papercast.config import GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_STORAGE_BUCKET


def _remove_prefix(filename: pathlib.Path) -> pathlib.Path:
    return filename.relative_to("downloads")


class GCSFileUploadable:
    @classmethod
    def _download_from_gcs(cls, source_file_name: pathlib.Path) -> None:
        destination_key = _remove_prefix(source_file_name)

        storage_client = storage.Client(project=GOOGLE_CLOUD_PROJECT)
        bucket = storage_client.bucket(GOOGLE_CLOUD_STORAGE_BUCKET)
        blob = bucket.blob(str(destination_key))
        blob.download_to_filename(str(source_file_name))

    @classmethod
    async def _bulk_download_from_gcs(cls, source_file_names: List[pathlib.Path]) -> None:
        tasks = [asyncio.to_thread(cls._download_from_gcs, source_file_name) for source_file_name in source_file_names]
        await asyncio.gather(*tasks)

    @classmethod
    def upload_gcs_from_file(cls, source_file_name: pathlib.Path) -> None:
        destination_key = _remove_prefix(source_file_name)
        cls._upload_gcs_from_file(source_file_name, destination_key)

    @classmethod
    def _upload_gcs_from_file(cls, source_file_name: pathlib.Path, destination_key: pathlib.Path) -> None:
        storage_client = storage.Client(project=GOOGLE_CLOUD_PROJECT)
        bucket = storage_client.bucket(GOOGLE_CLOUD_STORAGE_BUCKET)
        blob = bucket.blob(str(destination_key))
        blob.upload_from_filename(str(source_file_name))
