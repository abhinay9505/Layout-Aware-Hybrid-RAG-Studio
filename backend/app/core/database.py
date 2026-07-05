import json
import logging
import asyncio
import sqlite3
import uuid
from pathlib import Path
from app.core.config import MONGO_DB

# Use an absolute path for hybrid_rag.db so both run.py/FastAPI and reindex.py use the same file.
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
import os
DB_FILE = os.getenv("SQLITE_DB_PATH", str(BACKEND_DIR / f"{MONGO_DB}.db"))

# Thread-safe lock for SQLite operations in async context
_db_lock = asyncio.Lock()
_db_initialized = False
_use_mongo = False
_mongo_db = None

def init_sqlite_db():
    db_dir = os.path.dirname(DB_FILE)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()
        for table in ["documents", "chat_history", "users", "figures"]:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    _id TEXT PRIMARY KEY,
                    data TEXT
                )
            """)
        conn.commit()
    finally:
        conn.close()

async def ensure_db_initialized():
    global _db_initialized, _use_mongo, _mongo_db
    if _db_initialized:
        return
    async with _db_lock:
        if _db_initialized:
            return
        # 1. Initialize SQLite
        try:
            init_sqlite_db()
        except Exception as e:
            logging.error(f"Failed to initialize SQLite database: {e}")
        
        # 2. Try to connect to MongoDB
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            from app.core.config import MONGO_URI
            logging.info(f"Attempting to connect to MongoDB at {MONGO_URI}...")
            client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=1000)
            await client.admin.command("ping")
            _mongo_db = client[MONGO_DB]
            _use_mongo = True
            logging.info("Connected to MongoDB successfully. Using MongoDB.")
        except Exception as e:
            logging.warning(f"MongoDB not available: {e}. Falling back to SQLite local database.")
            _use_mongo = False
        _db_initialized = True

async def check_mongo_connection():
    await ensure_db_initialized()
    if _use_mongo:
        logging.info("Running in MongoDB mode.")
    else:
        logging.info(f"Running in SQLite local database mode (file: {DB_FILE}).")

# SQLite CRUD operations
async def sqlite_insert_one(table_name: str, document: dict):
    if "_id" not in document:
        document["_id"] = str(uuid.uuid4())
    doc_id = str(document["_id"])
    
    async with _db_lock:
        conn = sqlite3.connect(DB_FILE)
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"INSERT OR REPLACE INTO {table_name} (_id, data) VALUES (?, ?)",
                (doc_id, json.dumps(document))
            )
            conn.commit()
        finally:
            conn.close()
    return document

async def sqlite_find_one(table_name: str, query: dict):
    async with _db_lock:
        conn = sqlite3.connect(DB_FILE)
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT data FROM {table_name}")
            rows = cursor.fetchall()
        except sqlite3.OperationalError:
            rows = []
        finally:
            conn.close()

    for (data_str,) in rows:
        try:
            doc = json.loads(data_str)
            matched = True
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
                    matched = False
                    break
            if matched:
                return doc
        except Exception:
            continue
    return None

async def sqlite_delete_one(table_name: str, query: dict):
    doc = await sqlite_find_one(table_name, query)
    if not doc:
        class DeleteResult:
            deleted_count = 0
        return DeleteResult()
    
    doc_id = str(doc["_id"])
    async with _db_lock:
        conn = sqlite3.connect(DB_FILE)
        try:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table_name} WHERE _id = ?", (doc_id,))
            conn.commit()
        finally:
            conn.close()
            
    class DeleteResult:
        deleted_count = 1
    return DeleteResult()

async def sqlite_delete_many(table_name: str, query: dict):
    async with _db_lock:
        conn = sqlite3.connect(DB_FILE)
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT _id, data FROM {table_name}")
            rows = cursor.fetchall()
        except sqlite3.OperationalError:
            rows = []
        finally:
            conn.close()
            
    to_delete = []
    for doc_id, data_str in rows:
        try:
            doc = json.loads(data_str)
            matched = True
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
                    matched = False
                    break
            if matched:
                to_delete.append(doc_id)
        except Exception:
            continue

    if to_delete:
        async with _db_lock:
            conn = sqlite3.connect(DB_FILE)
            try:
                cursor = conn.cursor()
                for doc_id in to_delete:
                    cursor.execute(f"DELETE FROM {table_name} WHERE _id = ?", (doc_id,))
                conn.commit()
            finally:
                conn.close()

    class DeleteResult:
        def __init__(self, count):
            self.deleted_count = count
    return DeleteResult(len(to_delete))

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
            except sqlite3.OperationalError:
                rows = []
            finally:
                conn.close()

        docs = []
        for (data_str,) in rows:
            try:
                doc = json.loads(data_str)
                if self._matches(doc, self.query):
                    docs.append(doc)
            except Exception:
                continue

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

class DualModeCursor:
    def __init__(self, table_name: str, query: dict):
        self.table_name = table_name
        self.query = query
        self._sort_field = None
        self._sort_direction = 1
        self._limit = None
        self._mongo_cursor = None
        self._sqlite_cursor = None

    def sort(self, field, direction=1):
        self._sort_field = field
        self._sort_direction = direction
        if self._mongo_cursor:
            self._mongo_cursor.sort(field, direction)
        if self._sqlite_cursor:
            self._sqlite_cursor.sort(field, direction)
        return self

    def limit(self, value):
        self._limit = value
        if self._mongo_cursor:
            self._mongo_cursor.limit(value)
        if self._sqlite_cursor:
            self._sqlite_cursor.limit(value)
        return self

    async def _init_cursor(self):
        await ensure_db_initialized()
        if _use_mongo:
            self._mongo_cursor = _mongo_db[self.table_name].find(self.query)
            if self._sort_field:
                self._mongo_cursor.sort(self._sort_field, self._sort_direction)
            if self._limit is not None:
                self._mongo_cursor.limit(self._limit)
        else:
            self._sqlite_cursor = AsyncCursorMock(self.table_name, self.query)
            if self._sort_field:
                self._sqlite_cursor.sort(self._sort_field, self._sort_direction)
            if self._limit is not None:
                self._sqlite_cursor.limit(self._limit)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._mongo_cursor is None and self._sqlite_cursor is None:
            await self._init_cursor()
        
        if _use_mongo:
            try:
                return await self._mongo_cursor.__anext__()
            except StopAsyncIteration:
                raise StopAsyncIteration
        else:
            if not hasattr(self, '_sqlite_iter'):
                self._sqlite_iter = self._sqlite_cursor.__aiter__()
            try:
                return await self._sqlite_iter.__anext__()
            except StopAsyncIteration:
                raise StopAsyncIteration

class DualModeCollection:
    def __init__(self, name: str):
        self.name = name

    async def insert_one(self, document: dict):
        await ensure_db_initialized()
        if _use_mongo:
            return await _mongo_db[self.name].insert_one(document)
        else:
            return await sqlite_insert_one(self.name, document)

    async def find_one(self, query: dict):
        await ensure_db_initialized()
        if _use_mongo:
            return await _mongo_db[self.name].find_one(query)
        else:
            return await sqlite_find_one(self.name, query)

    async def delete_one(self, query: dict):
        await ensure_db_initialized()
        if _use_mongo:
            return await _mongo_db[self.name].delete_one(query)
        else:
            return await sqlite_delete_one(self.name, query)

    async def delete_many(self, query: dict):
        await ensure_db_initialized()
        if _use_mongo:
            return await _mongo_db[self.name].delete_many(query)
        else:
            return await sqlite_delete_many(self.name, query)

    def find(self, query: dict = None):
        if query is None:
            query = {}
        return DualModeCursor(self.name, query)

class MongoClientMock:
    class AdminMock:
        async def command(self, cmd):
            if cmd == "ping":
                if _use_mongo:
                    return True
                raise ConnectionError("MongoDB is offline (running in SQLite fallback mode)")
            raise ValueError(f"Unknown command: {cmd}")
    admin = AdminMock()

class DualModeMongoClient:
    @property
    def _client(self):
        if _use_mongo:
            from motor.motor_asyncio import AsyncIOMotorClient
            from app.core.config import MONGO_URI
            return AsyncIOMotorClient(MONGO_URI)
        return MongoClientMock()

    def __getattr__(self, name):
        return getattr(self._client, name)
        
    def __getitem__(self, name):
        return self._client[name]

# Redis Client Mock
class RedisClientMock:
    def __init__(self):
        self.data = {}

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, ex=None):
        self.data[key] = value

    async def ping(self):
        return True

class DualModeRedisClient:
    def __init__(self):
        self._mock = RedisClientMock()
        self._redis = None
        self._use_redis = False
        self._initialized = False

    async def _ensure_initialized(self):
        if self._initialized:
            return
        try:
            import redis.asyncio as redis
            from app.core.config import REDIS_HOST, REDIS_PORT, REDIS_DB
            self._redis = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True
            )
            await asyncio.wait_for(self._redis.ping(), timeout=1.0)
            self._use_redis = True
            logging.info("Connected to Redis successfully. Using Redis for caching.")
        except Exception as e:
            logging.warning(f"Redis not available: {e}. Using local in-memory caching.")
            self._use_redis = False
        self._initialized = True

    async def get(self, key):
        await self._ensure_initialized()
        if self._use_redis:
            return await self._redis.get(key)
        return await self._mock.get(key)

    async def set(self, key, value, ex=None):
        await self._ensure_initialized()
        if self._use_redis:
            return await self._redis.set(key, value, ex=ex)
        return await self._mock.set(key, value, ex=ex)

    async def ping(self):
        await self._ensure_initialized()
        if self._use_redis:
            return await self._redis.ping()
        return await self._mock.ping()

# Export clean interfaces
mongo_client = DualModeMongoClient()
documents_collection = DualModeCollection("documents")
chat_history_collection = DualModeCollection("chat_history")
users_collection = DualModeCollection("users")
figures_collection = DualModeCollection("figures")
redis_client = DualModeRedisClient()
