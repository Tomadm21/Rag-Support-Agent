# Deep Dive: Backend Agents

## Overview
The backend logic is split into specialized agents, each responsible for one cognitively distinct task. This "Separation of Concerns" improves reliability and makes testing easier.

## Agents

### 1. Query Classifier (`classifier.py`)
- **Role**: Analyzes the raw user query to determine metadata.
- **Outputs**:
  - `Category`: Used to filter RAG search (e.g., search only 'Billing' docs for billing questions).
  - `Sentiment`: Helps prioritization (e.g., Angry user = High Urgency).
  - `Urgency`: Routing logic.
- **Model**: `gpt-4-turbo` (Temperature 0 for deterministic classification).

### 2. Context Retriever (`retriever.py`)
- **Role**: Interfaces with Weaviate.
- **Logic**: 
  - Takes `customer_query` and `category` from state.
  - Generates an embedding.
  - Queries Weaviate with a filter: `where category == state.category`.
  - Returns top `k` chunks.

### 3. Response Generator (`generator.py`)
- **Role**: Synthesizes the final answer.
- **Inputs**: `customer_query`, `retrieved_context`.
- **System Prompt**: Enforces professional tone, empathy, and strict adherence to context (to reduce hallucinations).

## State Definition

The `TicketState` TypedDict defines the shared memory:

```python
class TicketState(TypedDict):
    ticket_id: str
    customer_query: str
    category: Optional[str]
    retrieved_context: List[str]
    draft_response: Optional[str]
    confidence_score: float
    sentiment: str
    urgency: str
```
