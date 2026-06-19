import logging
from app.core.dependencies import web_search_tool, llm

class RelevanceChecker:
    THRESHOLD = 0.30

    @staticmethod
    def is_relevant(results):
        if not results:
            return False
        scores = [item["score"] for item in results[:3]]
        avg_score = sum(scores) / len(scores)
        return avg_score >= RelevanceChecker.THRESHOLD

class WebChain:
    async def invoke(self, query, conversation_history=""):
        try:
            web_results = web_search_tool.run(query)
        except Exception as e:
            logging.error(e)
            web_results = "Web search failed."

        history_block = ""
        if conversation_history:
            history_block = f"""
            Conversation History (for context):
            {conversation_history}
            """

        response = await llm.ainvoke(f"""
            You are an AI assistant.
            {history_block}

            Web Results:
            {web_results}

            Question:
            {query}

            Rules:
            - Give a concise, factual answer to the specific question asked.
            - Use the conversation history to understand what the question refers to.
            - Do NOT provide generic information; be specific to the entities mentioned.
        """)
        return response.content
