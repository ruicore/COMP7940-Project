import logging
import asyncio
from pybot.chatbot import TelegramBot

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


async def main():
    bot = TelegramBot()
    await bot.run()


if __name__ == '__main__':
    asyncio.run(main())
