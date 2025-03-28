import os
import tempfile
from datetime import UTC, datetime

import firebase_admin
from firebase_admin import credentials, firestore


class FirebaseRepository:
    def __init__(self):
        cred_json = os.environ.get('GOOGLE_CREDENTIALS')
        if not cred_json:
            raise RuntimeError('Missing GOOGLE_CREDENTIALS env var')

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
            tmp.write(cred_json)
            cred_path = tmp.name

        firebase_admin.initialize_app(credentials.Certificate(cred_path))

        self.db = firestore.client()
        self.users = self.db.collection('users')
        self.rate_limits = self.db.collection('rate_limits')
        self.request_logs = self.db.collection('request_logs')

    def save_user(self, user: dict) -> None:
        name = user['name']
        self.users.document(name).set(user)

    def get_user(self, name: str) -> dict | None:
        doc = self.users.document(name).get()
        return doc.to_dict() if doc.exists else None

    def incr(self, key: str) -> int:
        doc = self.rate_limits.document(key).get()
        if doc.exists:
            data = doc.to_dict()
            count = data.get('count', 0) + 1
        else:
            count = 1

        self.rate_limits.document(key).set({'count': count, 'timestamp': datetime.now(UTC)})
        return count

    def rpush(self, key: str, value: str) -> None:
        self.request_logs.document(key).set(
            {
                'user': key,
                'content': value,
                'timestamp': datetime.now(UTC),
            },
            merge=True,
        )

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        logs = (
            self.request_logs.where('user', '==', key)
            .order_by('timestamp', direction=firestore.Query.DESCENDING)
            .offset(start)
            .limit(end - start + 1)
            .stream()
        )
        return [doc.to_dict()['content'] for doc in logs]
