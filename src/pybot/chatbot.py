from typing import Self

import pytz
from handlers import TelegramCommandHandler
from repository import FirebaseRepository
from service.chatgpt import ChatGPTService
from service.event import EventService
from service.user import UserService
from setting import config
from telegram import BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, JobQueue, MessageHandler, filters


class TelegramBot:
    def __init__(self):
        self.config = config
        self.chatgpt_service = ChatGPTService(config.chatgpt)
        self.firebase_repo = FirebaseRepository()
        self.user_service = UserService(self.chatgpt_service, self.firebase_repo)
        self.event_service = EventService(self.chatgpt_service, self.firebase_repo)
        self.command_handler = TelegramCommandHandler(
            self.firebase_repo,
            self.chatgpt_service,
            self.user_service,
            self.event_service,
        )
        job_queue = JobQueue()
        job_queue.scheduler.configure(timezone=pytz.UTC)

        self.app = ApplicationBuilder().token(config.telegram.access_token).job_queue(job_queue).build()

    def setup_handlers(self):
        self.app.add_handler(CommandHandler('start', self.command_handler.start))
        self.app.add_handler(CommandHandler('help', self.command_handler.help))
        self.app.add_handler(CommandHandler('hello', self.command_handler.hello))
        self.app.add_handler(CommandHandler('add', self.command_handler.add))
        self.app.add_handler(CommandHandler('register', self.command_handler.register))
        self.app.add_handler(CommandHandler('events', self.command_handler.events))
        self.app.add_handler(CommandHandler('more_events', self.command_handler.more_events))
        self.app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.command_handler.handle_message))

    async def set_bot_commands(self, app) -> Self:
        commands = [
            BotCommand('help', '查看帮助'),
            BotCommand('hello', '向 Bot 打招呼'),
            BotCommand('register', '注册你自己'),
            BotCommand('add', '添加推荐内容'),
            BotCommand('events', '查看推荐的事情'),
            BotCommand('more_events', '查看更多推荐'),
        ]
        await app.bot.set_my_commands(commands)
        return self

    def run(self):
        self.setup_handlers()
        self.app.post_init = self.set_bot_commands
        self.app.run_webhook(
            listen='0.0.0.0',
            port=self.config.app_port,
            url_path=self.config.telegram.access_token,
            webhook_url=f"{self.config.app_url}/{self.config.telegram.access_token}",
        )
