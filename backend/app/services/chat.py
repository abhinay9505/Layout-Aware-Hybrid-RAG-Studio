import json
from app.graph.builder import GraphBuilder
from app.services.cache import RedisCacheService
from app.services.database_mgr import ChatHistoryManager

class ChatService:
    def __init__(self):
        self.graph = GraphBuilder().build()

    async def chat(self, query, session_id, top_k, user_id=None):
        cache_key = f"cache:{user_id or ''}:{session_id}:{query}"
        cached = await RedisCacheService.get_cache(cache_key)

        if cached:
            response = json.loads(cached)
            response["cached"] = True
            return response

        result = await self.graph.ainvoke({
            "query": query,
            "rewritten_query": "",
            "session_id": session_id,
            "top_k": top_k,
            "user_id": user_id
        })

        await ChatHistoryManager.save_chat(session_id, "user", query, user_id=user_id)
        await ChatHistoryManager.save_chat(session_id, "assistant", result["response"], user_id=user_id)

        sources = []
        for item in result.get("search_results", []):
            doc = item["document"]
            sources.append({
                "document_name": doc.metadata.get("file_name") or "unknown",
                "page": doc.metadata.get("page_num"),
                "chunk": doc.page_content
            })

        response = {
            "answer": result["response"],
            "sources": sources
        }

        await RedisCacheService.set_cache(cache_key, json.dumps(response))
        return response
