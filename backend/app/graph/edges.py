from app.services.web_chain import RelevanceChecker

class ConditionalEdges:
    @staticmethod
    def route_query(state):
        # If any documents exist in the search results, always try document search first
        if state.get("search_results"):
            return "generate"
        # If the search results are completely empty (no documents uploaded), go to web search
        return "web"
