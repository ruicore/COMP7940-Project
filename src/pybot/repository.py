import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Increment
from google.cloud.firestore_v1.base_query import FieldFilter

from pybot.model import Event, UserProfile


@dataclass
class FirebaseRepository:

    def __post_init__(self):
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
        self.past_events = self.db.collection('past_events')

    def save_user(self, user: UserProfile) -> None:
        self.users.document(user.username).set(user.model_dump())

    def get_user(self, name: str) -> UserProfile | None:
        doc = self.users.document(name).get()
        return UserProfile(**doc.to_dict()) if doc.exists else None

    def save_events(self, username: str, events: list[Event]) -> None:
        batch = self.db.batch()
        for event in events:
            doc_ref = self.past_events.document()
            batch.set(
                doc_ref,
                {
                    'user': username,
                    'content': event.model_dump_json(),
                    'timestamp': datetime.now(UTC),
                },
            )
        batch.commit()

    def get_past_events(self, username: str, limit: int = 60) -> list[Event]:
        events = (
            self.past_events.where(filter=FieldFilter('user', '==', username))
            .order_by('timestamp', direction='DESCENDING')
            .limit(limit)
            .stream()
        )
        return [Event(**json.loads(doc.to_dict()['content'])) for doc in events] if events else []

    def incr(self, key: str) -> int:
        ref = self.rate_limits.document(key)
        ref.set({'timestamp': datetime.now(UTC)}, merge=True)
        ref.update({'count': Increment(1)})

        return ref.get().to_dict().get('count', 0)

    def rpush(self, key: str, value: str) -> None:
        self.request_logs.document(key).set(
            {
                'user': key,
                'content': value,
                'timestamp': datetime.now(UTC),
            },
            merge=True,
        )

    def check_rate_limit(self, username: str, cmd: str) -> bool:
        now = datetime.now(UTC)
        one_minute_ago = now - timedelta(seconds=60)

        recent_logs = (
            self.request_logs.where(filter=FieldFilter('user', '==', username))
            .where(filter=FieldFilter('timestamp', '>=', one_minute_ago))
            .order_by('timestamp', direction='DESCENDING')
            .limit(10)
            .stream()
        )

        if sum(1 for _ in recent_logs) >= 30:
            return False

        return True

    def log_request(self, username: str, command: str, success: bool) -> None:
        self.request_logs.add(
            {
                'timestamp': datetime.now(UTC),
                'username': username,
                'command': command,
                'success': success,
            }
        )
