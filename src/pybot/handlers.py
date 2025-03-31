import logging
from functools import wraps
from typing import Any, Callable

from service import ChatGPTService, EventService, UserService
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from pybot.model import Command
from pybot.repository import FirebaseRepository


def before_request(
    handler: Callable[
        [
            'TelegramCommandHandler',
            Update,
            ContextTypes.DEFAULT_TYPE,
        ],
        Any,
    ],
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Any]:

    @wraps(handler)
    async def wrapper(self: 'TelegramCommandHandler', update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        username = user.username or str(user.id)
        cmd = update.message.text.split()[0][1:]  # Get the command name without the leading '/'
        if not self._check_rate_limit(username, cmd):
            await update.message.reply_text('Rate limit exceeded. Try again in a minute.')
            return
        await handler(self, update, context)

    return wrapper


def after_request(
    command_name: str,
) -> Callable[[Callable[[Update, ContextTypes.DEFAULT_TYPE], Any]], Any]:
    def decorator(
        handler: Callable[
            [
                'TelegramCommandHandler',
                Update,
                ContextTypes.DEFAULT_TYPE,
            ],
            Any,
        ]
    ) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Any]:
        @wraps(handler)
        async def wrapper(
            self: 'TelegramCommandHandler',
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            *args,
            **kwargs,
        ) -> None:
            user = update.effective_user
            username = user.username or str(user.id)
            try:
                await handler(self, update, context)
                self._log_request(username, command_name, True)
            except Exception as e:
                self.logger.error(f'Error in {command_name}: {e}')
                self._log_request(username, command_name, False)
                raise

        return wrapper

    return decorator


