# Добавить обработку более чем трёх файлов
# Добавить флаг игнорирования файла
# Добавить флаг игнорирования эндпоинта
# Добавить копирование папки
# Есть что оптимизировать и куда вносить изменения при увеличении количества копируемых файлов

# Для работы с эндпоинтами выбрал самые популярные и поддерживаемые библиотеки

# TODO Убрать .env и fuxtures с прода. Оставил для более простой проверки тестового

import argparse
import asyncio
import base64
import http
import sys
import time
from pathlib import Path
from xml.etree import ElementTree

import aiohttp
from ipdb import set_trace

from config import Config
from connections import FTPConnection, LocalConnection, OwnCloudConnection
from constants import DESTINATIONS


def init_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("dir_1")
    parser.add_argument("dir_2")
    parser.add_argument("dir_3")
    parser.add_argument("-o", "--override", action="store_true")
    parser.add_argument("-d", "--dry", action="store_true")

    return parser.parse_args()


async def copy_to_owncloud(
    src_path: Path,
    url: str,
    password: str,
    override: bool = False,
    dry: bool = False,
):
    """
    Send a file from src_path to OwnCloud server's root shared folder.

    Override flag would override an existing file in a root folder.
    Dry mode would suppress actual copying but produce actual-like output.

    :param src_path: source path object
    :param url: owncloud shared folder url
    :param password: owncloud password for shared folder
    :param override: flag to overwrite existing file
    :param dry: flag to suppress actual changes in system
    :return:
    """

    print(f"copying <{src_path.name}> to owncloud")

    # Parse shared dir id and encode it along with password in base64
    token = url.split("/")[-1]
    credentials = f"{token}:{password}"
    credentials_encoded = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Depth": "1",
        "Authorization": f"Basic {credentials_encoded}",
        "Content-Type": "text/html",
    }

    async with aiohttp.ClientSession() as session:
        # Check if the file already exists on the server
        async with session.request(
            "PROPFIND", Config.OWNCLOUD_WEBDAV_ENDPOINT, headers=headers
        ) as resp:
            if resp.status != http.HTTPStatus.MULTI_STATUS:
                print(
                    f"ERROR: <{resp.status}> HTTP status when connecting to"
                    " owncloud (<207_MULTI_STATUS> expected)"
                )
                return

            content = await resp.read()
            xml_root = ElementTree.fromstring(content)

            for elem in xml_root.iter("{DAV:}response"):
                path = elem.find("{DAV:}href").text
                if path.endswith(src_path.name) and not override:
                    print(
                        f"ERROR: <{src_path.name}> already exists on the"
                        " OwnCloud server. Try using --override."
                    )
                    return

        # Copy if not dry mode
        if not dry:
            file = open(src_path, "rb").read()
            try:
                resp = await session.put(
                    f"{Config.OWNCLOUD_WEBDAV_ENDPOINT}/{src_path.name}",
                    data=file,
                    headers=headers,
                )
            except Exception as e:
                print(
                    f"ERROR: <{e}> when copying <{src_path.name}> to owncloud"
                )
                return
            if resp.status not in (
                http.HTTPStatus.NO_CONTENT,
                http.HTTPStatus.CREATED,
            ):
                print(
                    f"ERROR: <{resp.status}> HTTP status when copying"
                    f" <{src_path.name}> to owncloud (<201_CREATED> or"
                    " <204_NO_CONTENT> expected)"
                )
                return
        print(f"SUCCESS: <{src_path.name}> copied to owncloud")


async def main():
    assert sys.version_info >= (3, 7), "Python >= 3.7 is required"

    # Check if local target dir exists
    local_dest_path = Path(Config.LOCAL_TARGET_FOLDER)
    if not local_dest_path.exists():
        raise SystemExit("ERROR: local target directory doesn't exist.")

    args = init_args()

    start = time.perf_counter()

    # Building source files paths
    src_paths = list()
    src_paths.append(Path(args.dir_1 + DESTINATIONS["files"][0]["name"]))
    src_paths.append(Path(args.dir_2 + DESTINATIONS["files"][1]["name"]))
    src_paths.append(Path(args.dir_3 + DESTINATIONS["files"][2]["name"]))

    for i, path in enumerate(src_paths, start=1):
        if not path.exists():
            raise SystemExit(f"ERROR: <file{i}> path doesn't exist.")

    override = args.override
    dry = args.dry

    tasks = list()

    local_connection = LocalConnection()
    ftp_connection = FTPConnection(
        Config.FTP_ADDRESS, Config.FTP_USER, Config.FTP_PASSWORD
    )
    owncloud_connection = OwnCloudConnection(
        Config.OWNCLOUD_URL, None, Config.OWNCLOUD_PASSWORD
    )

    # Create copying tasks
    for src_path, file in zip(src_paths, DESTINATIONS["files"]):
        if "ftp" in file["endpoints"]:  # Copying to FTP
            tasks.append(
                asyncio.create_task(
                    ftp_connection.copy_files(src_path, None, override, dry)
                )
            )

        if "owncloud" in file["endpoints"]:  # Copying to OwnCloud
            # tasks.append(copy_to_owncloud(src_path, Config.OWNCLOUD_URL, Config.OWNCLOUD_PASSWORD, override, dry))
            tasks.append(
                owncloud_connection.copy_files(src_path, None, override, dry)
            )

        if "folder" in file["endpoints"]:  # Copying locally
            tasks.append(
                asyncio.create_task(
                    local_connection.copy_files(
                        src_path, local_dest_path, override, dry
                    )
                )
            )

    await asyncio.gather(*tasks, return_exceptions=False)

    end = time.perf_counter()
    # seconds_elapsed = int(round(end - start, 0))  # todo
    seconds_elapsed = end - start
    if not dry:
        print(f"\nSUCCESS: copied in {seconds_elapsed} second(s)")


if __name__ == "__main__":
    asyncio.run(main())
