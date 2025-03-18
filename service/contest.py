# contest.py
from fastapi import APIRouter, HTTPException, Cookie
from typing import Annotated
import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import common
from common.model import *

router = APIRouter()
db = common.db.get_database()
system_config = common.db.get_system_config()


@router.post("/new")
async def new(info: Contest, cookies: Annotated[Cookies, Cookie()] = None):
    if not db["sessions"].find_one({"sid": cookies.sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not common.db.check_permission(db, sid=cookies.sid, permission="create-contest"):
        raise HTTPException(status_code=403, detail="Permission denied, create-contest")

    db["contest"].insert_one(info.model_dump())
    return {"status": "success"}


@router.post("/list")
async def get(cookies: Annotated[Cookies, Cookie()] = None):
    if not db["sessions"].find_one({"sid": cookies.sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    contest = list(db["contest"].find())
    for i in contest:
        i["_id"] = str(i["_id"])
        del i["files"]
        del i["problems"]
    return {"status": "success", "data": contest}


@router.post("/{contest_id}")
async def get_contest(contest_id: str, cookies: Annotated[Cookies, Cookie()] = None):
    if not db["sessions"].find_one({"sid": cookies.sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not common.db.check_permission(db, sid=cookies.sid, permission="view-contest"):
        raise HTTPException(status_code=403, detail="Permission denied, view-contest")
    contest = db["contest"].find_one({"contest_id": contest_id})
    if not contest:
        raise HTTPException(status_code=404, detail="Contest not found")
    del contest["_id"]

    user = db["users"].find_one({"sid": cookies.sid})["username"]

    if (
        not common.db.check_permission(db, sid=cookies.sid, permission="edit-contest")
    ) and (
        time.localtime() < contest["begin_time"]
        or user not in contest["contest_members"]
    ):
        del contest["files"]
        del contest["problems"]

    return {"status": "success", "data": contest}


@router.post("/{contest_id}/edit")
async def edit_contest(
    contest_id: str, info: Contest, cookies: Annotated[Cookies, Cookie()] = None
):
    if not db["sessions"].find_one({"sid": cookies.sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not common.db.check_permission(db, sid=cookies.sid, permission="edit-contest"):
        raise HTTPException(status_code=403, detail="Permission denied, edit-contest")
    if not db["contest"].find_one({"contest_id": contest_id}):
        raise HTTPException(status_code=404, detail="Contest not found")

    db["contest"].update_one({"contest_id": contest_id}, {"$set": info.model_dump()})


@router.post("/{contest_id}/delete")
async def delete_contest(contest_id: str, cookies: Annotated[Cookies, Cookie()] = None):
    if not db["sessions"].find_one({"sid": cookies.sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not common.db.check_permission(db, sid=cookies.sid, permission="delete-contest"):
        raise HTTPException(status_code=403, detail="Permission denied, delete-contest")
    if not db["contest"].find_one({"contest_id": contest_id}):
        raise HTTPException(status_code=404, detail="Contest not found")

    db["contest"].delete_one({"contest_id": contest_id})

    return {"status": "success"}


@router.post("/{contest_id}/join")
async def join_contest(contest_id: str, cookies: Annotated[Cookies, Cookie()] = None):
    if not db["sessions"].find_one({"sid": cookies.sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not common.db.check_permission(db, sid=cookies.sid, permission="view-contest"):
        raise HTTPException(status_code=403, detail="Permission denied, view-contest")
    if not db["contest"].find_one({"contest_id": contest_id}):
        raise HTTPException(status_code=404, detail="Contest not found")

    user = db["users"].find_one({"sid": cookies.sid})["username"]
    contest = db["contest"].find_one({"contest_id": contest_id})

    if user in contest["contest_members"]:
        raise HTTPException(status_code=403, detail="Already joined")

    db["contest"].update_one(
        {"contest_id": contest_id}, {"$push": {"contest_members": user}}
    )

    return {"status": "success"}


@router.post("/{contest_id}/scoreboard")
async def get_scoreboard(contest_id: str, cookies: Annotated[Cookies, Cookie()] = None):
    if not db["sessions"].find_one({"sid": cookies.sid}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not common.db.check_permission(db, sid=cookies.sid, permission="view-contest"):
        raise HTTPException(status_code=403, detail="Permission denied, view-contest")
    contest = db["contest"].find_one({"contest_id": contest_id})
    if not contest:
        raise HTTPException(status_code=404, detail="Contest not found")
    if (
        contest["rule"] == "OI"
        and time.localtime() < contest["end_time"]
        and not common.db.check_permission(
            db, sid=cookies.sid, permission="edit-contest"
        )
    ):
        raise HTTPException(status_code=403, detail="Permission denied, edit-contest")
    if time.localtime() < contest["begin_time"]:
        raise HTTPException(status_code=403, detail="Contest not started")

    scoreboard = []
    for i in contest["contest_members"]:
        scoreboard.append(
            {
                "username": i,
                "problems": {},
            }
        )
    submissions = list(
        db["submissions"].find({"contest_id": contest_id}).sort("timestamp", 1)
    )
    for submission in submissions:
        if contest["rule"] == "IOI":
            scoreboard[submission["author"]]["problems"][submission["problem"]][
                "score"
            ] = max(
                (
                    0
                    if scoreboard[submission["author"]]["problems"][
                        submission["problem"]
                    ]["score"]
                    is None
                    else scoreboard[submission["author"]]["problems"][
                        submission["problem"]
                    ]["score"]
                ),
                submission["score"],
            )
        elif contest["rule"] == "OI":
            scoreboard[submission["author"]]["problems"][submission["problem"]][
                "score"
            ] = submission["score"]
        elif contest["rule"] == "ACM":
            if (
                scoreboard[submission["author"]]["problems"][submission["problem"]][
                    "status"
                ]
                == "Accepted"
            ):
                continue
            scoreboard[submission["author"]]["problems"][submission["problem"]][
                "status"
            ] = submission["status"]
            if submission["status"] == "Accepted":
                scoreboard[submission["author"]]["problems"][submission["problem"]][
                    "time"
                ] = (submission["timestamp"] - contest["begin_time"])
            else:
                scoreboard[submission["author"]]["problems"][submission["problem"]][
                    "penalty"
                ] = (
                    0
                    if scoreboard[submission["author"]]["problems"][
                        submission["problem"]
                    ]["penalty"]
                    is None
                    else scoreboard[submission["author"]]["problems"][
                        submission["problem"]
                    ]["penalty"]
                ) + 20

    return {"status": "success", "scoreboard": scoreboard}
