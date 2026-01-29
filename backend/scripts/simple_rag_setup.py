"""Simple RAG Setup - Guaranteed to work."""

import os, sys
from pathlib import Path
import weaviate
from weaviate.classes.config import Property, DataType, Configure

sys.path.append(str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

print("🚀 Simple RAG Setup\n")

# Connect
print("📡 Connecting...")
client = weaviate.connect_to_local(
    host='localhost', port=8080,
    headers={'X-OpenAI-Api-Key': os.getenv('OPENAI_API_KEY')},
    skip_init_checks=True
)
print("✅ Connected\n")

# Create schema
if client.collections.exists("SupportDocs"):
    client.collections.delete("SupportDocs")

print("📝 Creating collection...")
client.collections.create(
    name="SupportDocs",
    properties=[
        Property(name="content", data_type=DataType.TEXT),
        Property(name="document", data_type=DataType.TEXT),
        Property(name="section", data_type=DataType.TEXT),
        Property(name="category", data_type=DataType.TEXT),
    ],
    vectorizer_config=Configure.Vectorizer.text2vec_openai()
)
print("✅ Collection created\n")

# Manual chunks (representative samples from each document)
chunks = [
    # Billing Guide
    {
        "content": "To request a refund, navigate to Settings > Billing > Transaction History and click 'Request Refund' next to the charge. Refunds can be requested within 30 days of purchase for first-time subscriptions. Refunds are processed within 5-7 business days.",
        "document": "billing_guide.md",
        "section": "Refund Policy",
        "category": "Billing & Payments"
    },
    {
        "content": "Duplicate charges are typically processed within 3-5 business days. If you see duplicate charges, check your transaction history first. Sometimes charges appear as both 'pending' and 'complete'. If truly duplicated, contact billing@support.com with transaction ID, date, and amount.",
        "document": "billing_guide.md",
        "section": "Duplicate Charges",
        "category": "Billing & Payments"
    },
    {
        "content": "We offer three subscription plans: Starter ($29/month for up to 100 tickets), Professional ($99/month for up to 1,000 tickets with API access), and Enterprise (custom pricing with unlimited tickets and 24/7 support).",
        "document": "billing_guide.md",
        "section": "Subscription Plans",
        "category": "Billing & Payments"
    },
    {
        "content": "Payment failures can occur due to expired credit cards, insufficient funds, card declined by bank, or billing address mismatch. Update your payment method in Settings > Billing and retry the failed payment. You have a 7-day grace period before account suspension.",
        "document": "billing_guide.md",
        "section": "Payment Failures",
        "category": "Billing & Payments"
    },

    # Technical Docs
    {
        "content": "All API requests require authentication using an API key in the Authorization header. Get your API key from Settings > API > Generate New API Key. Example: curl -H 'Authorization: Bearer YOUR_API_KEY' https://api.example.com/v1/tickets",
        "document": "technical_docs.md",
        "section": "API Authentication",
        "category": "Technical Support"
    },
    {
        "content": "Common API error 401 Unauthorized means invalid or missing API key. Check your API key and ensure it's in the Authorization header. Error 429 Too Many Requests means you exceeded the rate limit - implement exponential backoff and respect X-RateLimit headers.",
        "document": "technical_docs.md",
        "section": "Common API Errors",
        "category": "Technical Support"
    },
    {
        "content": "Rate limits: Starter plan has 100 requests/minute, Professional has 1,000 requests/minute, Enterprise has 10,000 requests/minute. Check rate limit headers: X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset.",
        "document": "technical_docs.md",
        "section": "Rate Limits",
        "category": "Technical Support"
    },
    {
        "content": "For 500 Internal Server Error, check status.example.com for incidents and retry with exponential backoff. For 503 Service Unavailable, retry after 60 seconds and check the status page for maintenance notices.",
        "document": "technical_docs.md",
        "section": "API Errors",
        "category": "Technical Support"
    },
    {
        "content": "Webhook setup: Go to Settings > Webhooks, click Add Webhook, enter HTTPS URL, select events (ticket.created, ticket.updated, ticket.resolved, response.sent), and set webhook secret for signature verification.",
        "document": "technical_docs.md",
        "section": "Webhook Integration",
        "category": "Technical Support"
    },

    # Features Guide
    {
        "content": "To enable dark mode: Navigate to Settings > Appearance > Theme and select 'Dark'. The dark mode provides a clean, aesthetic interface that's easier on the eyes during extended use.",
        "document": "features_guide.md",
        "section": "Dashboard Features",
        "category": "Features & Usage"
    },
    {
        "content": "AI automatically categorizes tickets into: Billing & Payments, Technical Issues, Feature Requests, Bug Reports, Account Management, and General Inquiry. The AI analyzes ticket content, identifies key topics and intent, assigns appropriate category, and routes to specialized teams.",
        "document": "features_guide.md",
        "section": "AI-Powered Features",
        "category": "Features & Usage"
    },
    {
        "content": "Sentiment Analysis detects customer sentiment with emojis: Positive (😊 customer satisfied), Neutral (😐 standard inquiry), Negative (😞 customer frustrated). Use cases include prioritizing negative sentiment tickets, alerting supervisors, and tracking sentiment trends.",
        "document": "features_guide.md",
        "section": "Sentiment Analysis",
        "category": "Features & Usage"
    },
    {
        "content": "Set up automation rules with triggers and actions. Example: Auto-escalate high priority tickets with no response in 2 hours to supervisor. Auto-close resolved tickets with no customer reply in 7 days. Auto-tag tickets by keywords.",
        "document": "features_guide.md",
        "section": "Automation Rules",
        "category": "Features & Usage"
    },
    {
        "content": "Available integrations include CRM (Salesforce, HubSpot), Chat (Slack, Teams), Project Management (Jira, Asana), E-commerce (Shopify, WooCommerce), and Analytics (Google Analytics, Mixpanel). Set up in Settings > Integrations.",
        "document": "features_guide.md",
        "section": "Integrations",
        "category": "Features & Usage"
    }
]

print(f"💾 Indexing {len(chunks)} chunks...\n")

collection = client.collections.get("SupportDocs")

for i, chunk in enumerate(chunks, 1):
    collection.data.insert(chunk)
    print(f"   ✓ {i}/{len(chunks)}: {chunk['document']} - {chunk['section']}")

print(f"\n✅ Indexed {len(chunks)} chunks")

# Test
print("\n🧪 Testing Retrieval\n")

tests = [
    "How do I request a refund?",
    "API 401 error authentication",
    "enable dark mode"
]

for query in tests:
    print(f"🔍 '{query}'")
    response = collection.query.near_text(query=query, limit=2)
    if response.objects:
        for obj in response.objects:
            p = obj.properties
            print(f"   → [{p['category']}] {p['section']}")
    print()

client.close()
print("✅ Setup Complete!")
