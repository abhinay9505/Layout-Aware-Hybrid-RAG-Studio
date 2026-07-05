from langgraph.graph import StateGraph, END
from app.graph.state import GraphState
from app.graph.nodes import GraphNodes

class GraphBuilder:
    def __init__(self):
        self.nodes = GraphNodes()

    def build(self):
        workflow = StateGraph(GraphState)

        # Nodes
        workflow.add_node("rewrite", self.nodes.rewrite_query)
        workflow.add_node("retrieve", self.nodes.retrieve_documents)
        workflow.add_node("generate", self.nodes.generate_response)

        # Flow: rewrite → retrieve → generate → END
        workflow.set_entry_point("rewrite")
        workflow.add_edge("rewrite", "retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)

        return workflow.compile()
