import argparse
import asyncio
import os
import shutil
import time
from collections import defaultdict
from ftplib import FTP
from pathlib import Path

import aioftp
import requests

from config import Config
from constants import DESTINATIONS


def send_to_ftp(source_paths: [Path], override: bool = False, dry: bool = False):
    """
    Sends files from list with source paths to FTP server's root folder.
    Dry mode would suppress actual copying but produce actual-like output.

    :param source_paths: list of source paths objects
    :param override: flag to overwrite existing files
    :param dry: flag to suppress actual changes in system
    :return:
    """

    try:
        connection = FTP(host=Config.FTP_ADDRESS, user=Config.FTP_USER, passwd=Config.FTP_PASSWORD)
    except Exception as e:
        raise SystemExit(f"ERROR: can't connect to FTP server: {e}.")

    files_list = connection.nlst()

    for source_path in source_paths:
        # Check if the  file is already exists on the server
        if source_path.name in files_list and not override:
            connection.close()
            raise SystemExit(f"ERROR: <{source_path.name}> already exists on the FTP server. Try using --override.")

        with open(source_path, "rb") as file:
            if not dry:
                connection.storlines(f"STOR {source_path.name}", file)
    connection.close()


# def send_to_owncloud(source_path: Path, override: bool = False, dry: bool = False):
#     try:
#         with open(source_path, "rb") as file:
#             response = requests.post(
#                 Config.OWNCLOUD_URL,
#                 files={"file": (os.path.basename(source_path), file)},
#                 auth=("user", Config.OWNCLOUD_PASSWORD),
#             )
#             if response.status_code == 200:
#                 return True
#             else:
#                 print(f"OwnCloud Error: {response.text}")
#                 return False
#     except Exception as e:
#         print(f"OwnCloud Error: {e}")
#         return False


def send_locally(source_paths: [Path], dest_path: Path, override: bool = False, dry: bool = False):
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("path_1")
    parser.add_argument("path_2")
    parser.add_argument("path_3")
    parser.add_argument("-o", "--override", action="store_true")
    parser.add_argument("-d", "--dry", action="store_true")

    args = parser.parse_args()

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

    start = time.time()

    # Building dict with endpoints as keys
    for source_path, file in zip(source_paths, DESTINATIONS["files"]):
        if "ftp" in file["endpoints"]:
            destinations["ftp"].append(source_path)

        if "owncloud" in file["endpoints"]:
            destinations["owncloud"].append(source_path)

        if "folder" in file["endpoints"]:
            destinations["folder"].append(source_path)

    for key, paths in destinations.items():
        if key == "ftp":  # Copying to FTP
            print(f"sending {len(paths)} file(s) to ftp")
            send_to_ftp(paths, OVERRIDE, DRY)

        if key == "owncloud":  # Copying to OwnCloud
            print(f"sending {len(paths)} file(s) to owncloud")
            # send_to_owncloud(source_path, OVERRIDE, DRY)

        if key == "folder":  # Copying locally
            # Check if target dir exists
            if not Path(Config.LOCAL_TARGET_FOLDER).exists():
                raise SystemExit("ERROR: local target directory doesn't exist.")

            print(f"sending {len(paths)} file(s) locally")
            # send_locally(paths, Path(Config.LOCAL_TARGET_FOLDER), OVERRIDE, DRY)

    print(time.time() - start)
    print("SUCCESS: copied 3 files.")
