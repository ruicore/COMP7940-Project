import configparser
import os
from enum import StrEnum

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class TelegramConfig(BaseModel):
    access_token: str


class ChatGPTConfig(BaseModel):
    basicurl: str
    modelname: str
    apiversion: str
    access_token: str


class RedisConfig(BaseModel):
    host: str
    port: int
    password: str | None = None
    ssl: bool = False
    username: str | None = None
    decode_responses: bool = True


class AppConfig(BaseSettings):
    telegram: TelegramConfig
    chatgpt: ChatGPTConfig
    redis: RedisConfig
    app_url: str
    app_port: int = Field(alias='PORT')

    @classmethod
    def from_ini(cls, file: str = '.ini') -> 'AppConfig':
        parser = configparser.ConfigParser()
        parser.read(file)
        data = {s.lower(): dict(parser.items(s)) for s in parser.sections()}

        for key in ['TELEGRAM_ACCESS_TOKEN', 'CHATGPT_ACCESS_TOKEN', 'REDIS_PASSWORD']:
            pre, post = key.lower().split('_', 1)
            data.setdefault(pre, {})[post] = os.environ.get(key, data.get(pre, {}).get(post))  # type: ignore

        return cls(**data)


config = AppConfig.from_ini()
