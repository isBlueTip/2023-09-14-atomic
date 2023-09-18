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
        raise SystemExit(f"ERROR: can't connect to FTP server: {e}")

    # Check if file is already exists on the server
    if source_path.name in connection.nlst() and not override:
        raise SystemExit(f"ERROR: <{source_path.name}> already exists on the FTP server. Try using --override")

    with open(source_path, "rb") as file:
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


def send_locally(source_path: Path, override: bool = False, dry: bool = False):
    if not Path(Config.LOCAL_TARGET_FOLDER).exists():
        raise SystemExit("local target folder doesn't exist")

    # Building complete target path
    target_path = Path(Config.LOCAL_TARGET_FOLDER + source_path.name)

    # from os import listdir
    # from os.path import isfile, join
    # file_list = [f for f in listdir(Config.LOCAL_PATH) if isfile(join(Config.LOCAL_PATH, f))]

    with open(source_path, "rb") as file:
        if not target_path.exists() or override:
            shutil.copy(source_path, target_path)
        else:
            raise SystemExit(f"{file.name} already exists; try using --override")

    return "end"


if __name__ == "__main__":
    # Building source files paths
    source_paths = list()
    source_paths.append(Path(args.path_1 + DESTINATIONS["files"][0]["name"]))
    source_paths.append(Path(args.path_2 + DESTINATIONS["files"][1]["name"]))
    source_paths.append(Path(args.path_3 + DESTINATIONS["files"][2]["name"]))

    for i, path in enumerate(source_paths, start=1):
        if not path.exists():
            print(f"file{i} path doesn't exist")
            raise SystemExit(1)

    override = args.override
    dry = args.dry

    for source_path, file in zip(source_paths, DESTINATIONS["files"]):
        if "ftp" in file["endpoints"]:
            print("sending to ftp", "\n", "\n")
            send_to_ftp(source_path, override, dry)
            print("finish sending to ftp", "\n", "\n")
        if "owncloud" in file["endpoints"]:
            print("sending to owncloud", "\n", "\n")
            # send_to_owncloud(source_path, override, dry)
            print("finish sending to owncloud", "\n", "\n")
        if "folder" in file["endpoints"]:
            print("sending locally", "\n", "\n")
            send_locally(source_path, override, dry)
            print("finish sending locally", "\n", "\n")
    print("successfully copied 3 files")


# todo обработать вариант с отсутствующей целевой папкой
# todo логин-пароль неверный    был файл удалённо    не было файла удалённо     файл найден локально   файл не найден локально, иди нафиг
