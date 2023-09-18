import argparse
from ftplib import FTP
from pathlib import Path

from config import Config

parser = argparse.ArgumentParser()

parser.add_argument("path_1")
parser.add_argument("path_2")
parser.add_argument("path_3")
parser.add_argument("-o", "--override", action="store_true")
parser.add_argument("-d", "--dry", action="store_true")

args = parser.parse_args()

path_1 = Path(args.path_1 + "file1.txt")
path_2 = Path(args.path_2 + "file2.txt")
path_3 = Path(args.path_3 + "file3.txt")


OVERRIDE = args.override
DRY = args.dry

if not path_1.exists():
    print("file 1: path doesn't exist")
    raise SystemExit(1)

if not path_2.exists():
    print("file 2: path doesn't exist")
    raise SystemExit(1)

if not path_3.exists():
    print("file 3: path doesn't exist")
    raise SystemExit(1)


def send_to_ftp(path: Path, override: bool = False):
    try:
        connection = FTP(host=Config.FTP_ADDRESS, user=Config.FTP_USER, passwd=Config.FTP_PASSWORD)
    except Exception as e:
        return f"an error occurred while connecting to FTP server: {e}"
    server_files = connection.nlst()

    with open(path, "rb") as file:
        if not (file.name in server_files) or override:
            connection.storlines(f"STOR {file.name}", file)
            connection.close()
        else:
            print(f"{file.name}: file already exists. try using --override")
            raise SystemExit(1)


def send_to_owncloud(path: Path, override: bool = False):
    print(path)
    print("")


def send_locally(path: Path, override: bool = False):
    print(path)


if __name__ == "__main__":
    print(send_to_ftp(path_1, OVERRIDE))
    # print(send_to_owncloud(path_2, OVERRIDE))
    # print(send_locally(path_3, OVERRIDE))
