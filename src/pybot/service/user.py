import logging

from pybot.model import UserProfile
from pybot.repository import FirebaseRepository
from pybot.service.chatgpt import ChatGPTService


class UserService:
    def __init__(self, chatgpt_service: ChatGPTService, repo: FirebaseRepository):
        self.chatgpt_service = chatgpt_service
        self.repo = repo

    def register_user(self, username: str, interests: list[str], description: str = '') -> None:
        self.repo.save_user(
            UserProfile(
                username=username,
                interests=set(interests),
                description=description.strip(),
            )
        )

    def get_user(self, username: str) -> UserProfile:

        user_data = self.repo.get_user(username)
        return user_data if user_data else UserProfile(username=username, interests=set())

    def find_matches(self, username: str) -> list[str]:
        users_data = self.repo.get_user(username)
        if username not in users_data:
            return []

        current_user = UserProfile(**users_data[username])
        other_users = [UserProfile(**data) for u, data in users_data.items() if u != username]
        if not other_users:
            return []

        prompt = (
            'You are a matchmaking assistant. I have a user with the following profile:\n'
            f"Interests: {', '.join(current_user.interests)}\n"
            f"Description: {current_user.description or 'No additional context provided.'}\n\n"
            'Here are other user profiles:\n'
        )
        for i, user in enumerate(other_users, 1):
            prompt += (
                f'User {i}:\n'
                f"Interests: {', '.join(user.interests)}\n"
                f"Description: {user.description or 'No additional context provided.'}\n"
            )
        prompt += (
            '\nBased on the interests and descriptions, suggest up to 3 users who are the best matches '
            'for the first user. Provide their user numbers (e.g., User 1, User 2) and a brief reason '
            'for each match. Format your response as:\n'
            '- User X: [reason]\n'
            '- User Y: [reason]\n'
            '- User Z: [reason]'
        )

        response = self.chatgpt_service.submit(prompt)
        if 'Error' in response:
            return []

        matches = []
        try:
            for line in response.strip().split('\n'):
                if line.startswith('- User'):
                    user_num = int(line.split(':')[0].split('User')[1].strip()) - 1
                    if 0 <= user_num < len(other_users):
                        matches.append(other_users[user_num].username)
        except Exception as e:
            logging.error(f'Error parsing matches: {e}')
            return []

        return matches
    
    def add_interest(self, username: str, interest: list[str])-> None:
        user = self.get_user(username)
        user.interests = user.interests.union(set(interest))
        self.repo.save_user(user)