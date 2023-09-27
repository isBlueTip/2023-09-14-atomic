# Добавить обработку более чем трёх файлов
# Добавить флаг игнорирования файла
# Добавить флаг игнорирования эндпоинта
# Добавить копирование папки

import argparse
import asyncio
import base64
import inspect
import os
import shutil
import time
from collections import defaultdict
from ftplib import FTP
from pathlib import Path
from pprint import pprint
from xml.etree import ElementTree

import aiofiles
import aiofiles.os
import aioftp
import aiohttp
import ipdb
import requests

from config import Config
from constants import DESTINATIONS


def init_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("path_1")
    parser.add_argument("path_2")
    parser.add_argument("path_3")
    parser.add_argument("-o", "--override", action="store_true")
    parser.add_argument("-d", "--dry", action="store_true")

    return parser.parse_args()


async def send_to_ftp(src_path: Path, override: bool = False, dry: bool = False) -> None:
    """
    Send a file from src_path to FTP server's root folder.

    Override flag would override an existing file in a root folder.
    Dry mode would suppress actual copying but produce actual-like output.

    :param src_path: source path object
    :param override: flag to overwrite existing file
    :param dry: flag to suppress actual changes in system
    :return:
    """

    async with aioftp.Client.context(Config.FTP_ADDRESS, user=Config.FTP_USER, password=Config.FTP_PASSWORD) as client:
        # Check if the  file is already exists on the server
        if await client.exists(src_path.name) and not override:
            raise SystemExit(f"ERROR: <{src_path.name}> already exists on the FTP server. Try using --override.")
        if not dry:
            await client.upload(src_path)


async def asend_to_owncloud(src_path: Path, url: str, password: str, override: bool = False, dry: bool = False):
    # Parse shared dir id and encode it along with password in base64
    token = url.split("/")[-1]
    credentials = f"{token}:{password}"
    credentials_encoded = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Depth": "1",
        "Authorization": f"Basic {credentials_encoded}",
    }

    # session = requests.Session()
    # resp = session.request('PROPFIND', Config.OWNCLOUD_WEBDAV_ENDPOINT, headers=headers)
    # xml_data = resp.content
    # xml_root = ElementTree.fromstring(xml_data)

    async with aiohttp.ClientSession() as session:
        async with session.request("PROPFIND", Config.OWNCLOUD_WEBDAV_ENDPOINT, headers=headers) as resp:
            print(f"resp.status = {resp.status}")
            content = await resp.read()
            xml_data = content
            xml_root = ElementTree.fromstring(xml_data)
            print(content)

            for elem in xml_root.iter("{DAV:}response"):
                path = elem.find("{DAV:}href").text
                print(f"path = {path}")
                if path.endswith(src_path.name):
                    print(f"The file '{file_name}' exists in the folder.")
                    break

    return
    # print(f"resp.text = {resp.text}")
    # print("")

    #     files = {'file': open(file_path, 'rb')}
    #     # response = requests.post(url, data={'password': Config.OWNCLOUD_PASSWORD})


def send_to_owncloud(src_path, url, password, override: bool = False, dry: bool = False):
    # Parse shared dir id and encode it along with password in base64
    token = url.split("/")[-1]
    credentials = f"{token}:{password}"
    credentials_encoded = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Depth": "1",
        "Authorization": f"Basic {credentials_encoded}",
    }

    session = requests.Session()
    resp = session.request("PROPFIND", Config.OWNCLOUD_WEBDAV_ENDPOINT, headers=headers)
    xml_data = resp.content
    xml_root = ElementTree.fromstring(xml_data)

    for elem in xml_root.iter("{DAV:}response"):
        path = elem.find("{DAV:}href").text
        print(f"path = {path}")
        if path.endswith(src_path.name):
            print(f"The file '{file_name}' exists in the folder.")
            break


async def send_locally(src_path: Path, dst_path: Path, override: bool = False, dry: bool = False) -> None:
    """
    Copy file from src_path to local target_path folder.

    Override flag would override an existing file in a dst_path.
    Dry mode would suppress actual copying but produce actual-like output.

    :param src_path: source path object
    :param dst_path: destination directory path object
    :param override: flag to overwrite existing file
    :param dry: flag to suppress actual changes in system
    :return:
    """

    # Check if the file already exists in the destination folder
    if not dst_path.exists() or override:
        dst_path = dst_path.joinpath(src_path.name)  # Replace target dir with file
        handle_src = await aiofiles.open(src_path, mode="r")
        handle_dst = await aiofiles.open(dst_path, mode="w")

        stat_src = await aiofiles.os.stat(src_path)
        bytes_cnt = stat_src.st_size

        src_descr = handle_src.fileno()
        dst_descr = handle_dst.fileno()

        if not dry:
            await aiofiles.os.sendfile(dst_descr, src_descr, 0, bytes_cnt)

    else:
        raise SystemExit(f"ERROR: <{src_path.name}> already exists in the local target dir. Try using --override.")


async def main():
    # Check if local target dir exists
    if not Path(Config.LOCAL_TARGET_FOLDER).exists():
        raise SystemExit("ERROR: local target directory doesn't exist.")

    args = init_args()

    start = time.perf_counter()

    # Building source files paths
    source_paths = list()
    source_paths.append(Path(args.path_1 + DESTINATIONS["files"][0]["name"]))
    source_paths.append(Path(args.path_2 + DESTINATIONS["files"][1]["name"]))
    source_paths.append(Path(args.path_3 + DESTINATIONS["files"][2]["name"]))

    for i, path in enumerate(source_paths, start=1):
        if not path.exists():
            raise SystemExit(f"ERROR: <file{i}> path doesn't exist.")

    OVERRIDE = args.override
    DRY = args.dry

    destinations = defaultdict(list)
    tasks = list()

    # Building dict with endpoints as keys
    for source_path, file in zip(source_paths, DESTINATIONS["files"]):
        # if "ftp" in file["endpoints"]:  # Copying to FTP
        #     print(f"sending {source_path.name} to ftp asyncronously")
        #     tasks.append(asyncio.create_task(send_to_ftp(source_path, OVERRIDE, DRY)))

        if "owncloud" in file["endpoints"]:
            print(f"sending {source_path.name} to owncloud asyncronously")
            tasks.append(asend_to_owncloud(source_path, Config.OWNCLOUD_URL, Config.OWNCLOUD_PASSWORD, OVERRIDE, DRY))
            # send_to_owncloud(source_path, Config.OWNCLOUD_URL, Config.OWNCLOUD_PASSWORD, OVERRIDE, DRY)

        # if "folder" in file["endpoints"]:
        #     print(f"sending {source_path.name} to local folder asyncronously")
        #     tasks.append(
        #         asyncio.create_task(send_locally(source_path, Path(Config.LOCAL_TARGET_FOLDER), OVERRIDE, DRY))
        #     )

    await asyncio.gather(*tasks)

    # dst_path = dst_path.joinpath(src_path.name)  # Replace target dir with file
    end = time.perf_counter()
    # seconds_elapsed = int(round(end - start, 0))
    seconds_elapsed = end - start
    print(f"SUCCESS: copied {len(destinations)} file(s) in {seconds_elapsed} second(s)")


if __name__ == "__main__":
    asyncio.run(main())
