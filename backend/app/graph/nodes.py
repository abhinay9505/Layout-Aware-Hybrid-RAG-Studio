import logging
from app.services.vector_store import LocalVectorStore
from app.services.web_chain import WebChain
from app.services.database_mgr import ConversationMemoryService
from app.core.dependencies import llm

class GraphNodes:
    def __init__(self):
        self.web_chain = WebChain()

    # ── NEW: Rewrite query using chat history context ──────────────
    async def rewrite_query(self, state):
        """
        Use recent conversation history to rewrite ambiguous follow-up
        questions into fully self-contained queries.
        e.g. "tell me about his wife" → "tell me about Allu Arjun's wife"
        """
        history = await ConversationMemoryService.get_recent_history(
            state["session_id"], limit=6, user_id=state.get("user_id")
        )

        # If there's no history, the query is already standalone
        if not history.strip():
            state["rewritten_query"] = state["query"]
            return state

        rewrite_response = await llm.ainvoke(f"""
You are a query rewriter. Given the conversation history and the latest user question,
rewrite the question so it is FULLY SELF-CONTAINED (no pronouns like "he", "she", "his",
"her", "it", "they", "this", "that" referring to earlier messages).

Conversation History:
{history}

Latest Question:
{state["query"]}

Rules:
- Replace ALL pronouns and references with the actual entity names from the conversation history.
- Keep the rewritten question concise.
- If the question is already self-contained, return it unchanged.
- Return ONLY the rewritten question, nothing else.

Rewritten Question:""")

        rewritten = rewrite_response.content.strip().strip('"').strip("'")
        logging.info(f"Query rewrite: '{state['query']}' → '{rewritten}'")
        state["rewritten_query"] = rewritten
        return state

    # ── Retrieve documents using the rewritten query ───────────────
    async def retrieve_documents(self, state):
        search_query = state.get("rewritten_query") or state["query"]
        results = await LocalVectorStore.similarity_search(
            search_query,
            state["top_k"],
            user_id=state.get("user_id")
        )
        state["search_results"] = results
        state["retrieved_docs"] = [item["document"] for item in results]
        return state

    # ── Generate response from retrieved docs ──────────────────────
    async def generate_response(self, state):
        history = await ConversationMemoryService.get_recent_history(state["session_id"], user_id=state.get("user_id"))
        context = "\n\n".join([doc.page_content for doc in state["retrieved_docs"]])
        search_query = state.get("rewritten_query") or state["query"]

        response = await llm.ainvoke(f"""
            You are a professional AI assistant.

            Conversation History:
            {history}

            Context:
            {context}

            Original Question:
            {state['query']}

            Interpreted Question:
            {search_query}

            Rules:
            - Use ONLY provided context
            - Avoid hallucinations
            - Answer the interpreted question using the context
            - If answer unavailable say:
              Information not found
        """)

        response_text = response.content.strip().lower()
        not_found_indicators = [
            "information not found",
            "not found",
            "not mentioned",
            "no mention",
            "cannot find",
            "not available",
            "do not have",
            "does not contain"
        ]

        if any(indicator in response_text for indicator in not_found_indicators):
            # Fall back to web search directly within this node
            logging.info("Information not found in documents. Falling back to web search...")
            web_response = await self.web_chain.invoke(search_query, history)
            state["response"] = web_response
            state["source"] = "web"
            state["relevance_score"] = 0.0
        else:
            state["response"] = response.content
            state["source"] = "document"

        scores = [item["score"] for item in state["search_results"][:3]]
        state["relevance_score"] = sum(scores) / len(scores) if scores else 0.0

        return state

    # ── Web search fallback using the rewritten query ──────────────
    async def web_search_fallback(self, state):
        search_query = state.get("rewritten_query") or state["query"]
        history = await ConversationMemoryService.get_recent_history(state["session_id"], user_id=state.get("user_id"))
        response = await self.web_chain.invoke(search_query, history)
        state["response"] = response
        state["source"] = "web"
        state["relevance_score"] = 0.0
        return state
