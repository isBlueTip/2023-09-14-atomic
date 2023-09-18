import argparse
import os
import shutil
from ftplib import FTP
from pathlib import Path

import requests

from config import Config

parser = argparse.ArgumentParser()

parser.add_argument("path_1")
parser.add_argument("path_2")
parser.add_argument("path_3")
parser.add_argument("-o", "--override", action="store_true")
parser.add_argument("-d", "--dry", action="store_true")

args = parser.parse_args()

source_path_1 = Path(args.path_1 + "file1.txt")
source_path_2 = Path(args.path_2 + "file2.txt")
source_path_3 = Path(args.path_3 + "file3.txt")


OVERRIDE = args.override
DRY = args.dry

if not source_path_1.exists():
    print("file1 path doesn't exist")
    raise SystemExit(1)

if not source_path_2.exists():
    print("file2 path doesn't exist")
    raise SystemExit(1)

if not source_path_3.exists():
    print("file3 path doesn't exist")
    raise SystemExit(1)


def send_to_ftp(source_path: Path, override: bool = False):
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


# def send_to_owncloud(source_path: Path, override: bool = False):
#     print(source_path)
#     print("")
#
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


def send_locally(source_path: Path, override: bool = False):
    if not Path(Config.LOCAL_TARGET_PATH).exists():
        print("local target path doesn't exist")
        raise SystemExit(1)

    target_path = Path(Config.LOCAL_TARGET_PATH + source_path.name)

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
    # print(send_to_ftp(source_path_1, OVERRIDE, DRY))
    # print(send_to_owncloud(source_path_2, OVERRIDE, DRY))
    print(send_locally(source_path_3, OVERRIDE, DRY))


# todo обработать вариант с отсутствующей целевой папкой
# todo логин-пароль неверный    был файл удалённо    не было файла удалённо     файл найден локально   файл не найден локально, иди нафиг
