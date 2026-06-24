from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import classify_query_node, retrieve_context_node, generate_response_node

# Define graph workflow
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("classify_query", classify_query_node)
workflow.add_node("retrieve_context", retrieve_context_node)
workflow.add_node("generate_response", generate_response_node)

# Set entrypoint node
workflow.set_entry_point("classify_query")

# Set routing edges
workflow.add_edge("classify_query", "retrieve_context")
workflow.add_edge("retrieve_context", "generate_response")
workflow.add_edge("generate_response", END)

# Compile graph
app_graph = workflow.compile()
