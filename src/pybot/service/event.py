import logging

from pybot.model import Event, UserProfile
from pybot.repository import FirebaseRepository
from pybot.service.chatgpt import ChatGPTService


class EventService:
    def __init__(self, chatgpt_service: ChatGPTService, repo: FirebaseRepository):
        self.chatgpt_service = chatgpt_service
        self.repo = repo

    def recommend_events(self, user_profile: UserProfile) -> list[Event]:
        if not user_profile.interests:
            return []

        interests_str = ', '.join(user_profile.interests)
        prompt = (
            'You are an event planner. Generate a list of 3 fictional online events tailored to a user with the following profile:\n'
            f'Interests: {interests_str}\n'
            f"Description: {user_profile.description or 'No additional context provided.'}\n\n"
            'For each event, include the event name, date (in 2025), and a fake URL. '
            "Ensure the events align with the user's specific preferences. "
            'Format your response as a numbered list like this:\n'
            '1. Event Name - Date - URL\n'
            '2. Event Name - Date - URL\n'
            '3. Event Name - Date - URL'
        )

        events = self._parse_events(self.chatgpt_service.submit(prompt))
        if events:
            self.repo.save_events(user_profile.username, events)
        return events

    def recommend_more_events(self, user_profile: UserProfile) -> list[Event]:
        if not user_profile.interests:
            return []

        past_events = self.repo.get_past_events(user_profile.username, 10)
        past_events_str = ', '.join([event.name for event in past_events]) if past_events else 'none'

        logging.error(f'Past events: {past_events_str}')
        interests_str = ', '.join(user_profile.interests)
        prompt = (
            'You are an event planner. Generate a list of 3 new fictional online events tailored to a user with the following profile:\n'
            f'Interests: {interests_str}\n'
            f"Description: {user_profile.description or 'No additional context provided.'}\n\n"
            "For each event, include the event name, date (in 2025), and a fake URL. Ensure the events align with the user's specific preferences "
            f'and are different from these previously suggested events: {past_events_str}. '
            'Format your response as a numbered list like this:\n'
            '1. Event Name - Date - URL\n'
            '2. Event Name - Date - URL\n'
            '3. Event Name - Date - URL'
        )

        events = self._parse_events(self.chatgpt_service.submit(prompt))
        if events:
            self.repo.save_events(user_profile.username, events)
        return events

    def _parse_events(self, response: str) -> list[Event]:
        if 'Error' in response:
            return []

        events = []
        try:
            for line in response.strip().split('\n'):
                if line.strip() and line[0].isdigit():
                    parts = line.split(' - ')
                    if not len(parts) == 3:
                        continue
                    name, date, url = parts
                    events.append(
                        Event(
                            **{
                                'name': name[3:].strip(),
                                'date': date.strip(),
                                'link': url.strip(),
                            }
                        )
                    )
        except Exception as e:
            logging.error(f'Error parsing events: {e}')
            return []

        return events
