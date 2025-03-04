# config.py
from fastapi import APIRouter, HTTPException

import common


router = APIRouter()
db = common.db.get_database()
system_config = common.db.get_system_config()


@router.get("/")
async def get_system_config():
    """
    Get system configuration
    获取系统配置
    """
    configs = list(system_config.find({}))
    for _ in configs:
        if "_id" in configs:
            configs["_id"] = str(configs["_id"])
    return configs


@router.get("/{config_name}")
async def get_single_config(config_name: str):
    """
    Get a single configuration item
    获取单个配置项
    """
    config = system_config.find_one({"name": config_name})
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    if "_id" in config:
        config["_id"] = str(config["_id"])
    return config


@router.post("/update")
async def update_system_config(config: common.SystemConfig):
    """
    Update system configuration
    更新系统配置
    """
    if not common.db.check_permission(db, permission="update-system-config"):
        raise HTTPException(
            status_code=403, detail="Permission denied, update-system-config"
        )
    system_config.update_one({"name": config.name}, {"$set": {"value": config.value}})
    return {"status": "success"}
