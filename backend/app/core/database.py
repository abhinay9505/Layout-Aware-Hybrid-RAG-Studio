import sqlite3
import json
import logging
import asyncio
import os
import redis.asyncio as redis
from app.core.config import MONGO_DB, REDIS_HOST, REDIS_PORT, REDIS_DB

DB_FILE = f"{MONGO_DB}.db"

# Thread-safe lock for SQLite operations in async context
_db_lock = asyncio.Lock()

def init_db():
    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()
        for table in ["documents", "chat_history", "users"]:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    _id TEXT PRIMARY KEY,
                    data TEXT
                )
            """)
        conn.commit()
    finally:
        conn.close()

# Initialize DB on import
init_db()

class AsyncCursorMock:
    def __init__(self, table_name: str, query: dict):
        self.table_name = table_name
        self.query = query
        self._sort_field = None
        self._sort_direction = 1
        self._limit = None

    def sort(self, field, direction=1):
        self._sort_field = field
        self._sort_direction = direction
        return self

    def limit(self, value):
        self._limit = value
        return self

    def __aiter__(self):
        return self._fetch_all()

    async def _fetch_all(self):
        async with _db_lock:
            conn = sqlite3.connect(DB_FILE)
            try:
                cursor = conn.cursor()
                cursor.execute(f"SELECT data FROM {self.table_name}")
                rows = cursor.fetchall()
            finally:
                conn.close()

        docs = []
        for (data_str,) in rows:
            doc = json.loads(data_str)
            if self._matches(doc, self.query):
                docs.append(doc)
        
        # Handle sorting
        if self._sort_field:
            reverse = self._sort_direction == -1
            def sort_key(d):
                parts = self._sort_field.split(".")
                val = d
                for part in parts:
                    if isinstance(val, dict) and part in val:
                        val = val[part]
                    else:
                        val = ""
                        break
                return val
            docs.sort(key=sort_key, reverse=reverse)

        # Handle limit
        if self._limit is not None:
            docs = docs[:self._limit]

        for doc in docs:
            yield doc

    def _matches(self, doc: dict, query: dict) -> bool:
        for k, v in query.items():
            actual_val = doc
            parts = k.split(".")
            for part in parts:
                if isinstance(actual_val, dict) and part in actual_val:
                    actual_val = actual_val[part]
                else:
                    actual_val = None
                    break
            if actual_val != v:
                return False
        return True

class SQLiteCollectionMock:
    def __init__(self, name: str):
        self.name = name

    async def insert_one(self, document: dict):
        if "_id" not in document:
            import uuid
            document["_id"] = str(uuid.uuid4())
        
        doc_id = str(document["_id"])
        
        async with _db_lock:
            conn = sqlite3.connect(DB_FILE)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    f"INSERT OR REPLACE INTO {self.name} (_id, data) VALUES (?, ?)",
                    (doc_id, json.dumps(document))
                )
                conn.commit()
            finally:
                conn.close()
        return document

    async def find_one(self, query: dict):
        async with _db_lock:
            conn = sqlite3.connect(DB_FILE)
            try:
                cursor = conn.cursor()
                cursor.execute(f"SELECT data FROM {self.name}")
                rows = cursor.fetchall()
            finally:
                conn.close()
        
        for (data_str,) in rows:
            doc = json.loads(data_str)
            if self._matches(doc, query):
                return doc
        return None

    async def delete_one(self, query: dict):
        doc = await self.find_one(query)
        if not doc:
            class DeleteResult:
                deleted_count = 0
            return DeleteResult()
        
        async with _db_lock:
            conn = sqlite3.connect(DB_FILE)
            try:
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM {self.name} WHERE _id = ?", (str(doc["_id"]),))
                conn.commit()
            finally:
                conn.close()
        
        class DeleteResult:
            deleted_count = 1
        return DeleteResult()

    async def delete_many(self, query: dict):
        async with _db_lock:
            conn = sqlite3.connect(DB_FILE)
            try:
                cursor = conn.cursor()
                cursor.execute(f"SELECT _id, data FROM {self.name}")
                rows = cursor.fetchall()
                deleted_count = 0
                for doc_id, data_str in rows:
                    doc = json.loads(data_str)
                    if self._matches(doc, query):
                        cursor.execute(f"DELETE FROM {self.name} WHERE _id = ?", (doc_id,))
                        deleted_count += 1
                conn.commit()
            finally:
                conn.close()
        
        class DeleteResult:
            deleted_count = deleted_count
        return DeleteResult()

    def find(self, query: dict = None):
        if query is None:
            query = {}
        return AsyncCursorMock(self.name, query)

    def _matches(self, doc: dict, query: dict) -> bool:
        for k, v in query.items():
            actual_val = doc
            parts = k.split(".")
            for part in parts:
                if isinstance(actual_val, dict) and part in actual_val:
                    actual_val = actual_val[part]
                else:
                    actual_val = None
                    break
            if actual_val != v:
                return False
        return True

class MongoClientMock:
    class AdminMock:
        async def command(self, cmd):
            if cmd == "ping":
                return True
            raise ValueError(f"Unknown command: {cmd}")
    admin = AdminMock()

    def __getitem__(self, key):
        class DBItemMock:
            def __getitem__(self, coll_key):
                if coll_key == "users":
                    return users_collection
                elif coll_key == "documents":
                    return documents_collection
                elif coll_key == "chat_history":
                    return chat_history_collection
                else:
                    return SQLiteCollectionMock(coll_key)
            
            def __getattr__(self, coll_key):
                return self[coll_key]
        return DBItemMock()

# Export mocked interfaces mimicking PyMongo
mongo_client = MongoClientMock()
documents_collection = SQLiteCollectionMock("documents")
chat_history_collection = SQLiteCollectionMock("chat_history")
users_collection = SQLiteCollectionMock("users")

# Setup Redis
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)
