# Добавить обработку более чем трёх файлов
# Добавить флаг игнорирования файла
# Добавить флаг игнорирования эндпоинта
# Добавить копирование папки
# Есть что оптимизировать и куда вносить изменения при увеличении количества копируемых файлов

# Для работы с эндпоинтами выбрал самые популярные и поддерживаемые библиотеки

# TODO Убрать .env и fuxtures с прода. Оставил для более простой проверки тестового

import argparse
import asyncio
import sys
import time
from pathlib import Path

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


async def main():
    assert sys.version_info >= (3, 7), "Python >= 3.7 is required"

    # Check if local target dir exists
    local_dest_path = Path(Config.LOCAL_TARGET_FOLDER)
    if not local_dest_path.exists():
        raise SystemExit("ERROR: local target directory doesn't exist.")

    args = init_args()

    start = time.perf_counter()

    # Создание путей исходных файлов
    src_paths = list()
    src_paths.append(Path(args.dir_1 + DESTINATIONS["files"][0]["name"]))
    src_paths.append(Path(args.dir_2 + DESTINATIONS["files"][1]["name"]))
    src_paths.append(Path(args.dir_3 + DESTINATIONS["files"][2]["name"]))

    # Проверка наличия исходных файлов
    for i, path in enumerate(src_paths, start=1):
        if not path.exists():
            raise SystemExit(f"ERROR: <file{i}> path doesn't exist.")

    override = args.override
    dry = args.dry

    tasks = list()

    # Создание объектов соединений для каждого эндпоинта
    local_connection = LocalConnection()
    ftp_connection = FTPConnection(
        Config.FTP_ADDRESS, Config.FTP_USER, Config.FTP_PASSWORD
    )
    owncloud_connection = OwnCloudConnection(
        url=Config.OWNCLOUD_URL, password=Config.OWNCLOUD_PASSWORD
    )

    # Создание задач на копирование
    for src_path, file in zip(src_paths, DESTINATIONS["files"]):
        if "folder" in file["endpoints"]:  # Копирование локально
            tasks.append(
                asyncio.create_task(
                    local_connection.copy_file(
                        src_path=src_path,
                        dst_path=local_dest_path,
                        override=override,
                        dry=dry,
                    )
                )
            )

        if "ftp" in file["endpoints"]:  # Копирование на FTP
            tasks.append(
                asyncio.create_task(
                    ftp_connection.copy_file(
                        src_path=src_path, override=override, dry=dry
                    )
                )
            )

        if "owncloud" in file["endpoints"]:  # Копирование на OwnCloud
            tasks.append(
                owncloud_connection.copy_file(
                    src_path=src_path, override=override, dry=dry
                )
            )

    await asyncio.gather(*tasks, return_exceptions=False)

    end = time.perf_counter()
    seconds_elapsed = int(round(end - start, 0))
    if not dry:
        print(f"\nSUCCESS: copied in {seconds_elapsed} second(s)")


if __name__ == "__main__":
    asyncio.run(main())
