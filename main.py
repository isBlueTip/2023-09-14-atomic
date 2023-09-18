import argparse
import os
import shutil
from ftplib import FTP
from pathlib import Path

import requests

from config import Config
from constants import DESTINATIONS

parser = argparse.ArgumentParser()

parser.add_argument("path_1")
parser.add_argument("path_2")
parser.add_argument("path_3")
parser.add_argument("-o", "--override", action="store_true")
parser.add_argument("-d", "--dry", action="store_true")

args = parser.parse_args()


def send_to_ftp(source_path: Path, override: bool = False, dry: bool = False):
    """
    Sends file from source path to FTP server's root folder.
    Dry mode would suppress actual copying but produce actual-like output.

    :param source_path:
    :param override:
    :param dry:
    :return:
    """
    try:
        connection = FTP(host=Config.FTP_ADDRESS, user=Config.FTP_USER, passwd=Config.FTP_PASSWORD)
    except Exception as e:
        raise SystemExit(f"ERROR: can't connect to FTP server: {e}.")

    # Check if file is already exists on the server
    if source_path.name in connection.nlst() and not override:
        raise SystemExit(f"ERROR: <{source_path.name}> already exists on the FTP server. Try using --override.")

    with open(source_path, "rb") as file:
        if not dry:
            connection.storlines(f"STOR {file.name}", file)
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


def send_locally(source_path: Path, dest_path: Path, override: bool = False, dry: bool = False):
    """
    Copy file from source path to local target_path folder.
    Dry mode would suppress actual copying but produce actual-like output.

    :param source_path:
    :param override:
    :param dry:
    :return:
    """
    # Check if the file already exists
    if not dest_path.exists() or override:
        if not dry:
            shutil.copy(source_path, dest_path)
    else:
        raise SystemExit(f"ERROR: <{source_path.name}> already exists in the local target dir. Try using --override.")


if __name__ == "__main__":
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

    for source_path, file in zip(source_paths, DESTINATIONS["files"]):
        if "ftp" in file["endpoints"]:  # Copying to FTP
            print("sending to ftp", "\n")
            send_to_ftp(source_path, OVERRIDE, DRY)
            print("finish sending to ftp", "\n")

        if "owncloud" in file["endpoints"]:  # Copying to OwnCloud
            print("sending to owncloud", "\n")
            # send_to_owncloud(source_path, OVERRIDE, DRY)
            print("finish sending to owncloud", "\n")

        if "folder" in file["endpoints"]:  # Copying locally
            if not Path(Config.LOCAL_TARGET_FOLDER).exists():
                raise SystemExit("ERROR: local target folder doesn't exist.")

            # Building complete target path
            target_path = Path(Config.LOCAL_TARGET_FOLDER + source_path.name)

            print("sending locally", "\n")
            send_locally(source_path, target_path, OVERRIDE, DRY)
            print("finish sending locally", "\n")
    print("SUCCESS: copied 3 files.")
