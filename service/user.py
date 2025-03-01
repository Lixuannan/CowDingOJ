# user.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import schedule

from typing import Union

import common


router = APIRouter()
db = common.db.get_database()
system_config = common.db.get_system_config()


class User(BaseModel):
    username: str
    email: str
    bio: Union[str, None] = None
    nickname: Union[str, None] = None
    password: str
    phone_number: Union[str, None] = None
    school_or_company: Union[str, None] = None
    introduction: Union[str, None] = None
    permissions: str = system_config.find_one({"name": "default-permissions"})["value"]


class UserInfo(BaseModel):
    username: str
    email: str
    bio: Union[str, None] = None
    nickname: Union[str, None] = None
    phone_number: Union[str, None] = None
    school_or_company: Union[str, None] = None
    introduction: Union[str, None] = None


class NewUser(BaseModel):
    username: str
    email: str
    password: str


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


@router.get("/check_username")
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
    print(user4db.model_dump())
    db["users"].insert_one(user4db.model_dump())
    return process_user_info(user4db.model_dump())


@router.get("/{username}")
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
        db["users"].update_one({"username": user.username}, user.model_dump())
        return db["users"].find_one({"username": user.username})
    except Exception:
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
                    "sid": cookie,
                    "timestamp": common.get_timestamp(),
                }
            )
            return {"status": "success", "sid": cookie}
    return {"status": "failed", "sid": None}


@router.post("/logout")
async def logout(username: str, cookie: str):
    """
    User logout
    用户登出
    """
    for s in db["sessions"]:
        if s["username"] == username and s["sid"] == cookie:
            db["sessions"].remove(s)
            return {"status": "success"}
    return {"status": "failed"}
