import os

import dotenv

dotenv.load_dotenv()


class Config:
    FTP_ADDRESS = os.getenv("FTP_ADDRESS", "ftp.automiq.ru")
    FTP_USER = os.getenv("FTP_USER", "xxxx-123321")
    FTP_PASSWORD = os.getenv("FTP_PASSWORD", "_xxx_aaa11")

    OWNCLOUD_URL = os.getenv("OWNCLOUD_URL", "https://fs.automiq.ru/owncloud/index.php/")
    OWNCLOUD_PASSWORD = os.getenv("OWNCLOUD_PASSWORD", "_xxx_aaa11")

    OWNCLOUD_TARGET_FOLDER = os.getenv("OWNCLOUD_TARGET_FOLDER", "/tmp/xxxx-123321/")

    LOCAL_TARGET_FOLDER = os.getenv("LOCAL_TARGET_FOLDER", "/tmp/test-230531/")
