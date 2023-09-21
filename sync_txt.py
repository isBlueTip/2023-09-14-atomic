import argparse
import asyncio
import shutil
import time
from collections import defaultdict
from ftplib import FTP
from pathlib import Path

import aioftp

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


async def send_to_ftp(source_path: Path, override: bool = False, dry: bool = False) -> None:
    """
    Sends files from list with source paths to FTP server's root folder.
    Dry mode would suppress actual copying but produce actual-like output.

    :param source_paths: list of source paths objects
    :param override: flag to overwrite existing files
    :param dry: flag to suppress actual changes in system
    :return:
    """
    async with aioftp.Client.context(Config.FTP_ADDRESS, user=Config.FTP_USER, password=Config.FTP_PASSWORD) as client:
        # Check if the  file is already exists on the server
        if await client.exists(source_path.name) and not override:
            raise SystemExit(f"ERROR: <{source_path.name}> already exists on the FTP server. Try using --override.")
        if not dry:
            await client.upload(source_path)


# async def send_to_owncloud(source_paths: [Path], override: bool = False, dry: bool = False) -> None:
#     pass


def send_locally(source_paths: [Path], dest_path: Path, override: bool = False, dry: bool = False) -> None:
    """
    Copy file from source path to local target_path folder.
    Dry mode would suppress actual copying but produce actual-like output.

    :param source_paths: list of source paths objects
    :param dest_path: destination directory path object
    :param override: flag to overwrite existing files
    :param dry: flag to suppress actual changes in system
    :return:
    """

    for source_path in source_paths:
        # Check if the file already exists in the destination folder
        if not dest_path.joinpath(source_path.name).exists() or override:
            if not dry:
                shutil.copy(source_path, dest_path)
        else:
            raise SystemExit(
                f"ERROR: <{source_path.name}> already exists in the local target dir. Try using --override."
            )


async def main():
    args = init_args()

    start = time.time()

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
        if "ftp" in file["endpoints"]:  # Copying to FTP
            print(f"sending {source_path.name} to ftp asyncronously")
            tasks.append(asyncio.create_task(send_to_ftp(source_path, OVERRIDE, DRY)))
            destinations["ftp"].append(source_path)

        if "owncloud" in file["endpoints"]:
            print("append owncloud")
            destinations["owncloud"].append(source_path)

        if "folder" in file["endpoints"]:
            print("append folder")
            tasks.append(asyncio.create_task(asend_locally(source_path, file, OVERRIDE, DRY)))
            destinations["folder"].append(source_path)

    await asyncio.gather(*tasks)

    # Main copying loop
    for key, paths in destinations.items():
        if key == "owncloud":  # Copying to OwnCloud
            print(f"sending {len(paths)} file(s) to owncloud")
            # send_to_owncloud(paths, OVERRIDE, DRY)

        if key == "folder":  # Copying locally
            # Check if target dir exists
            if not Path(Config.LOCAL_TARGET_FOLDER).exists():
                raise SystemExit("ERROR: local target directory doesn't exist.")

            print(f"sending {len(paths)} file(s) locally")
            send_locally(paths, Path(Config.LOCAL_TARGET_FOLDER), OVERRIDE, DRY)

    seconds_elapsed = int(round(time.time() - start, 0))
    print(f"SUCCESS: copied {len(destinations)} file(s) in {seconds_elapsed} second(s)")


if __name__ == "__main__":
    asyncio.run(main())


# Добавить обработку более чем трёх файлов
# Добавить флаг игнорирования файла
# Добавить флаг игнорирования эндпоинта
# Добавить копирование папки
