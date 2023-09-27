# Добавить обработку более чем трёх файлов
# Добавить флаг игнорирования файла
# Добавить флаг игнорирования эндпоинта
# Добавить копирование папки

import argparse
import asyncio
import base64
import http
import time
from pathlib import Path
from xml.etree import ElementTree

import aiofiles
import aiofiles.os
import aioftp
import aiohttp

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


async def copy_to_ftp(
        src_path: Path,
        url: str,
        login: str,
        password: str,
        override: bool = False,
        dry: bool = False
) -> None:
    """
    Send a file from src_path to FTP server's root folder.

    Override flag would override an existing file in a root folder.
    Dry mode would suppress actual copying but produce actual-like output.

    :param src_path: source path object
    :param url: FTP server url
    :param login: FTP login
    :param password: FTP password
    :param override: flag to overwrite existing file
    :param dry: flag to suppress actual changes in system
    :return:
    """

    print(f"copying {src_path.name} to ftp")

    async with aioftp.Client.context(url, user=login, password=password) as client:
        # Check if the file already exists on the server
        if await client.exists(src_path.name) and not override:
            raise SystemExit(f"ERROR: <{src_path.name}> already exists on the FTP server. Try using --override.")
        if not dry:
            await client.upload(src_path)
            print(f"{src_path.name} copied to ftp")


async def copy_to_owncloud(src_path: Path, url: str, password: str, override: bool = False, dry: bool = False):
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

    print(f"copying {src_path.name} to owncloud")

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
        async with session.request("PROPFIND", Config.OWNCLOUD_WEBDAV_ENDPOINT, headers=headers) as resp:
            if resp.status != http.HTTPStatus.MULTI_STATUS:
                print(f"ERROR: <{resp.status}> HTTP status when connecting to owncloud (<207_MULTI_STATUS> expected)")
                return
            content = await resp.read()
            xml_root = ElementTree.fromstring(content)

            for elem in xml_root.iter("{DAV:}response"):
                path = elem.find("{DAV:}href").text
                if path.endswith(src_path.name) and not override:
                    raise SystemExit(
                        f"ERROR: <{src_path.name}> already exists on the OwnCloud server. Try using --override."
                    )

        file = open(src_path, "rb").read()
        if not dry:
            resp = await session.put(Config.OWNCLOUD_WEBDAV_ENDPOINT + f"/{src_path.name}", data=file, headers=headers)
            if resp.status not in (http.HTTPStatus.NO_CONTENT, http.HTTPStatus.CREATED):
                print(
                    f"ERROR: <{resp.status}> HTTP status when copying {src_path.name} to owncloud (<201_CREATED> or"
                    " <204_NO_CONTENT> expected)"
                )
            else:
                print(f"{src_path.name} copied to owncloud")


async def copy_locally(src_path: Path, dst_path: Path, override: bool = False, dry: bool = False) -> None:
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

    print(f"copying {src_path.name} to {dst_path.resolve()}")

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
            print(f"{src_path.name} copied to {dst_path.resolve()}")

    else:
        raise SystemExit(f"ERROR: <{src_path.name}> already exists in the local target dir. Try using --override.")


async def main():
    # Check if local target dir exists
    local_dest_path = Path(Config.LOCAL_TARGET_FOLDER)
    if not local_dest_path.exists():
        raise SystemExit("ERROR: local target directory doesn't exist.")

    args = init_args()

    start = time.perf_counter()

    # Building source files paths
    src_paths = list()
    src_paths.append(Path(args.path_1 + DESTINATIONS["files"][0]["name"]))
    src_paths.append(Path(args.path_2 + DESTINATIONS["files"][1]["name"]))
    src_paths.append(Path(args.path_3 + DESTINATIONS["files"][2]["name"]))

    for i, path in enumerate(src_paths, start=1):
        if not path.exists():
            raise SystemExit(f"ERROR: <file{i}> path doesn't exist.")

    OVERRIDE = args.override
    DRY = args.dry

    tasks = list()

    # Create copying tasks
    for src_path, file in zip(src_paths, DESTINATIONS["files"]):
        if "ftp" in file["endpoints"]:  # Copying to FTP
            tasks.append(asyncio.create_task(copy_to_ftp(
                src_path,
                Config.FTP_ADDRESS,
                Config.FTP_USER,
                Config.FTP_PASSWORD,
                OVERRIDE,
                DRY)
            )
            )

        if "owncloud" in file["endpoints"]:  # Copying to OwnCloud
            tasks.append(copy_to_owncloud(src_path, Config.OWNCLOUD_URL, Config.OWNCLOUD_PASSWORD, OVERRIDE, DRY))

        if "folder" in file["endpoints"]:  # Copying locally
            tasks.append(asyncio.create_task(copy_locally(src_path, local_dest_path, OVERRIDE, DRY)))

    await asyncio.gather(*tasks)

    end = time.perf_counter()
    # seconds_elapsed = int(round(end - start, 0))
    seconds_elapsed = end - start
    print(f"SUCCESS: copied {len(src_paths)} file(s) in {seconds_elapsed} second(s)")


if __name__ == "__main__":
    asyncio.run(main())
