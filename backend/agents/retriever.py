from typing import List
import os
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery, Filter
from weaviate.exceptions import WeaviateConnectionError
from langchain_openai import OpenAIEmbeddings
from state.state_manager import TicketState


class RAGRetriever:
    """RAG Retriever using Weaviate v4 API for vector search."""

    def __init__(self):
        self.weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
        self.weaviate_key = os.getenv("WEAVIATE_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        self.connected = False
        self.embeddings = None

        self._connect()

    def _connect(self):
        """Attempt to connect to Weaviate with v4 API."""
        # Parse URL for host and port
        url_parts = self.weaviate_url.replace("http://", "").replace("https://", "")
        if ":" in url_parts:
            host, port_str = url_parts.split(":")
            port = int(port_str)
        else:
            host = url_parts
            port = 8080

        try:
            # For local Docker deployment
            if "localhost" in self.weaviate_url or "127.0.0.1" in self.weaviate_url:
                self.client = weaviate.connect_to_local(
                    host=host,
                    port=port,
                    headers={"X-OpenAI-Api-Key": self.openai_key} if self.openai_key else {}
                )
            else:
                # For Weaviate Cloud
                self.client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self.weaviate_url,
                    auth_credentials=Auth.api_key(self.weaviate_key) if self.weaviate_key else None,
                    headers={"X-OpenAI-Api-Key": self.openai_key} if self.openai_key else {}
                )

            self.embeddings = OpenAIEmbeddings()
            self.connected = self.client.is_ready()
            print(f"Weaviate connection: {'SUCCESS' if self.connected else 'FAILED'}")

        except WeaviateConnectionError as e:
            print(f"Warning: Weaviate connection failed: {e}")
            self.connected = False
        except Exception as e:
            print(f"Warning: Unexpected error connecting to Weaviate: {e}")
            self.connected = False

    def _get_mock_data(self, category: str, query: str) -> List[str]:
        """Return realistic mock data for testing without Weaviate."""
        mock_kb = {
            "Billing": [
                "To request a refund, navigate to Settings > Billing > Transaction History and click 'Request Refund' next to the charge.",
                "Duplicate charges are typically processed within 3-5 business days. Contact billing@example.com for urgent issues.",
            ],
            "Technical": [
                "For API 500 errors, first check our status page at status.example.com for any ongoing incidents.",
                "Common causes of /v1/users endpoint failures: invalid API key, rate limiting (100 req/min), or malformed request body.",
            ],
            "Feature": [
                "To enable dark mode: Settings > Appearance > Theme > Select 'Dark'.",
                "Feature requests can be submitted at feedback.example.com. Popular requests are reviewed monthly.",
            ],
            "Bug": [
                "If you encounter a crash, please provide: 1) Browser/OS version, 2) Steps to reproduce, 3) Console errors (F12).",
                "Known issue: Data sync delays may occur during peak hours (9-11 AM EST). We're working on scaling improvements.",
            ]
        }
        return mock_kb.get(category, mock_kb["Technical"])

    async def run(self, state: TicketState) -> TicketState:
        """Retrieve relevant context for the query with source metadata."""
        query = state.get("customer_query", "")
        category = state.get("category", "Technical")
        selected_sources = state.get("selected_sources")

        if not self.connected or self.client is None:
            # Fallback to mock data
            print("Using mock data (Weaviate not connected)")
            mock_docs = self._get_mock_data(category, query)
            return {
                "retrieved_context": mock_docs,
                "rag_sources": [
                    {
                        "document": "Mock Knowledge Base",
                        "section": "General",
                        "category": category,
                        "relevance": 0.85
                    }
                ]
            }

        try:
            # Perform actual vector search with Weaviate v4 API
            support_docs = self.client.collections.get("SupportDocs")

            # Enhanced query with category
            search_query = f"{category}: {query}"

            # Build query with optional filter for selected sources
            query_params = {
                "query": search_query,
                "limit": 5 if selected_sources else 3,  # Get more results if filtering
                "return_metadata": MetadataQuery(distance=True, certainty=True)
            }

            # Add filter if specific sources are selected
            if selected_sources and len(selected_sources) > 0:
                print(f"🎯 Filtering by selected sources: {selected_sources}")
                # Create filter for documents matching any of the selected sources
                if len(selected_sources) == 1:
                    query_params["filters"] = Filter.by_property("document").equal(selected_sources[0])
                else:
                    # Use OR condition for multiple sources
                    filters = [Filter.by_property("document").equal(source) for source in selected_sources]
                    query_params["filters"] = Filter.any_of(filters)

            response = support_docs.query.near_text(**query_params)

            if not response.objects:
                # No results found, use mock data
                print("No documents found in Weaviate, using mock data")
                mock_docs = self._get_mock_data(category, query)
                return {
                    "retrieved_context": mock_docs,
                    "rag_sources": [
                        {
                            "document": "Mock Knowledge Base",
                            "section": "General",
                            "category": category,
                            "relevance": 0.85
                        }
                    ]
                }

            # Extract content and metadata
            docs = []
            sources = []

            for obj in response.objects:
                props = obj.properties
                meta = obj.metadata

                docs.append(props.get("content", ""))

                # Calculate relevance score (1 - distance, or use certainty if available)
                relevance = 0.0
                if hasattr(meta, 'certainty') and meta.certainty is not None:
                    relevance = meta.certainty
                elif hasattr(meta, 'distance') and meta.distance is not None:
                    # Convert distance to similarity (lower distance = higher similarity)
                    relevance = max(0.0, 1.0 - meta.distance)
                else:
                    relevance = 0.75  # Default fallback

                sources.append({
                    "document": props.get("document", "Unknown"),
                    "section": props.get("section", "Unknown"),
                    "category": props.get("category", category),
                    "relevance": round(float(relevance), 3),
                    "content_preview": props.get("content", "")[:150] + "..."
                })

            print(f"✅ Retrieved {len(docs)} documents from Weaviate with sources")
            return {
                "retrieved_context": docs,
                "rag_sources": sources
            }

        except Exception as e:
            print(f"Weaviate query error: {e}")
            mock_docs = self._get_mock_data(category, query)
            return {
                "retrieved_context": mock_docs,
                "rag_sources": [
                    {
                        "document": "Mock Knowledge Base (Error Fallback)",
                        "section": "General",
                        "category": category,
                        "relevance": 0.80
                    }
                ]
            }

    def __del__(self):
        """Clean up Weaviate connection."""
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
