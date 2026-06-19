from typing import TypedDict, List

class GraphState(TypedDict):
    query: str
    rewritten_query: str
    session_id: str
    top_k: int
    search_results: list
    retrieved_docs: list
    response: str
    source: str
    relevance_score: float
    user_id: str

