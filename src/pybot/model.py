from pydantic import BaseModel


class UserProfile(BaseModel):
    username: str
    interests: set[str]
    description: str = ''


class Event(BaseModel):
    name: str
    date: str
    link: str
