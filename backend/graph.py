from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, HumanMessage
from state.state_manager import TicketState
from agents.classifier import QueryClassifier
from agents.retriever import RAGRetriever
from agents.generator import ResponseGenerator
from agents.validator import QualityValidator


async def parse_input(state: TicketState) -> TicketState:
    """
    Parse the incoming CopilotKit messages and extract the customer query.
    CopilotKit sends messages in the 'messages' field.
    """
    messages = state.get("messages", [])
    customer_query = state.get("customer_query", "")

    # If customer_query is already set (from frontend context), use it
    if customer_query:
        return {}

    # Otherwise, try to extract from the last human message
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) or (hasattr(msg, 'type') and msg.type == 'human'):
            content = msg.content if hasattr(msg, 'content') else str(msg)
            # The content might contain both the instruction and ticket context
            return {"customer_query": content}

    # Fallback - no query found
    return {"customer_query": "No query provided"}


async def format_response(state: TicketState) -> TicketState:
    """
    Format the final response for CopilotKit.
    Returns an AI message with the draft response and metadata.
    """
    draft = state.get("draft_response", "I couldn't generate a response.")
    confidence = state.get("confidence_score", 0.0)
    critique = state.get("critique", "")
    needs_review = state.get("needs_human_review", True)

    # Create a formatted response
    response_text = f"""Here's my draft response for this ticket:

---

{draft}

---

**AI Confidence:** {int(confidence * 100)}%
"""

    if needs_review:
        response_text += "\n**Note:** This response should be reviewed by a human before sending."

    if critique:
        response_text += f"\n**Validation Notes:** {critique}"

    # Return as an AI message
    return {
        "messages": [AIMessage(content=response_text)]
    }


def create_support_graph():
    """Create the CopilotKit-compatible support agent graph."""

    # Initialize Agents
    classifier = QueryClassifier()
    retriever = RAGRetriever()
    generator = ResponseGenerator()
    validator = QualityValidator()

    # Create Graph
    workflow = StateGraph(TicketState)

    # Add Nodes
    workflow.add_node("parse_input", parse_input)
    workflow.add_node("classify", classifier.run)
    workflow.add_node("retrieve", retriever.run)
    workflow.add_node("generate", generator.run)
    workflow.add_node("validate", validator.run)
    workflow.add_node("format_response", format_response)

    # Define Edges - linear pipeline with input parsing and output formatting
    workflow.set_entry_point("parse_input")
    workflow.add_edge("parse_input", "classify")
    workflow.add_edge("classify", "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "validate")
    workflow.add_edge("validate", "format_response")
    workflow.add_edge("format_response", END)

    # Compile with checkpointer for CopilotKit state management
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)
