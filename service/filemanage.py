# filemanage.py
from fastapi import APIRouter, HTTPException, Cookie
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Union
import minio
import oss2

import os

import common


router = APIRouter()
db = common.db.get_database()
system_config = common.db.get_system_config()


class Storage:
    def __init__(self, url: str, access_key: str, secret_key: str, bucket: str): ...

    def upload(self, file: bytes, filename: str): ...

    def download(self, filename: str): ...

    def get_url(self, filename: str): ...

    def delete(self, filename: str): ...

    def generate_presigned_url(self, filename: str, expires: int = 3600): ...


class MinIOStorage(Storage):
    def __init__(self, url: str, access_key: str, secret_key: str, bucket: str):
        self.client = minio.Minio(url, access_key, secret_key)
        self.bucket = bucket

    def upload(self, file: bytes, filename: str):
        self.client.put_object(bucket_name=self.bucket, object_name=filename, data=file)

    def download(self, filename: str):
        return self.client.get_object(bucket_name=self.bucket, object_name=filename)

    def delete(self, filename: str):
        self.client.remove_object(bucket_name=self.bucket, object_name=filename)

    def generate_presigned_url(self, filename: str, expires: int = 3600):
        return self.client.presigned_get_object(self.bucket, filename, expires)


class OSSStorage(Storage):
    def __init__(self, url: str, access_key: str, secret_key: str, bucket: str):
        self.client = oss2.Bucket(oss2.Auth(access_key, secret_key), url, bucket)
        self.url = url

    def upload(self, file: bytes, filename: str):
        self.client.put_object(filename, file)

    def download(self, filename: str):
        return self.client.get_object(filename)

    def delete(self, filename: str):
        self.client.delete_object(filename)

    def generate_presigned_url(self, filename: str, expires: int = 3600):
        return self.client.sign_url("GET", filename, expires)


storage = (
    MinIOStorage(
        url=system_config.find_one({"name": "storage-minio-url"})["value"],
        access_key=system_config.find_one({"name": "storage-minio-access-key"})[
            "value"
        ],
        secret_key=system_config.find_one({"name": "storage-minio-secret-key"})[
            "value"
        ],
        bucket=system_config.find_one({"name": "storage-minio-bucket"})["value"],
    )
    if system_config.find_one({"name": "storage-type"})["value"] == "minio"
    else OSSStorage(
        url=system_config.find_one({"name": "storage-oss-url"})["value"],
        access_key=system_config.find_one({"name": "storage-oss-access-key"})["value"],
        secret_key=system_config.find_one({"name": "storage-oss-secret-key"})["value"],
    )
)


@router.post("/upload")
async def upload_file(
    file: bytes, filename: str, filetype: str, sid: str = Cookie(None)
):
    """
    Upload a file
    上传文件

    Args 参数:
    - file: File content 文件内容
    - filename: File name 文件名
    - filetype: File type (can be Image, Normal or Data) 文件类型【可以是 Image（图片）、Normal（普通文件） 或 Data（题目数据）】
    """
    if not db["sessions"].find_one({"sid": sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not common.db.check_permission(db, sid=sid, permission="upload-file"):
        raise HTTPException(status_code=403, detail="Permission denied, upload-file")
    if (
        not common.db.check_permission(db, sid=sid, permission="edit-problem")
        and filetype == "Data"
    ):
        raise HTTPException(status_code=403, detail="Permission denied, edit-problem")

    file_size = 0
    tmp_filename = f"/tmp/{common.get_timestamp()}"
    with open(tmp_filename, "wb") as f:
        while chunk := await file.read(10 * 1024 * 1024):
            file_size += len(chunk)
            if file_size > int(
                system_config.find_one({"name": "max-file-size"})["value"]
            ):
                raise HTTPException(status_code=413, detail="File too large")
            f.write(chunk)

    username = db["sessions"].find_one({"sid": sid})["username"]
    hash_filename = common.get_file_hash(tmp_filename)
    if db["files"].find_one({"hash_filename": hash_filename}):
        os.remove(tmp_filename)

    result = db["files"].insert_one(
        {
            "filename": filename,
            "owner": username,
            "hash_filename": hash_filename,
            "size": file_size,
            "filetype": filetype,
            "timestamp": common.get_timestamp(),
        }
    )
    with open(tmp_filename, "rb") as f:
        storage.upload(f.read(), hash_filename)
    os.remove(tmp_filename)

    return {"status": "success", "file_id": str(result.inserted_id)}


@router.get("/{filename}")
async def download_file(file_id: str, sid: str = Cookie(None)):
    """
    Download a file
    下载文件
    """
    file_record = db["files"].find_one({"_id": file_id})
    if file_record is None:
        raise HTTPException(status_code=404, detail="File not found")
    hash_filename = file_record["hash_filename"]

    if db["sessions"].find_one({"sid": sid}) is None and (
        file_record["filetype"] != "Image"
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")

    if (
        not common.db.check_permission(db, sid=sid, permission="download-data-file")
        and file_record["filetype"] == "Data"
    ):
        raise HTTPException(
            status_code=403, detail="Permission denied, download-data-file"
        )
    presigned_url = storage.generate_presigned_url(hash_filename)

    response = RedirectResponse(url=presigned_url)
    response.headers["Content-Disposition"] = (
        f"attachment; filename={file_record['filename']}"
    )
    return response


@router.post("/delete")
async def delete_file(file_id: str, sid: str = Cookie(None)):
    """
    Delete a file
    删除文件
    """
    if not db["sessions"].find_one({"sid": sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")

    user = db["sessions"].find_one({"sid": sid})["username"]
    file = db["files"].find_one({"_id": file_id})

    if file["owner"] != user and not common.db.check_permission(
        db, sid=sid, permission="delete-file"
    ):
        raise HTTPException(status_code=403, detail="Permission denied, delete-file")

    if db["files"].find({"hash_filename": file["hash_filename"]}).count() == 1:
        storage.delete(file["hash_filename"])

    db["files"].delete_one({"_id": file_id})
    return {"status": "success"}


@router.get("/list_all")
async def list_files(sid: str = Cookie(None)):
    """
    List all files
    列出所有文件
    """
    if not db["sessions"].find_one({"sid": sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not common.db.check_permission(db, sid=sid, permission="list-all-file"):
        raise HTTPException(status_code=403, detail="Permission denied, list-all-file")

    files = list(db["files"].find({}))
    return {"status": "success", "files": files}


@router.get("/list_user")
async def list_files(sid: str = Cookie(None)):
    """
    List all files
    列出所有文件
    """
    if not db["sessions"].find_one({"sid": sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")

    user = db["sessions"].find_one({"sid": sid})["username"]
    files = list(db["files"].find({"owner": user}))

    return {"status": "success", "files": files}
