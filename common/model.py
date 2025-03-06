from pydantic import BaseModel

from typing import Union


class Cookies(BaseModel):
    sid: Union[str, None] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordResetRequest(BaseModel):
    username: str
    origin_password: str
    new_password: str


class User(BaseModel):
    username: str
    email: str
    bio: Union[str, None] = None
    nickname: Union[str, None] = None
    password: str
    phone_number: Union[str, None] = None
    school_or_company: Union[str, None] = None
    introduction: Union[str, None] = None
    permissions: str = None


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


class Discussion(BaseModel):
    title: str
    author: str
    content: str
    tags: Union[list, None] = []
    comments: Union[list, None] = []
    top: bool = False
    highlight: bool = False


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