class TelegramCommandHandler:
    def __init__(
        self,
        repo: FirebaseRepository,
        chatgpt_service: ChatGPTService,
        user_service: UserService,
        event_service: EventService,
    ):
        self.repo = repo
        self.chatgpt_service = chatgpt_service
        self.user_service = user_service
        self.event_service = event_service
        self.logger = logging.getLogger(__name__)

    def _check_rate_limit(self, username: str, cmd: str) -> bool:
        return self.repo.check_rate_limit(username, cmd)

    def _log_request(self, username: str, command: str, success: bool) -> None:
        self.repo.log_request(username, command, success)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        type_ = query.data
        chat_id = query.message.chat.id
        await query.answer()

        match type_:
            case Command.REGISTER:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Usage: /register <interests> [\"description\"] (e.g., \n/register gaming vr \"I enjoy FPS games\")",
                )
            case Command.EVENTS:
                await self.events(update, context)
            case Command.STORE:
                await context.bot.send_message(chat_id=chat_id, text='Usage: /add <keyword>')
            case Command.OPENAI:
                await context.bot.send_message(chat_id=chat_id, text='Usage: /openai <message>')
            case Command.HELP:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text='Commands: /help, /add, /register, /events, /openai\n'
                    'Example: /register gaming vr "I enjoy fast-paced shooter games"',
                )
            case _:
                await context.bot.send_message(chat_id=chat_id, text='⚠️ Unknown command. Please try again.')

    @staticmethod
    async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            (
                f"👋 Hello, {update.effective_user.first_name}! \n"
                f"I am your smart recommendation assistant. \n"
                f"Please select the function you want to use"
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton('📝 Register', callback_data=Command.REGISTER),
                        InlineKeyboardButton('🎯 Events', callback_data=Command.EVENTS),
                    ],
                    [
                        InlineKeyboardButton('➕ Add', callback_data=Command.STORE),
                        InlineKeyboardButton('🤖 OpenAI', callback_data=Command.OPENAI),
                    ],
                    [
                        InlineKeyboardButton('❓ Help', callback_data=Command.HELP),
                    ],
                ]
            ),
        )

    @before_request
    @after_request(Command.HELP)
    async def help(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            'Commands: /help, /hello, /add, /register, /events, /more_events\n'
            "Example: /register gaming vr \"I enjoy fast-paced shooter games\""
        )

    @before_request
    @after_request(Command.HELLO)
    async def hello(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        reply_message = ' '.join(context.args) if context.args else 'friend'
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Good day, {reply_message}!')

    @before_request
    @after_request(Command.OPENAI)
    async def openai(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not context.args:
            await update.message.reply_text('Usage: /openai <message>')
            return

        message = ' '.join(context.args)
        self.logger.info(f'OpenAI message: {message}')
        reply = self.chatgpt_service.submit(message)
        self.logger.info(f'OpenAI response: {reply}')
        await context.bot.send_message(chat_id=update.effective_chat.id, text=reply)

    @before_request
    @after_request(Command.STORE)
    async def add(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            msg = context.args[0]
            self.logger.info(f'Incrementing count for: {msg}')
            count = self.repo.incr(msg)
            await update.message.reply_text(f'You have said {msg} for {count} times')
        except IndexError:
            await update.message.reply_text('Usage: /add <keyword>')
        except Exception as e:
            self.logger.error(f'Error in add command: {e}')
            await update.message.reply_text('An error occurred.')

    @before_request
    @after_request(Command.REGISTER)
    async def register(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        username = update.message.from_user.username or str(update.message.from_user.id)
        if not context.args:
            await update.message.reply_text(
                "Usage: /register <interests> [\"description\"] (e.g., /register gaming vr \"I enjoy FPS games\")"
            )
            return

        args = context.args
        interests = []
        description = ''
        for i, arg in enumerate(args):
            if arg.startswith('"') and arg.endswith('"'):
                description = arg[1:-1]
                interests = args[:i]
                break
            elif arg.startswith('"'):
                description = ' '.join(args[i:])[1:-1]
                interests = args[:i]
                break
            interests.append(arg)

        if not interests:
            await update.message.reply_text('Please provide at least one interest.')
            return

        self.user_service.register_user(username, interests, description)
        matches = self.user_service.find_matches(username)

        response = f"Registered interests: {', '.join(interests)}"
        if description:
            response += f'\nDescription: {description}'
        response += '\n'
        if matches:
            response += f"Matched users: {', '.join(matches)}"
        else:
            response += 'No matches found yet. Invite friends to join!'
        await update.message.reply_text(response)

    @before_request
    @after_request(Command.EVENTS)
    async def events(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        username = update.message.from_user.username or str(update.message.from_user.id)
        user_profile = self.user_service.get_user(username)

        if not user_profile or not user_profile.interests:
            await update.message.reply_text('Please register your interests first with /register')
            return

        events = self.event_service.recommend_events(user_profile)
        if not events:
            await update.message.reply_text("Sorry, I couldn't generate event recommendations right now.")
            return

        response = ['Recommended Events:'] + [
            f"{i}. {event.name} on {event.date} ({event.link})" for i, event in enumerate(events, 1)
        ]
        await update.message.reply_text('\n'.join(response))

    @before_request
    @after_request('more_events')
    async def more_events(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        username = update.message.from_user.username or str(update.message.from_user.id)
        user_profile = self.user_service.get_user(username)

        if not user_profile or not user_profile.interests:
            await update.message.reply_text('Please register your interests first with /register')
            return

        events = self.event_service.recommend_more_events(user_profile)
        if not events:
            await update.message.reply_text("Sorry, I couldn't generate more event recommendations right now.")
            return

        response = ['More Recommended Events:'] + [
            f"{i}. {event.name} on {event.date} ({event.link})" for i, event in enumerate(events, 1)
        ]
        await update.message.reply_text('\n'.join(response))

    @before_request
    @after_request(Command.MESSAGE)
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        if message.chat.type in ['group', 'supergroup']:
            bot_username = context.bot.username
            if f"@{bot_username}" not in message.text:
                return

        reply = self.chatgpt_service.submit(message.text)
        self.logger.info(f'ChatGPT response: {reply}')
        await context.bot.send_message(chat_id=message.chat.id, text=reply)
