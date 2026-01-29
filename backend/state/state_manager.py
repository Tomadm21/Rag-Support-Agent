from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import BaseMessage
import operator

class TicketState(TypedDict):
    """
    Shared state for the Customer Support RAG System.
    """
    # Input
    ticket_id: str
    customer_query: str
    selected_sources: Optional[List[str]]  # Optional list of document names to filter retrieval

    # Processing
    category: Optional[str]  # 'Billing', 'Technical', 'Feature', 'Bug'
    sentiment: Optional[str]  # 'Positive', 'Neutral', 'Negative'
    urgency: Optional[str]  # 'Low', 'Medium', 'High', 'Critical'
    retrieved_context: List[str]  # List of relevant doc strings
    rag_sources: Optional[List[dict]]  # RAG source metadata

    # Output
    draft_response: Optional[str]
    confidence_score: float
    critique: Optional[str]
    needs_human_review: bool

    # Conversation History (for CopilotKit)
    messages: Annotated[List[BaseMessage], operator.add]
