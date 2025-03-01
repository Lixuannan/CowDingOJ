# common/db.py
import pymongo
import yaml
from pymongo.collection import Collection
from pymongo.database import Database

# Global variable to avoid creating connections repeatedly
# 全局变量，避免重复创建连接
_client = None
_db = None


# Read the configuration file
# 读取配置文件
def load_config() -> dict:
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)


_config = load_config()
_mongodb_url = (
    f"mongodb://{_config['database']['user']}:{_config['database']['password']}"
    f"@{_config['database']['host']}:{_config['database']['port']}"
)


def check_permission(sid: str, permission: str) -> bool:
    """
    Check if the user has the specified permission
    检查用户是否具有指定的权限
    """
    session = _db["sessions"].find_one({"sid": sid})
    if not session:
        return False
    permissions = (
        _db["users"]
        .find_one({"username": session["username"]})["permissions"]
        .split(",")
    )
    return permission in permissions


def get_client(uri: str = _mongodb_url) -> pymongo.MongoClient:
    """
    Get the MongoDB client connection
    获取 MongoDB 客户端连接
    """
    global _client
    if _client is None:
        _client = pymongo.MongoClient(uri)
    return _client


def get_database(db_name: str = _config["database"]["name"]) -> Database:
    """
    Get the specified database, which will be created automatically if it does not exist
    获取指定的数据库，如果不存在会自动创建
    """
    global _db
    if _db is None:
        _db = get_client().get_database(db_name)
    return _db


def get_collection(collection_name: str) -> Collection:
    """
    Get the specified collection
    获取指定的集合（Collection）
    """
    db = get_database()
    return db[collection_name]


def get_system_config() -> dict:
    """
    Get system configuration
    获取系统配置
    """
    db = get_database()
    return db["system-config"]
