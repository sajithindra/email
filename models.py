from typing import Optional
from pydantic import BaseModel


class UserUpdate(BaseModel):
    id: str
    first_name: str
    last_name: str
    username: str


class User(BaseModel):
    first_name: str
    last_name: str
    username: str
    email_id: str
    password: str


class SentModel(BaseModel):
    from_email: str
    to_email: list
    cc: list
    bcc: list


class Email(BaseModel):
    sent: dict = {
        "from_email": "",
        "to_email": [],
        "cc": [],
        "bcc": [],
    },
    subject: Optional[str] = ""
    body: str


class EmailReply(BaseModel):
    parent_id: str
    from_email: str
    subject: Optional[str] = ""
    body: str
