import uuid
from datetime import datetime
from app.core.database import documents_collection, chat_history_collection
from app.services.vector_store import LocalVectorStore

class DocumentManager:
    @staticmethod
    async def save_document_metadata(file_name, total_chunks, file_type="document", user_id=None):
        document_id = str(uuid.uuid4())
        await documents_collection.insert_one({
            "document_id": document_id,
            "file_name": file_name,
            "file_type": file_type,
            "total_chunks": total_chunks,
            "uploaded_at": datetime.utcnow().isoformat(),
            "user_id": user_id
        })
        return document_id

    @staticmethod
    async def get_all_documents(user_id=None):
        query = {}
        if user_id:
            query["user_id"] = user_id
        cursor = documents_collection.find(query)
        docs = []
        async for item in cursor:
            item["_id"] = str(item["_id"])
            docs.append(item)
        return docs

    @staticmethod
    async def delete_document(document_id, user_id=None):
        query = {"document_id": document_id}
        if user_id:
            query["user_id"] = user_id
        # Delete document metadata
        res = await documents_collection.delete_one(query)
        if res.deleted_count > 0:
            # Delete corresponding vectors
            await LocalVectorStore.delete_documents(document_id)

class ChatHistoryManager:
    @staticmethod
    async def save_chat(session_id, role, content, user_id=None):
        await chat_history_collection.insert_one({
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id
        })

    @staticmethod
    async def get_history(session_id, user_id=None):
        query = {"session_id": session_id}
        if user_id:
            query["user_id"] = user_id
        cursor = chat_history_collection.find(query)
        history = []
        async for item in cursor:
            item["_id"] = str(item["_id"])
            history.append(item)
        return history

    @staticmethod
    async def clear_history(session_id, user_id=None):
        query = {"session_id": session_id}
        if user_id:
            query["user_id"] = user_id
        await chat_history_collection.delete_many(query)

class ConversationMemoryService:
    @staticmethod
    async def get_recent_history(session_id, limit=6, user_id=None):
        query = {"session_id": session_id}
        if user_id:
            query["user_id"] = user_id
        cursor = chat_history_collection.find(query).sort("_id", -1).limit(limit)
        history = []
        async for item in cursor:
            history.append(f"{item['role']}: {item['content']}")
        history.reverse()
        return "\n".join(history)

