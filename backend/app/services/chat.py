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

        documents_used = []
        for doc in result.get("retrieved_docs", []):
            documents_used.append({
                "file_name": doc.metadata.get("file_name"),
                "chunk_id": doc.metadata.get("chunk_id")
            })

        rewritten = result.get("rewritten_query", query)
        response = {
            "success": True,
            "source": result["source"],
            "answer": result["response"],
            "session_id": session_id,
            "cached": False,
            "relevance_score": result.get("relevance_score", 0.0),
            "retrieved_chunks": len(result.get("retrieved_docs", [])),
            "documents_used": documents_used,
            "rewritten_query": rewritten if rewritten != query else None
        }

        await RedisCacheService.set_cache(cache_key, json.dumps(response))
        return response
