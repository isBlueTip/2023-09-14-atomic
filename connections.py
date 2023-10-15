import base64
import http
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from pathlib import Path
from xml.etree import ElementTree

import aiofiles
import aiofiles.os
import aioftp
import aiohttp

from config import Config


class Connection(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def copy_file(
        self, src_path: Path, dst_path: Path, override: bool, dry: bool
    ):
        pass


class LocalConnection(Connection):
    def __init__(self):
        pass

    def connect(self):
        pass

    async def copy_file(
        self,
        src_path: Path,
        dst_path: Path,
        override: bool = False,
        dry: bool = False,
    ) -> None:
        """
        Копирует файл из src_path в локальную папку dst_path.

        Флаг override позволяет перезаписать существующий файл в dst_path.
        Флаг dry отключает фактическое копирование.

        :param src_path: Объект пути к источнику.
        :param dst_path: Объект пути к каталогу назначения.
        :param override: Флаг для перезаписи существующего файла.
        :param dry: Флаг для отключения фактических изменений в системе.
        :return:
        """

        print(f"копирование <{src_path.name}> в {dst_path.resolve()}")

        # Добавление имени файла к объекту пути папки
        dst_path = dst_path.joinpath(src_path.name)

        # Проверка, существует ли файл уже в папке назначения
        if not dst_path.exists() or override:
            # Копирование, если не в режиме dry
            if not dry:
                try:
                    handle_src = await aiofiles.open(src_path, mode="r")
                    handle_dst = await aiofiles.open(dst_path, mode="w")

                    stat_src = await aiofiles.os.stat(src_path)
                    bytes_cnt = stat_src.st_size

                    src_descr = handle_src.fileno()
                    dst_descr = handle_dst.fileno()

                    await aiofiles.os.sendfile(
                        dst_descr, src_descr, 0, bytes_cnt
                    )
                except Exception as e:
                    print(
                        f"ОШИБКА: <{e}> при копировании <{src_path.name}> в"
                        f" {dst_path.resolve()}"
                    )
                    return
            print(
                f"УСПЕХ: <{src_path.name}> скопирован в {dst_path.resolve()}"
            )

        else:
            print(
                f"ОШИБКА: <{src_path.name}> уже существует в локальной целевой"
                " папке. Попробуйте использовать --override."
            )


class FTPConnection(Connection):
    def __init__(self, url: str, login: str, password: str):
        """
        Инициализация нового подключения FTP.

        :param url: URL для подключения.
        :param login: Имя пользователя для входа.
        :param password: Пароль для входа.
        """

        self.url = url
        self.login = login
        self.password = password

    @asynccontextmanager
    async def connect(self) -> aioftp.Client:
        """
        Возвращает экземпляр клиента aioftp для использования в качестве контекстного менеджера.

        :return:
        """

        client = aioftp.Client()
        await client.connect(self.url)
        await client.login(user=self.login, password=self.password)
        yield client

    async def copy_file(
        self,
        src_path: Path,
        dst_path: Path = Path("/"),
        override: bool = False,
        dry: bool = False,
    ):
        """
        Копирует файл из src_path в корневую папку сервера FTP.

        Параметр dst_path не используется в этой версии метода.
        Флаг override позволяет перезаписать существующий файл в корневой папке.
        Флаг dry отключает фактическое копирование.

        :param src_path: Объект пути источника.
        :param dst_path: Объект пути назначения.
        :param override: Флаг для перезаписи существующего файла.
        :param dry: Флаг для отключения фактических изменений в системе.
        :return:
        """

        print(f"копирование <{src_path.name}> на FTP")

        async with self.connect() as client:
            # Проверка, существует ли файл уже на сервере
            if await client.exists(src_path.name) and not override:
                print(
                    f"ОШИБКА: <{src_path.name}> уже существует на сервере FTP."
                    " Попробуйте использовать --override."
                )
                return

            # Копирование, если не в режиме dry
            if not dry:
                try:
                    await client.upload(src_path)
                except Exception as e:
                    print(
                        f"ОШИБКА: <{e}> при копировании <{src_path.name}>"
                        " на FTP"
                    )
                    return
            print(f"УСПЕХ: <{src_path.name}> скопирован на FTP")


class OwnCloudConnection(Connection):
    _session = None

    def __init__(self, url: str, password: str):
        """
        Инициализация нового подключения OwnCloud.

        :param url: OwnCloud URL.
        :param password: Пароль OwnCloud.
        """

        self.url = url
        self.password = password

    @classmethod
    def get_session(cls) -> aiohttp.ClientSession:
        if cls._session is None:
            cls._session = aiohttp.ClientSession()
        return cls._session

    @asynccontextmanager
    async def connect(self) -> aiohttp.ClientSession:
        """
        Возвращает экземпляр клиента OwnCloud для использования в качестве контекстного менеджера.

        :return:
        """

        session = self.get_session()

        yield session

    async def copy_file(
        self,
        src_path: Path,
        dst_path: Path = Path("/"),
        override: bool = False,
        dry: bool = False,
    ):
        """
        Отправляет файл из src_path в общую корневую папку сервера OwnCloud.

        Параметр dst_path не используется в этой версии метода.
        Флаг override позволяет перезаписать существующий файл в корневой папке.
        Флаг dry отключает фактическое копирование.

        :param src_path: Объект пути источника.
        :param dst_path: Объект пути назначения.
        :param override: Флаг для перезаписи существующего файла.
        :param dry: Флаг для отключения фактических изменений в системе.
        :return:
        """

        print(f"копирование <{src_path.name}> в OwnCloud")

        # Парсинг идентификатора общей папки и кодирование его вместе с паролем в base64
        token = self.url.split("/")[-1]
        credentials = f"{token}:{self.password}"
        credentials_encoded = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Depth": "1",
            "Authorization": f"Basic {credentials_encoded}",
            "Content-Type": "text/html",
        }

        async with self.connect() as session:
            # Проверка, если файл уже на сервере
            async with session.request(
                "PROPFIND", Config.OWNCLOUD_WEBDAV_ENDPOINT, headers=headers
            ) as resp:
                if resp.status != http.HTTPStatus.MULTI_STATUS:
                    print(
                        f"ОШИБКА: <{resp.status}> HTTP-статус при подключении"
                        " к OwnCloud (ожидается <207_MULTI_STATUS>)"
                    )
                    return

                content = await resp.read()
                xml_root = ElementTree.fromstring(content)

                for elem in xml_root.iter("{DAV:}response"):
                    path = elem.find("{DAV:}href").text
                    if path.endswith(src_path.name) and not override:
                        print(
                            f"ОШИБКА: <{src_path.name}> уже существует на"
                            " сервере OwnCloud. Попробуйте использовать"
                            " --override."
                        )
                        return

            # Копирование, если не в режиме dry
            if not dry:
                file = open(src_path, "rb").read()
                try:
                    resp = await session.put(
                        f"{Config.OWNCLOUD_WEBDAV_ENDPOINT}/{src_path.name}",
                        data=file,
                        headers=headers,
                    )
                except Exception as e:
                    print(
                        f"ОШИБКА: <{e}> при копировании <{src_path.name}> в"
                        " OwnCloud"
                    )
                    return
                if resp.status not in (
                    http.HTTPStatus.NO_CONTENT,
                    http.HTTPStatus.CREATED,
                ):
                    print(
                        f"ОШИБКА: <{resp.status}> HTTP-статус при копировании"
                        f" <{src_path.name}> в OwnCloud (ожидается"
                        " <201_CREATED> или <204_NO_CONTENT>)"
                    )
                    return
            print(f"УСПЕХ: <{src_path.name}> скопирован в OwnCloud")
