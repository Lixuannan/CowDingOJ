# discussion.py
from fastapi import APIRouter, HTTPException, Cookie
from typing import Annotated
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import common
from common.model import *

router = APIRouter()
db = common.db.get_database()
system_config = common.db.get_system_config()


@router.post("/new")
async def new_discussion(
    discussion: Discussion, cookies: Annotated[Cookies, Cookie()] = None
):
    """
    Create a new discussion
    创建新的讨论
    """
    if not db["sessions"].find_one({"sid": cookies.sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not common.db.check_permission(
        db, sid=cookies.sid, permission="create-discussion"
    ):
        raise HTTPException(
            status_code=403, detail="Permission denied, create-discussion"
        )
    if discussion.highlight and not common.db.check_permission(
        db, sid=cookies.sid, permission="highlight-discussion"
    ):
        raise HTTPException(
            status_code=403, detail="Permission denied, highlight-discussion"
        )
    if discussion.top and not common.db.check_permission(
        db, sid=cookies.sid, permission="top-discussion"
    ):
        raise HTTPException(status_code=403, detail="Permission denied, top-discussion")

    db["discussions"].insert_one(discussion.model_dump())
    discussion_id = str(db["discussions"].find_one({"title": discussion.title})["_id"])
    return {"status": "success", "discuss_id": discussion_id}


@router.post("/list")
async def list_discussions(cookies: Annotated[Cookies, Cookie()] = None):
    """
    List all discussions
    列出所有讨论
    """
    if not db["sessions"].find_one({"sid": cookies.sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not common.db.check_permission(
        db, sid=cookies.sid, permission="view-discussion"
    ):
        raise HTTPException(
            status_code=403, detail="Permission denied, view-discussion"
        )

    discussions = list(db["discussions"].find({}))
    for discussion in discussions:
        discussion["_id"] = str(discussion["_id"])
        del discussion["comments"]
        del discussion["content"]
    return discussions


@router.post("/{discussion_id}")
async def get_discussion(
    discussion_id: str, cookies: Annotated[Cookies, Cookie()] = None
):
    """
    Get a single discussion
    获取单个讨论
    """
    if not db["sessions"].find_one({"sid": cookies.sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not common.db.check_permission(
        db, sid=cookies.sid, permission="view-discussion"
    ):
        raise HTTPException(
            status_code=403, detail="Permission denied, view-discussion"
        )

    discussion = db["discussions"].find_one({"_id": common.ObjectId(discussion_id)})
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")
    discussion["_id"] = str(discussion["_id"])
    return discussion


@router.post("/update")
async def update_discussion(
    discussion_id: str,
    discussion: Discussion,
    cookies: Annotated[Cookies, Cookie()] = None,
):
    """
    Update a discussion
    更新讨论
    """
    if not common.db.check_permission(
        db, sid=cookies.sid, permission="update-discussion"
    ):
        raise HTTPException(
            status_code=403, detail="Permission denied, update-discussion"
        )
    if discussion.highlight and not common.db.check_permission(
        db, sid=cookies.sid, permission="highlight-discussion"
    ):
        raise HTTPException(
            status_code=403, detail="Permission denied, highlight-discussion"
        )
    if discussion.top and not common.db.check_permission(
        db, sid=cookies.sid, permission="top-discussion"
    ):
        raise HTTPException(status_code=403, detail="Permission denied, top-discussion")
    if not db["discussions"].find_one({"_id": common.ObjectId(discussion_id)}):
        raise HTTPException(status_code=404, detail="Discussion not found")
    db["discussions"].update_one(
        {"_id": common.ObjectId(discussion_id)}, {"$set": discussion.model_dump()}
    )
    return {"status": "success", "discussion_id": discussion_id}


@router.post("/delete/{discussion_id}")
async def delete_discussion(
    discussion_id: str, cookies: Annotated[Cookies, Cookie()] = None
):
    """
    Delete a discussion
    删除讨论
    """
    if not db["discussions"].find_one({"_id": common.ObjectId(discussion_id)}):
        raise HTTPException(status_code=404, detail="Discussion not found")
    if not common.db.check_permission(
        db, sid=cookies.sid, permission="delete-discussion"
    ):
        raise HTTPException(
            status_code=403, detail="Permission denied, delete-discussion"
        )

    db["discussions"].delete_one({"_id": common.ObjectId(discussion_id)})
    return {"status": "success"}


@router.post("/comment")
async def comment_discussion(
    discussion_id: str, comment: str, cookies: Annotated[Cookies, Cookie()] = None
):
    """
    Comment on a discussion
    评论讨论
    """
    if not db["discussions"].find_one({"_id": common.ObjectId(discussion_id)}):
        raise HTTPException(status_code=404, detail="Discussion not found")
    if not common.db.check_permission(
        db, sid=cookies.sid, permission="comment-discussion"
    ):
        raise HTTPException(
            status_code=403, detail="Permission denied, comment-discussion"
        )

    db["discussions"].update_one(
        {"_id": common.ObjectId(discussion_id)},
        {"$push": {"comments": {"author": cookies.sid, "content": comment}}},
    )
    return {"status": "success"}
