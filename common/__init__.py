from . import db

import hashlib
import time


def get_file_hash(filename: str) -> str:
    """
    Get file hash
    获取文件哈希
    """
    with open(filename, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def get_timestamp() -> int:
    """
    Get current timestamp
    获取当前时间戳
    """
    return str(time.time_ns())
