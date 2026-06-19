from langgraph.graph import StateGraph, END
from app.graph.state import GraphState
from app.graph.nodes import GraphNodes
from app.graph.edges import ConditionalEdges

class GraphBuilder:
    def __init__(self):
        self.nodes = GraphNodes()
        self.edges = ConditionalEdges()

    def build(self):
        workflow = StateGraph(GraphState)

        # Nodes
        workflow.add_node("rewrite", self.nodes.rewrite_query)
        workflow.add_node("retrieve", self.nodes.retrieve_documents)
        workflow.add_node("generate", self.nodes.generate_response)
        workflow.add_node("web", self.nodes.web_search_fallback)

        # Flow: rewrite → retrieve → (generate | web) → END
        workflow.set_entry_point("rewrite")
        workflow.add_edge("rewrite", "retrieve")

        workflow.add_conditional_edges(
            "retrieve",
            self.edges.route_query,
            {
                "generate": "generate",
                "web": "web"
            }
        )

        workflow.add_edge("generate", END)
        workflow.add_edge("web", END)

        return workflow.compile()
