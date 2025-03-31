from enum import StrEnum

from pydantic import BaseModel


class UserProfile(BaseModel):
    username: str
    interests: set[str]
    description: str = ''


class Event(BaseModel):
    name: str
    date: str
    link: str


class Command(StrEnum):
    START = 'start'
    HELP = 'help'
    EVENTS = 'events'
    REGISTER = 'register'
    OPENAI = 'openai'
    MESSAGE = 'message'
    STORE = 'store'
    HELLO = 'hello'
