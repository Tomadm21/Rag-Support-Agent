#!/usr/bin/env python3
"""
Script to initialize Weaviate schema and populate with sample support documentation.
Run this after starting the Weaviate Docker container.

Usage:
    cd backend
    source venv/bin/activate
    python scripts/setup_weaviate.py
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import weaviate
from weaviate.classes.config import Configure, Property, DataType
from dotenv import load_dotenv

load_dotenv()

# Sample support documentation
SAMPLE_DOCS = [
    # Billing
    {"category": "Billing", "content": "To request a refund, navigate to Settings > Billing > Transaction History. Find the charge and click 'Request Refund'. Refunds are processed within 3-5 business days."},
    {"category": "Billing", "content": "Duplicate charges can occur due to network timeouts. If you see a duplicate charge, it will be automatically reversed within 24 hours. For immediate assistance, contact billing@example.com."},
    {"category": "Billing", "content": "Premium plans are billed on the 1st of each month. When upgrading mid-cycle, you'll be charged a prorated amount for the remaining days."},
    {"category": "Billing", "content": "To update payment method: Go to Settings > Billing > Payment Methods > Add New Card. You can set a new default payment method at any time."},

    # Technical
    {"category": "Technical", "content": "API 500 errors typically indicate server-side issues. First, check status.example.com for ongoing incidents. If no incidents, verify your request format and API key."},
    {"category": "Technical", "content": "The /v1/users endpoint has a rate limit of 100 requests per minute. Exceeding this returns a 429 error. Implement exponential backoff for retries."},
    {"category": "Technical", "content": "For authentication errors, ensure your API key is valid and has the required scopes. Keys can be regenerated in Dashboard > Developer > API Keys."},
    {"category": "Technical", "content": "WebSocket connections timeout after 30 seconds of inactivity. Implement ping/pong heartbeats to maintain persistent connections."},

    # Feature
    {"category": "Feature", "content": "To enable dark mode, go to Settings > Appearance > Theme and select 'Dark'. The change applies immediately across all devices."},
    {"category": "Feature", "content": "Keyboard shortcuts can be viewed by pressing Ctrl+K (Windows/Linux) or Cmd+K (Mac). You can customize shortcuts in Settings > Accessibility."},
    {"category": "Feature", "content": "Export your data anytime from Settings > Data Management > Export. Supported formats include JSON, CSV, and XML."},
    {"category": "Feature", "content": "Two-factor authentication can be enabled in Settings > Security > 2FA. We support authenticator apps and SMS verification."},

    # Bug
    {"category": "Bug", "content": "If the application crashes, please collect: 1) Browser and OS version, 2) Steps to reproduce, 3) Console errors (press F12). Submit via Help > Report Issue."},
    {"category": "Bug", "content": "Known issue: Dashboard may show stale data during high traffic periods. Refresh the page or enable auto-refresh in Settings to get the latest data."},
    {"category": "Bug", "content": "Image upload failures are often caused by files exceeding the 5MB limit. Compress images or use our batch upload feature for large files."},
    {"category": "Bug", "content": "If password reset emails aren't arriving, check your spam folder. Add noreply@example.com to your contacts. Reset links expire after 24 hours."},
]


def setup_weaviate():
    """Initialize Weaviate with schema and sample data."""

    weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not openai_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set.")
        print("Please set it with: export OPENAI_API_KEY='your-key'")
        return False

    print(f"Connecting to Weaviate at {weaviate_url}...")

    # Parse URL for host and port
    url_parts = weaviate_url.replace("http://", "").replace("https://", "")
    if ":" in url_parts:
        host, port_str = url_parts.split(":")
        port = int(port_str)
    else:
        host = url_parts
        port = 8080

    try:
        client = weaviate.connect_to_local(
            host=host,
            port=port,
            headers={"X-OpenAI-Api-Key": openai_key}
        )
    except Exception as e:
        print(f"ERROR: Failed to connect to Weaviate: {e}")
        print("\nMake sure Weaviate is running:")
        print("  cd support-system")
        print("  docker-compose up -d")
        return False

    try:
        if not client.is_ready():
            print("ERROR: Weaviate is not ready. Make sure the Docker container is running.")
            return False

        print("Connected successfully!")

        # Check if collection exists and delete it for fresh setup
        if client.collections.exists("SupportDocs"):
            print("Deleting existing SupportDocs collection...")
            client.collections.delete("SupportDocs")

        # Create collection with OpenAI vectorizer
        print("Creating SupportDocs collection...")
        support_docs = client.collections.create(
            name="SupportDocs",
            vectorizer_config=Configure.Vectorizer.text2vec_openai(
                model="text-embedding-3-small"
            ),
            properties=[
                Property(name="category", data_type=DataType.TEXT),
                Property(name="content", data_type=DataType.TEXT),
            ]
        )

        # Insert sample documents
        print(f"Inserting {len(SAMPLE_DOCS)} sample documents...")

        with support_docs.batch.dynamic() as batch:
            for doc in SAMPLE_DOCS:
                batch.add_object(properties=doc)

        # Verify insertion
        count = support_docs.aggregate.over_all(total_count=True).total_count
        print(f"Successfully inserted {count} documents!")

        # Test a sample query
        print("\nTesting vector search...")
        results = support_docs.query.near_text(
            query="How do I get a refund?",
            limit=2
        )

        print(f"Test query returned {len(results.objects)} results:")
        for i, obj in enumerate(results.objects):
            print(f"  {i+1}. [{obj.properties['category']}] {obj.properties['content'][:80]}...")

        print("\nWeaviate setup complete!")
        return True

    except Exception as e:
        print(f"ERROR: Setup failed: {e}")
        return False

    finally:
        client.close()


if __name__ == "__main__":
    success = setup_weaviate()
    sys.exit(0 if success else 1)
