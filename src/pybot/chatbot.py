from typing import Self

import pytz
from handlers import TelegramCommandHandler
from repository import FirebaseRepository
from service.chatgpt import ChatGPTService
from service.event import EventService
from service.user import UserService
from setting import config
from telegram import BotCommand
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, JobQueue, MessageHandler, filters

from pybot.model import Command


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
        self.app.add_handler(CommandHandler(Command.START, self.command_handler.start))
        self.app.add_handler(CallbackQueryHandler(self.command_handler.handle_callback))
        self.app.add_handler(CommandHandler(Command.HELP, self.command_handler.help))
        self.app.add_handler(CommandHandler(Command.HELLO, self.command_handler.hello))
        self.app.add_handler(CommandHandler(Command.ADD_INTEREST, self.command_handler.add))
        self.app.add_handler(CommandHandler(Command.REGISTER, self.command_handler.register))
        self.app.add_handler(CommandHandler(Command.EVENTS, self.command_handler.events))
        self.app.add_handler(CommandHandler(Command.OPENAI, self.command_handler.openai))
        self.app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.command_handler.handle_message))

    async def set_bot_commands(self, app) -> Self:
        commands = [
            BotCommand(Command.START, 'Start the bot'),
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
