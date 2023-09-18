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


def is_valid_path(path: str) -> bool:
    # Checking if source files exist
    if not Path(path).exists():
        return False
    return True


def send_to_ftp(source_path: Path, override: bool = False, dry: bool = False):
    try:
        connection = FTP(host=Config.FTP_ADDRESS, user=Config.FTP_USER, passwd=Config.FTP_PASSWORD)
    except Exception as e:
        return f"an error occurred while connecting to FTP server: {e}"
    server_files = connection.nlst()

    with open(source_path, "rb") as file:
        if not (file.name in server_files) or override:
            connection.storlines(f"STOR {file.name}", file)
            connection.close()
        else:
            connection.close()
            print(f"{file.name}: file already exists on FTP; try using --override")
            raise SystemExit(1)


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
        print("local target folder doesn't exist")
        raise SystemExit(1)

    # Building complete target path
    target_path = Path(Config.LOCAL_TARGET_FOLDER + source_path.name)

    # from os import listdir
    # from os.path import isfile, join
    # file_list = [f for f in listdir(Config.LOCAL_PATH) if isfile(join(Config.LOCAL_PATH, f))]

    with open(source_path, "rb") as file:
        if not target_path.exists() or override:
            shutil.copy(source_path, target_path)
        else:
            print(f"{file.name} already exists; try using --override")
            raise SystemExit(1)

    # print("success!!!")
    return "end"


if __name__ == "__main__":
    # Building source files paths
    source_paths = list()
    source_paths.append(args.path_1 + DESTINATIONS["files"][0]["name"])
    source_paths.append(args.path_2 + DESTINATIONS["files"][1]["name"])
    source_paths.append(args.path_3 + DESTINATIONS["files"][2]["name"])

    for i, path in enumerate(source_paths, start=1):
        if not is_valid_path(path):
            print(path)
            print(f"file{i} path doesn't exist")
            raise SystemExit(1)

    override = args.override
    dry = args.dry

    for file in DESTINATIONS["files"]:
        if "ftp" in file["endpoints"]:
            pass
        if "owncloud" in file["endpoints"]:
            pass
        if "folder" in file["endpoints"]:
            pass

    # print(send_to_ftp(source_path_1, OVERRIDE, DRY))
    # print(send_to_owncloud(source_path_2, OVERRIDE, DRY))
    # print(send_locally(source_path_3, OVERRIDE, DRY))


# todo обработать вариант с отсутствующей целевой папкой
# todo логин-пароль неверный    был файл удалённо    не было файла удалённо     файл найден локально   файл не найден локально, иди нафиг
