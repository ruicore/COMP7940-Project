import logging

from pybot.chatbot import TelegramBot

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def main():
    bot = TelegramBot()
    bot.run()


if __name__ == '__main__':
    main()
