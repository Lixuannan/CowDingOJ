# problem.py
from fastapi import APIRouter, HTTPException, Cookie, Request
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from kafka import KafkaProducer
import asyncio

import json
from typing import Union, List

import common

router = APIRouter()
db = common.db.get_database()
system_config = common.db.get_system_config()
producer = KafkaProducer(
    bootstrap_servers=[system_config["kafka-broker"]],
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)


class Problem(BaseModel):
    tid: str
    title: str
    author: str
    hiden: bool
    tags: Union[list, None] = []
    background: Union[str, None] = None
    description: str
    input_description: str
    output_description: str
    samples: Union[list, None] = []
    judge_config: Union[dict, None] = {}
    hint: str
    source: str
    difficulty: int


@router.post("/new")
async def new_problem(problem: Problem, sid: str = Cookie(None)):
    """
    Create a new problem
    创建新的题目
    """
    if not db["sessions"].find_one({"sid": sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not common.db.check_permission(db, sid=sid, permission="create-problem"):
        raise HTTPException(status_code=403, detail="Permission denied, create-problem")
    if problem.hiden and not common.db.check_permission(
        db, sid=sid, permission="hide-problem"
    ):
        raise HTTPException(status_code=403, detail="Permission denied, hide-problem")

    if db["problems"].find_one({"tid": problem.tid}):
        raise HTTPException(status_code=409, detail="Problem ID already exists")
    db["problems"].insert_one(problem.model_dump())
    return {"status": "success", "tid": problem.tid}


@router.get("/list")
async def list_problems(sid: str = Cookie(None)):
    """
    List all problems
    列出所有题目
    """
    problems = list(db["problems"].find({}))
    for problem in problems:
        if "_id" in problem:
            del problem["_id"]
        if problem["hiden"] and not common.db.check_permission(
            db, sid=sid, permission="view-hiden-problem"
        ):
            problems.remove(problem)

    return problems


@router.get("/{tid}")
async def get_problem(tid: str, sid: str = Cookie(None)):
    """
    Get a single problem
    获取单个题目
    """
    problem = db["problems"].find_one({"tid": tid})
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    if problem["hiden"] and not common.db.check_permission(
        db, sid=sid, permission="view-hiden-problem"
    ):
        raise HTTPException(
            status_code=403, detail="Permission denied, view-hiden-problem"
        )
    if "_id" in problem:
        del problem["_id"]
    return problem


@router.post("/edit")
async def update_problem(problem: Problem, sid: str = Cookie(None)):
    """
    Update a problem
    更新题目
    """
    if not db["sessions"].find_one({"sid": sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not common.db.check_permission(db, sid=sid, permission="edit-problem"):
        raise HTTPException(status_code=403, detail="Permission denied, edit-problem")
    if problem.hiden and not common.db.check_permission(
        db, sid=sid, permission="hide-problem"
    ):
        raise HTTPException(status_code=403, detail="Permission denied, hide-problem")

    if not db["problems"].find_one({"tid": problem.tid}):
        raise HTTPException(status_code=404, detail="Problem not found")

    db["problems"].update_one({"tid": problem.tid}, {"$set": problem.model_dump()})
    return {"status": "success"}


@router.post("/delete")
async def delete_problem(tid: str, sid: str = Cookie(None)):
    """
    Delete a problem
    删除题目
    """
    if not db["sessions"].find_one({"sid": sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not common.db.check_permission(db, sid=sid, permission="delete-problem"):
        raise HTTPException(status_code=403, detail="Permission denied, delete-problem")

    if not db["problems"].find_one({"tid": tid}):
        raise HTTPException(status_code=404, detail="Problem not found")

    db["problems"].delete_one({"tid": tid})
    return {"status": "success"}


@router.post("/submit_code")
async def submit_problem(tid: str, code: str, sid: str = Cookie(None)):
    """
    Submit a solution to a problem
    提交题目解答
    """
    if not db["sessions"].find_one({"sid": sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not db["problems"].find_one({"tid": tid}):
        raise HTTPException(status_code=404, detail="Problem not found")
    if not common.db.check_permission(db, sid=sid, permission="submit-problem"):
        raise HTTPException(status_code=403, detail="Permission denied, submit-problem")

    if not code:
        raise HTTPException(status_code=400, detail="Code cannot be empty")

    result = db["submissions"].insert_one(
        {
            "tid": tid,
            "code": code,
            "status": "pending",
            "score": None,
            "timestamp": common.get_timestamp(),
        }
    )

    producer.send(
        "submission-queue",
        {"submission_id": result.inserted_id},
    )
    producer.flush()

    return {"status": "success", "submission_id": result.inserted_id}


@router.post("submit_file")
async def submit_file(tid: str, file_id: str, sid: str = Cookie(None)):
    """
    Submit a file to a problem
    提交文件
    """
    if not db["sessions"].find_one({"sid": sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not db["problems"].find_one({"tid": tid}):
        raise HTTPException(status_code=404, detail="Problem not found")
    if not common.db.check_permission(db, sid=sid, permission="submit-problem"):
        raise HTTPException(status_code=403, detail="Permission denied, submit-problem")

    if not file_id:
        raise HTTPException(status_code=400, detail="File cannot be empty")

    result = db["submissions"].insert_one(
        {
            "tid": tid,
            "file_id": file_id,
            "status": "pending",
            "score": None,
            "testcases": [],
            "timestamp": common.get_timestamp(),
        }
    )

    producer.send(
        "submission-queue",
        {"submission_id": result.inserted_id},
    )
    producer.flush()

    return {"status": "success", "submission_id": result.inserted_id}


submission_clients: List[asyncio.Queue] = []


@router.post("/submission")
async def get_submission(submission_id: str, request: Request, sid: str = Cookie(None)):
    """
    Get a single submission
    获取单个提交
    """
    if not db["sessions"].find_one({"sid": sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not common.db.check_permission(db, sid=sid, permission="view-submission"):
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
        return submission

    return EventSourceResponse(submission_client(submission_id, request))
