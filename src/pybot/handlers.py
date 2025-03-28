import json
import logging
from datetime import UTC, datetime, timedelta
from functools import wraps
from time import time
from typing import Any, Callable

from service import ChatGPTService, EventService, UserService
from telegram import Update
from telegram.ext import CallbackContext

from pybot.repository import FirebaseRepository


def before_request(
    handler: Callable[
        [
            'TelegramCommandHandler',
            Update,
            CallbackContext[Any, Any, Any],
        ],
        Any,
    ],
) -> Callable[[Update, CallbackContext[Any, Any, Any]], Any]:

    @wraps(handler)
    def wrapper(self: 'TelegramCommandHandler', update: Update, context: CallbackContext[Any, Any, Any]) -> None:
        username = update.message.from_user.username or str(update.message.from_user.id)
        cmd = update.message.text.split()[0][1:]  # Get the command name without the leading '/'
        if not self._check_rate_limit(username, cmd):
            update.message.reply_text('Rate limit exceeded. Try again in a minute.')
            return
        handler(self, update, context)

    return wrapper  # noqa


def after_request(
    command_name: str,
) -> Callable[[Callable[[Update, CallbackContext[Any, Any, Any]], Any]], Any]:
    """Decorator to handle post-request logging."""

    def decorator(
        handler: Callable[
            [
                'TelegramCommandHandler',
                Update,
                CallbackContext[Any, Any, Any],
            ],
            Any,
        ]
    ) -> Callable[[Update, CallbackContext[Any, Any, Any]], Any]:
        @wraps(handler)
        def wrapper(
            self: 'TelegramCommandHandler',
            update: Update,
            context: CallbackContext[Any, Any, Any],
            *args,
            **kwargs,
        ) -> None:
            username = update.message.from_user.username or str(update.message.from_user.id)
            try:
                handler(self, update, context)  # Call the original handler
                self._log_request(username, command_name, True)  # Log success
            except Exception as e:
                self.logger.error(f'Error in {command_name}: {e}')
                self._log_request(username, command_name, False)  # Log failure
                raise  # Re-raise the exception if needed

        return wrapper  # noqa

    return decorator  # noqa


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

    @before_request
    @after_request('help')
    def help(self, update: Update, _: CallbackContext[Any, Any, Any]) -> None:
        update.message.reply_text(
            'Commands: /help, /hello, /add, /register, /events, /more_events\n'
            "Example: /register gaming vr \"I enjoy fast-paced shooter games\""
        )

    @before_request
    @after_request('hello')
    def hello(self, update: Update, context: CallbackContext[Any, Any, Any]) -> None:
        reply_message = ' '.join(context.args) if context.args else 'friend'
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'Good day, {reply_message}!')

    @before_request
    @after_request('add')
    def add(self, update: Update, context: CallbackContext[Any, Any, Any]) -> None:
        try:
            msg = context.args[0]
            self.logger.info(f'Incrementing count for: {msg}')
            count = self.repo.incr(msg)
            update.message.reply_text(f'You have said {msg} for {count} times')
        except IndexError:
            update.message.reply_text('Usage: /add <keyword>')
        except Exception as e:
            self.logger.error(f'Error in add command: {e}')
            update.message.reply_text('An error occurred.')

    @before_request
    @after_request('register')
    def register(self, update: Update, context: CallbackContext[Any, Any, Any]) -> None:
        username = update.message.from_user.username or str(update.message.from_user.id)
        if not context.args:
            update.message.reply_text(
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
            update.message.reply_text('Please provide at least one interest.')
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
        update.message.reply_text(response)

    @before_request
    @after_request('events')
    def events(self, update: Update, context: CallbackContext[Any, Any, Any]) -> None:
        username = update.message.from_user.username or str(update.message.from_user.id)
        user_profile = self.user_service.get_user(username)

        if not user_profile or not user_profile.interests:
            update.message.reply_text('Please register your interests first with /register')
            return

        events = self.event_service.recommend_events(user_profile)
        if not events:
            update.message.reply_text("Sorry, I couldn't generate event recommendations right now.")
            return

        response = ['Recommended Events:'] + [
            f"{i}. {event.name} on {event.date} ({event.link})" for i, event in enumerate(events, 1)
        ]
        update.message.reply_text('\n'.join(response))

    @before_request
    @after_request('more_events')
    def more_events(self, update: Update, context: CallbackContext[Any, Any, Any]) -> None:
        username = update.message.from_user.username or str(update.message.from_user.id)
        user_profile = self.user_service.get_user(username)

        if not user_profile or not user_profile.interests:
            update.message.reply_text('Please register your interests first with /register')
            return

        events = self.event_service.recommend_more_events(user_profile)
        if not events:
            update.message.reply_text("Sorry, I couldn't generate more event recommendations right now.")
            return

        response = ['More Recommended Events:'] + [
            f"{i}. {event.name} on {event.date} ({event.link})" for i, event in enumerate(events, 1)
        ]
        update.message.reply_text('\n'.join(response))

    @before_request
    @after_request('message')
    def handle_message(self, update: Update, context: CallbackContext[Any, Any, Any]) -> None:
        reply = self.chatgpt_service.submit(update.message.text)
        self.logger.info(f'ChatGPT response: {reply}')
        context.bot.send_message(chat_id=update.effective_chat.id, text=reply)
