import os
import tempfile

import firebase_admin
import redis
from firebase_admin import credentials, firestore
from setting import RedisConfig, config

repo = redis.Redis(**dict(config.redis))


class RedisRepository:
    def __init__(self, redis_config: RedisConfig):
        self.client = redis.Redis(**redis_config.model_dump())

    def incr(self, key: str) -> int:
        return int(self.client.incr(key))

    def get(self, key: str) -> str | None:
        value = self.client.get(key)
        return value if value else None

    def rpush(self, key: str, value: str) -> None:
        self.client.rpush(key, value)

    def lrange(self, key: str, start: int, end: int) -> list[bytes]:
        return self.client.lrange(key, start, end)


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
        self.collection = self.db.collection('users')
        self.counters = self.db.collection('counters')
        self.lists = self.db.collection('lists')

    def save_user(self, user: dict) -> None:
        name = user['name']
        self.collection.document(name).set(user)

    def get_user(self, name: str) -> dict | None:
        doc = self.collection.document(name).get()
        return doc.to_dict() if doc.exists else None

    def incr(self, key: str) -> int:
        counter_ref = self.counters.document(key)

        @firestore.transactional
        def update_counter(transaction):
            snapshot = counter_ref.get(transaction=transaction)
            current = snapshot.get('value') if snapshot.exists else 0
            new_value = current + 1
            transaction.set(counter_ref, {'value': new_value}, merge=True)
            return new_value

        transaction = self.db.transaction()
        return update_counter(transaction)

    def rpush(self, key: str, value: str) -> None:
        list_ref = self.lists.document(key).collection('items')
        list_ref.add({'value': value, 'timestamp': firestore.SERVER_TIMESTAMP})

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        list_ref = self.lists.document(key).collection('items')
        query = list_ref.order_by('timestamp').limit(end + 1)
        docs = query.get()

        values = [doc.to_dict()['value'] for doc in docs]
        return values[start : end + 1] if values else []
