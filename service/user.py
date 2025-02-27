# user.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import psutil

import common


router = APIRouter()
db = common.db.get_database()


class User(BaseModel):
    username: str
    email: str
    nickname: str = None
    password: str
    phone_number: str = None
    school_or_company: str = None
    introduction: str = None


@router.get("/")
async def read_root():
    """
    系统状态
    System status
    """
    cpu_usage = psutil.cpu_percent(interval=1)
    ram_usage = psutil.virtual_memory().percent
    return {
        "status": "running",
        "cpu_usage": cpu_usage,
        "ram_usage": ram_usage
    }


@router.post("/create_user")
async def create_user(user: User):
    """
    Create a new user
    创建一个新用户
    """
    # Simulate database insert
    db["users"].insert_one(user.model_dump())
    return user


@router.get("/users/{username}")
async def read_user(username: str):
    """
    Get user info by username
    根据用户名获取用户信息
    """
    user = next((u for u in db["users"] if u["username"] == username), None)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    # Protect user passwd
    user.password = ""
    return user


@router.post("/update_user")
async def update_user(user: User):
    """
    Update user info
    更新用户信息
    """
    for u in db["users"]:
        if u["username"] == user.username:
            user.password = u["password"]
            u.update(user.model_dump())
            return user
    return {"status": "failed"}


@router.post("/reset_password")
async def reset_password(username: str, origin_password: str, new_password: str):
    """
    Reset user password
    重置用户密码
    """
    for u in db["users"]:
        if u["username"] == username and u["password"] == origin_password:
            u["password"] = new_password
            return u
    return {"status": "failed"}


@router.post("/delete_user")
async def delete_user(username: str, password: str):
    for u in db["users"]:
        if u["username"] == username and u["password"] == password:
            db["users"].remove(u)
            return {"status": "success"}
    return {"status": "failed"}


@router.post("/login")
async def login(username: str, password: str, cookie: str):
    """
    User login
    用户登录
    """
    for u in db["users"]:
        if u["username"] == username and u["password"] == password:
            db["sessions"].insert_one(
                {
                    "username": username,
                    "cookie": cookie,
                    "timestamp": common.get_timestamp(),
                }
            )
            return {"status": "success", "cookie": cookie}
    return {"status": "failed", "cookie": None}
