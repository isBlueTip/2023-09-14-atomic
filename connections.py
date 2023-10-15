import base64
import http
import os
import sys
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from pathlib import Path
from xml.etree import ElementTree

import aiofiles
import aiofiles.os
import aioftp
import aiohttp
from ipdb import set_trace

from config import Config


class FileOperation:  # todo
    def __init__(self, override: bool = False, dry: bool = False):
        self.override: override
        self.dry: dry

    def copy(self):
        pass


class Connection(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def copy_files(
        self,
        src_path: Path,
        dst_path: Path,
        override: bool = False,
        dry: bool = False,
    ):
        pass


class LocalConnection(Connection):
    def __init__(self):
        pass

    def connect(self):
        pass

    async def copy_files(
        self,
        src_path: Path,
        dst_path: Path,
        override: bool = False,
        dry: bool = False,
    ) -> None:
        """
        Copy file from src_path to local dst_path directory.

        Override flag would override an existing file in a dst_path.
        Dry mode would suppress actual copying but produce actual-like output.

        :param src_path: source path object
        :param dst_path: destination directory path object
        :param override: flag to overwrite existing file
        :param dry: flag to suppress actual changes in system
        :return:
        """

        print(f"copying <{src_path.name}> to {dst_path.resolve()}")

        # Add filename to a folder path
        dst_path = dst_path.joinpath(src_path.name)

        # Check if the file already exists in the destination folder
        if not dst_path.exists() or override:
            # Copy if not dry mode
            if not dry:
                try:  # Replace target dir with file
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
                        f"ERROR: <{e}> when copying <{src_path.name}> to"
                        f" {dst_path.resolve()}"
                    )
                    return
            print(f"SUCCESS: <{src_path.name}> copied to {dst_path.resolve()}")

        else:
            print(
                f"ERROR: <{src_path.name}> already exists in the local target"
                " dir. Try using --override."
            )


class FTPConnection(Connection):
    def __init__(self, url: str, login: str, password: str):
        """
        Init new ftp connection

        :param url:
        :param login:
        :param password:
        """

        self.url = url
        self.login = login
        self.password = password

    @asynccontextmanager
    async def connect(self):
        """
        Return an aioftp client instance to use as a context manager

        :return:
        """

        client = aioftp.Client()
        await client.connect(self.url)
        await client.login(user=self.login, password=self.password)
        yield client

    async def copy_files(
        self,
        src_path: Path,
        dst_path: None,
        override: bool = False,
        dry: bool = False,
    ):
        """
        Copy a file from src_path to FTP server's root folder.

        dst_path is not used in this version of ftp copying
        Override flag would override an existing file in a root folder.
        Dry mode would suppress actual copying but produce actual-like output.

        :param src_path: source path object
        :param dst_path: destination path object
        :param override: flag to overwrite existing file
        :param dry: flag to suppress actual changes in system
        :return:
        """

        print(f"copying <{src_path.name}> to ftp")

        async with self.connect() as client:
            # Check if the file already exists on the server
            if await client.exists(src_path.name) and not override:
                print(
                    f"ERROR: <{src_path.name}> already exists on the FTP"
                    " server. Try using --override."
                )
                return

            # Copy if not dry mode
            if not dry:
                try:
                    await client.upload(src_path)
                except Exception as e:
                    print(
                        f"ERROR: <{e}> when copying <{src_path.name}> to ftp"
                    )
                    return
            print(f"SUCCESS: <{src_path.name}> copied to ftp")


class OwnCloudConnection(Connection):
    def __init__(self, url: str, login: str, password: str):
        """
        Init new OwnCloud connection

        :param url:
        :param login:
        :param password:
        """

        self.url = url
        self.login = login
        self.password = password

    @asynccontextmanager
    async def connect(self):
        """
        Return an OwnCLoud client instance to use as a context manager

        :return:
        """

        # # Parse shared dir id and encode it along with password in base64
        # token = self.url.split("/")[-1]
        # credentials = f"{token}:{self.password}"
        # credentials_encoded = base64.b64encode(credentials.encode()).decode()
        #
        # headers = {
        #     "Depth": "1",
        #     "Authorization": f"Basic {credentials_encoded}",
        #     "Content-Type": "text/html",
        # }

        # session = aiohttp.ClientSession(Config.OWNCLOUD_WEBDAV_ENDPOINT)
        session = aiohttp.ClientSession()

        # resp = await session.request("PROPFIND", Config.OWNCLOUD_WEBDAV_ENDPOINT, headers=headers)
        #
        # if resp.status != http.HTTPStatus.MULTI_STATUS:
        #     print(
        #         f"ERROR: <{resp.status}> HTTP status when connecting to"
        #         " owncloud (<207_MULTI_STATUS> expected)"
        #     )
        #     return

        yield session

    async def copy_files(
        self,
        src_path: Path,
        dst_path: Path,
        override: bool = False,
        dry: bool = False,
    ):
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

        print(f"copying <{src_path.name}> to owncloud")

        # Parse shared dir id and encode it along with password in base64
        token = self.url.split("/")[-1]
        credentials = f"{token}:{self.password}"
        credentials_encoded = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Depth": "1",
            "Authorization": f"Basic {credentials_encoded}",
            "Content-Type": "text/html",
        }

        # async with aiohttp.ClientSession() as session:
        async with self.connect() as session:
            # set_trace()
            # # Check if the file already exists on the server
            async with session.request(
                "PROPFIND", Config.OWNCLOUD_WEBDAV_ENDPOINT, headers=headers
            ) as resp:
                if resp.status != http.HTTPStatus.MULTI_STATUS:
                    print(
                        f"ERROR: <{resp.status}> HTTP status when connecting"
                        " to owncloud (<207_MULTI_STATUS> expected)"
                    )
                    return

                content = await resp.read()
                xml_root = ElementTree.fromstring(content)

                for elem in xml_root.iter("{DAV:}response"):
                    path = elem.find("{DAV:}href").text
                    if path.endswith(src_path.name) and not override:
                        print(
                            f"ERROR: <{src_path.name}> already exists on the"
                            " OwnCloud server. Try using --override."
                        )
                        return

            # Copy if not dry mode
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
                        f"ERROR: <{e}> when copying <{src_path.name}> to"
                        " owncloud"
                    )
                    return
                if resp.status not in (
                    http.HTTPStatus.NO_CONTENT,
                    http.HTTPStatus.CREATED,
                ):
                    print(
                        f"ERROR: <{resp.status}> HTTP status when copying"
                        f" <{src_path.name}> to owncloud (<201_CREATED> or"
                        " <204_NO_CONTENT> expected)"
                    )
                    return
            print(f"SUCCESS: <{src_path.name}> copied to owncloud")
