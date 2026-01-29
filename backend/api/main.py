import os
import sys
import json
import asyncio
from typing import Optional, List, Dict, Any

# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
import weaviate
from weaviate.classes.query import MetadataQuery

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from graph import create_support_graph

app = FastAPI(title="RAG Support Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create the LangGraph pipeline
graph = create_support_graph()


class Message(BaseModel):
    role: str
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    model: Optional[str] = "gpt-4"
    messages: List[Message]
    stream: Optional[bool] = True
    temperature: Optional[float] = 0.5
    tools: Optional[List[Dict]] = None
    tool_choice: Optional[str] = "auto"
    selected_sources: Optional[List[str]] = None  # Optional list of document names to filter RAG retrieval


@app.get("/")
async def root():
    return {"status": "ok", "message": "RAG Support Agent API is running"}


async def generate_stream_response(messages: List[Message], selected_sources: Optional[List[str]] = None):
    """Generate streaming response using the LangGraph pipeline."""

    # Extract the last user message as the customer query
    customer_query = ""
    for msg in reversed(messages):
        if msg.role == "user":
            customer_query = msg.content
            break

    if not customer_query:
        # Yield error message
        yield f"data: {json.dumps({'choices': [{'delta': {'content': 'No user message found.'}, 'index': 0}]})}\n\n"
        yield "data: [DONE]\n\n"
        return

    try:
        # Run the LangGraph pipeline
        initial_state = {
            "ticket_id": "runtime",
            "customer_query": customer_query,
            "selected_sources": selected_sources,
            "messages": [],
            "category": None,
            "retrieved_context": [],
            "draft_response": None,
            "confidence_score": 0.0,
            "critique": None,
            "needs_human_review": True,
        }

        config = {"configurable": {"thread_id": "chat-thread"}}

        # Yield a "thinking" message
        yield f"data: {json.dumps({'choices': [{'delta': {'content': 'Analyzing your request...'}, 'index': 0}]})}\n\n"
        await asyncio.sleep(0.1)

        # Run the graph
        result = await graph.ainvoke(initial_state, config)

        # Get the draft response from the result
        draft_response = result.get("draft_response", "I couldn't generate a response.")
        confidence = result.get("confidence_score", 0.0)
        critique = result.get("critique", "")
        needs_review = result.get("needs_human_review", True)

        # Format the response
        response_text = f"\n\n---\n\n{draft_response}\n\n---\n\n"
        response_text += f"**AI Confidence:** {int(confidence * 100)}%\n"

        if needs_review:
            response_text += "\n**Note:** This response should be reviewed before sending.\n"

        if critique:
            response_text += f"\n**Validation:** {critique}\n"

        # Stream the response character by character for smooth effect
        chunk_size = 10
        for i in range(0, len(response_text), chunk_size):
            chunk = response_text[i:i + chunk_size]
            yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk}, 'index': 0}]})}\n\n"
            await asyncio.sleep(0.02)

        yield "data: [DONE]\n\n"

    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        yield f"data: {json.dumps({'choices': [{'delta': {'content': error_msg}, 'index': 0}]})}\n\n"
        yield "data: [DONE]\n\n"


@app.post("/copilot")
async def chat_completion(request: ChatRequest):
    """OpenAI-compatible chat completion endpoint for CopilotKit."""

    if request.stream:
        return StreamingResponse(
            generate_stream_response(request.messages, request.selected_sources),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    else:
        # Non-streaming response
        messages = request.messages
        customer_query = ""
        for msg in reversed(messages):
            if msg.role == "user":
                customer_query = msg.content
                break

        initial_state = {
            "ticket_id": "runtime",
            "customer_query": customer_query,
            "selected_sources": request.selected_sources,
            "messages": [],
            "category": None,
            "retrieved_context": [],
            "draft_response": None,
            "confidence_score": 0.0,
            "critique": None,
            "needs_human_review": True,
        }

        config = {"configurable": {"thread_id": "chat-thread"}}
        result = await graph.ainvoke(initial_state, config)

        # Return structured response with metadata
        return {
            "id": "chatcmpl-support",
            "object": "chat.completion",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result.get("draft_response", "")
                },
                "finish_reason": "stop"
            }],
            # Custom metadata for the frontend
            "metadata": {
                "confidence": result.get("confidence_score", 0.0),
                "critique": result.get("critique", ""),
                "needs_human_review": result.get("needs_human_review", True),
                "category": result.get("category", ""),
                "sentiment": result.get("sentiment", "Neutral"),
                "urgency": result.get("urgency", "Medium"),
                "rag_sources": result.get("rag_sources", [])
            }
        }


