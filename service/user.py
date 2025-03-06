# user.py
from fastapi import APIRouter, HTTPException, Cookie
import schedule

from typing import Annotated
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import common
from common.model import *


router = APIRouter()
db = common.db.get_database()
system_config = common.db.get_system_config()
logger = common.logger.get_logger(__name__)


def process_user_info(user: dict) -> dict:
    """
    Process user information
    处理用户信息
    """
    user_processed = UserInfo(**user)
    return user_processed.model_dump()


def clean_sessions():
    """
    Clean expired sessions
    清理过期的会话
    """
    for session in db["sessions"]:
        if common.get_timestamp() - session["timestamp"] > 2592000:
            db["sessions"].remove(session)


# Schedule the clean_sessions function to run every day at 2 AM
# 安排每天凌晨 2 点运行清理会话函数
schedule.every().day.at("02:00").do(clean_sessions)


@router.post("/check_username")
async def check_username(username: str):
    """
    Check if the username exists
    检查用户名是否存在
    """
    if db["users"].find_one({"username": username}) is not None:
        return {"status": "exists"}
    return {"status": "not exists"}


@router.post("/create_user")
async def create_user(user: NewUser) -> dict:
    """
    Create a new user
    创建一个新用户
    """
    if db["users"].find_one({"username": user.username}) is not None:
        raise HTTPException(status_code=400, detail="Username already exists")
    user4db = User(**user.model_dump())
    db["users"].insert_one(user4db.model_dump())
    return process_user_info(user4db.model_dump())


@router.post("/{username}")
async def read_user(username: str):
    """
    Get user info by username
    根据用户名获取用户信息
    """
    user = db["users"].find_one({"username": username})
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user = process_user_info(user)
    return user


@router.post("/update_user")
async def update_user(user: UserInfo):
    """
    Update user info
    更新用户信息
    """
    try:
        db["users"].update_one({"username": user.username}, {"$set": user.model_dump()})
        return process_user_info(db["users"].find_one({"username": user.username}))
    except Exception as e:
        logger.error(f"Failed to update user info, {e}")
        return {"status": "failed"}


@router.post("/reset_password")
async def reset_password(info: PasswordResetRequest):
    """
    Reset user password
    重置用户密码
    """
    user = db["users"].find_one({"username": info.username})

    if user and user["password"] == info.origin_password:
        db["users"].update_one(
            {"username": info.username}, {"$set": {"password": info.new_password}}
        )
        return {"status": "success"}
    else:
        return {"status": "failed, wrong password"}


@router.post("/delete_user")
async def delete_user(info: LoginRequest):
    """
    Delete user
    删除用户
    """
    user = db["users"].find_one({"username": info.username})
    if user and user["password"] == info.password:
        db["users"].delete_one({"username": info.username})
        return {"status": "success"}
    return {"status": "failed"}


@router.post("/user_login")
async def login(info: LoginRequest, cookies: Annotated[Cookies, Cookie()] = None):
    """
    User login
    用户登录
    """
    user = db["users"].find_one({"username": info.username})
    if user["password"] == info.password:
        db["sessions"].insert_one(
            {
                "username": info.username,
                "sid": cookies.sid,
                "timestamp": common.get_timestamp(),
            }
        )
        return {"status": "success", "sid": cookies.sid}
    return {"status": "failed", "sid": None}


@router.post("/user_logout")
async def logout(cookies: Annotated[Cookies, Cookie()] = None):
    """
    User logout
    用户登出
    """
    if not cookies or not cookies.sid:
        raise HTTPException(
            status_code=401, content={"detail": "No session ID found in cookies"}
        )

    session = db["sessions"].find_one({"sid": cookies.sid})
    if session:
        db["sessions"].delete_one({"sid": cookies.sid})
        return {"status": "success", "sid": cookies.sid}
    return {"status": "failed"}
