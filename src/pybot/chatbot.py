import logging
from typing import Self

from handlers import TelegramCommandHandler
from repository import FirebaseRepository
from service.chatgpt import ChatGPTService
from service.event import EventService
from service.user import UserService
from setting import config
from telegram.ext import CommandHandler, Dispatcher, Filters, MessageHandler, Updater


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
        self.updater = Updater(token=config.telegram.access_token, use_context=True)
        self.dispatcher = self.updater.dispatcher

    def setup_handlers(self) -> 'TelegramBot':
        self.dispatcher.add_handler(CommandHandler('help', self.command_handler.help))
        self.dispatcher.add_handler(CommandHandler('hello', self.command_handler.hello))
        self.dispatcher.add_handler(CommandHandler('add', self.command_handler.add))
        self.dispatcher.add_handler(CommandHandler('register', self.command_handler.register))
        self.dispatcher.add_handler(CommandHandler('events', self.command_handler.events))
        self.dispatcher.add_handler(CommandHandler('more_events', self.command_handler.more_events))
        self.dispatcher.add_handler(
            MessageHandler(Filters.text & (~Filters.command), self.command_handler.handle_message)
        )
        return self

    def run(self) -> Self:
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
        self.setup_handlers()
        self.updater.start_polling()
        self.updater.idle()
        return self


def main():
    bot = TelegramBot()
    bot.run()


if __name__ == '__main__':
    main()
