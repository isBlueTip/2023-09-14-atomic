import os

import dotenv

dotenv.load_dotenv()


class Config:
    FTP_ADDRESS = os.getenv("FTP_ADDRESS", "ftp.automiq.ru")
    FTP_USER = os.getenv("FTP_USER", "xxxx-123321")
    FTP_PASSWORD = os.getenv("FTP_PASSWORD", "_xxx_aaa11")

    OWNCLOUD_URL = os.getenv("OWNCLOUD_URL", "https://fs.automiq.ru/owncloud/index.php/")
    OWNCLOUD_PASSWORD = os.getenv("OWNCLOUD_PASSWORD", "_xxx_aaa11")

    OWNCLOUD_TARGET_PATH = os.getenv("OWNCLOUD_FOLDER_PATH", "/tmp/xxxx-123321/")

    LOCAL_TARGET_PATH = os.getenv("LOCAL_PATH", "/tmp/test-230531/")
