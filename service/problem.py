# problem.py
from fastapi import APIRouter, HTTPException, Cookie, Request
from sse_starlette.sse import EventSourceResponse
from kafka import KafkaProducer
import asyncio

import json
from typing import List, Annotated
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import common
from common.model import *

router = APIRouter()
db = common.db.get_database()
system_config = common.db.get_system_config()
producer = KafkaProducer(
    bootstrap_servers=[system_config["kafka-broker"]],
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)


@router.post("/new")
async def new_problem(problem: Problem, cookies: Annotated[Cookies, Cookie()] = None):
    """
    Create a new problem
    创建新的题目
    """
    if not common.db.check_permission(db, sid=cookies.sid, permission="create-problem"):
        raise HTTPException(status_code=403, detail="Permission denied, create-problem")
    if problem.hiden and not common.db.check_permission(
        db, sid=cookies.sid, permission="hide-problem"
    ):
        raise HTTPException(status_code=403, detail="Permission denied, hide-problem")

    if db["problems"].find_one({"tid": problem.tid}):
        raise HTTPException(status_code=409, detail="Problem ID already exists")
    db["problems"].insert_one(problem.model_dump())
    return {"status": "success", "tid": problem.tid}


@router.post("/list")
async def list_problems(cookies: Annotated[Cookies, Cookie()] = None):
    """
    List all problems
    列出所有题目
    """
    problems = list(db["problems"].find({}))
    for problem in problems:
        if "_id" in problem:
            del problem["_id"]
        if (
            problem["hiden"] or db["contest"].find_one({"problems": problem["tid"]})
        ) and (
            not common.db.check_permission(
                db, sid=cookies.sid, permission="view-hiden-problem"
            )
        ):
            problems.remove(problem)

    return problems


@router.post("/{tid}")
async def get_problem(tid: str, cookies: Annotated[Cookies, Cookie()] = None):
    """
    Get a single problem
    获取单个题目
    """
    problem = db["problems"].find_one({"tid": tid})
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    if (problem["hiden"] or db["contest"].find_one({"problems": problem["tid"]})) and (
        not common.db.check_permission(
            db, sid=cookies.sid, permission="view-hiden-problem"
        )
    ):
        raise HTTPException(
            status_code=403, detail="Permission denied, view-hiden-problem"
        )
    if "_id" in problem:
        del problem["_id"]
    return problem


@router.post("/edit")
async def update_problem(
    problem: Problem, cookies: Annotated[Cookies, Cookie()] = None
):
    """
    Update a problem
    更新题目
    """
    if not common.db.check_permission(db, sid=cookies.sid, permission="edit-problem"):
        raise HTTPException(status_code=403, detail="Permission denied, edit-problem")
    if problem.hiden and not common.db.check_permission(
        db, sid=cookies.sid, permission="hide-problem"
    ):
        raise HTTPException(status_code=403, detail="Permission denied, hide-problem")

    if not db["problems"].find_one({"tid": problem.tid}):
        raise HTTPException(status_code=404, detail="Problem not found")

    db["problems"].update_one({"tid": problem.tid}, {"$set": problem.model_dump()})
    return {"status": "success"}


@router.post("/delete")
async def delete_problem(tid: str, cookies: Annotated[Cookies, Cookie()] = None):
    """
    Delete a problem
    删除题目
    """
    if not common.db.check_permission(db, sid=cookies.sid, permission="delete-problem"):
        raise HTTPException(status_code=403, detail="Permission denied, delete-problem")

    if not db["problems"].find_one({"tid": tid}):
        raise HTTPException(status_code=404, detail="Problem not found")

    db["problems"].delete_one({"tid": tid})
    return {"status": "success"}


@router.post("/submit")
async def submit(submission: Submission, cookies: Annotated[Cookies, Cookie()] = None):
    if (not cookies or not cookies.sid) or (
        not common.db.check_permission(db, sid=cookies.sid, permission="submit-problem")
    ):
        raise HTTPException(status_code=403, detail="Permission denied, submit-problem")

    if submission.contest_id:
        if not db["contest"].find_one({"_id": submission.contest_id}):
            raise HTTPException(status_code=404, detail="Contest not found")

    if not db["problems"].find_one({"tid": submission.problem}):
        raise HTTPException(status_code=404, detail="Problem not found")

    submission_id = db["submissions"].insert_one(submission.model_dump()).inserted_id
    producer.send(
        "submission",
        {
            "submission_id": str(submission_id),
            "problem": submission.problem,
            "author": submission.author,
            "contest_id": submission.contest_id,
        },
    )
    return {"status": "success"}


submission_clients: List[asyncio.Queue] = []


@router.post("/submission")
async def get_submission(
    submission_id: str, request: Request, cookies: Annotated[Cookies, Cookie()] = None
):
    """
    Get a single submission
    获取单个提交
    """
    if not common.db.check_permission(
        db, sid=cookies.sid, permission="view-submission"
    ):
        raise HTTPException(
            status_code=403, detail="Permission denied, view-submission"
        )

    async def submission_client(submission_id: str, request: Request):
        if await request.is_disconnected():
            return
        while True:
            submission = db["submissions"].find_one({"_id": submission_id})
            if submission["status"] != "pending" and submission["status"] != "judging":
                break
            yield submission
            await asyncio.sleep(1)
        return

    return EventSourceResponse(submission_client(submission_id, request))
