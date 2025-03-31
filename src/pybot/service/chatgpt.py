import requests

from pybot.setting import ChatGPTConfig


class ChatGPTService:
    def __init__(self, config: ChatGPTConfig):
        self.config = config
        self.url = f'{config.basicurl}/deployments/{config.modelname}/chat/completions/?api-version={config.apiversion}'
        self.headers = {'Content-Type': 'application/json', 'api-key': config.access_token}

    def submit(self, message: str) -> str:
        try:
            response = requests.post(
                self.url,
                json={
                    'messages': [
                        {
                            'role': 'user',
                            'content': message,
                        }
                    ]
                },
                headers=self.headers,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except requests.RequestException as e:
            return f'Error: {str(e)}'