@app.get("/sources")
async def get_available_sources():
    """Get all available RAG sources from knowledge base."""
    try:
        # Connect to Weaviate
        client = weaviate.connect_to_local(
            host='localhost',
            port=8080,
            headers={'X-OpenAI-Api-Key': os.getenv('OPENAI_API_KEY')},
            skip_init_checks=True
        )

        if not client.is_ready():
            return {"sources": [], "error": "Weaviate not connected"}

        # Get all documents
        collection = client.collections.get("SupportDocs")
        response = collection.query.fetch_objects(limit=100)

        # Extract unique sources with metadata
        sources_map = {}
        for obj in response.objects:
            props = obj.properties
            doc_name = props.get("document", "Unknown")

            if doc_name not in sources_map:
                sources_map[doc_name] = {
                    "id": obj.uuid,
                    "document": doc_name,
                    "category": props.get("category", "General"),
                    "sections": set(),
                    "total_chunks": 0
                }

            sources_map[doc_name]["sections"].add(props.get("section", "Unknown"))
            sources_map[doc_name]["total_chunks"] += 1

        # Convert to list
        sources = []
        for doc_name, data in sources_map.items():
            sources.append({
                "id": data["id"],
                "document": doc_name,
                "category": data["category"],
                "sections": list(data["sections"]),
                "total_chunks": data["total_chunks"]
            })

        client.close()
        return {"sources": sources}

    except Exception as e:
        print(f"Error fetching sources: {e}")
        return {"sources": [], "error": str(e)}


@app.post("/suggest-sources")
async def suggest_sources(request: ChatRequest):
    """Suggest best RAG sources for a query without generating draft."""
    try:
        # Extract query
        customer_query = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                customer_query = msg.content
                break

        if not customer_query:
            return {"suggested_sources": []}

        # Connect to Weaviate
        client = weaviate.connect_to_local(
            host='localhost',
            port=8080,
            headers={'X-OpenAI-Api-Key': os.getenv('OPENAI_API_KEY')},
            skip_init_checks=True
        )

        if not client.is_ready():
            return {"suggested_sources": []}

        # Perform vector search
        collection = client.collections.get("SupportDocs")
        response = collection.query.near_text(
            query=customer_query,
            limit=5,
            return_metadata=MetadataQuery(distance=True, certainty=True)
        )

        # Extract sources with relevance
        suggested = []
        seen_docs = set()

        for obj in response.objects:
            props = obj.properties
            meta = obj.metadata
            doc_name = props.get("document", "Unknown")

            # Skip duplicates (same document)
            if doc_name in seen_docs:
                continue
            seen_docs.add(doc_name)

            # Calculate relevance
            relevance = 0.0
            if hasattr(meta, 'certainty') and meta.certainty is not None:
                relevance = meta.certainty
            elif hasattr(meta, 'distance') and meta.distance is not None:
                relevance = max(0.0, 1.0 - meta.distance)
            else:
                relevance = 0.75

            suggested.append({
                "document": doc_name,
                "section": props.get("section", "Unknown"),
                "category": props.get("category", "General"),
                "relevance": round(float(relevance), 3),
                "content_preview": props.get("content", "")[:150] + "..."
            })

        client.close()
        return {"suggested_sources": suggested}

    except Exception as e:
        print(f"Error suggesting sources: {e}")
        return {"suggested_sources": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
