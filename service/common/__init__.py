from . import db

import hashlib


def get_file_hash(filename: str) -> str:
    """
    Get file hash
    获取文件哈希
    """
    with open(filename, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()