# config.py
from fastapi import APIRouter, HTTPException, Cookie

import os
import sys
from typing import Annotated

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import common
from common.model import *


router = APIRouter()
db = common.db.get_database()
system_config = common.db.get_system_config()


@router.post("/")
async def get_system_config(cookies: Annotated[Cookies, Cookie()] = None):
    """
    Get system configuration
    获取系统配置
    """
    if not common.db.check_permission(
        db, sid=cookies.sid, permission="get-system-config"
    ):
        raise HTTPException(
            status_code=403, detail="Permission denied, get-system-config"
        )
    configs = list(system_config.find({}))
    for _ in configs:
        if "_id" in configs:
            configs["_id"] = str(configs["_id"])
    return configs


@router.post("/{config_name}")
async def get_single_config(
    config_name: str, cookies: Annotated[Cookies, Cookie()] = None
):
    """
    Get a single configuration item
    获取单个配置项
    """
    if not common.db.check_permission(
        db, sid=cookies.sid, permission="get-system-config"
    ):
        raise HTTPException(
            status_code=403, detail="Permission denied, get-system-config"
        )
    config = system_config.find_one({"name": config_name})
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    if "_id" in config:
        config["_id"] = str(config["_id"])
    return config


@router.post("/update")
async def update_system_config(
    config, cookies: Annotated[Cookies, Cookie()] = None
):
    """
    Update system configuration
    更新系统配置
    """
    if not common.db.check_permission(
        db, sid=cookies.sid, permission="update-system-config"
    ):
        raise HTTPException(
            status_code=403, detail="Permission denied, update-system-config"
        )
    system_config.update_one({"name": config.name}, {"$set": {"value": config.value}})
    return {"status": "success"}
