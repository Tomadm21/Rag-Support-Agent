"""Quick RAG Setup - Simplified version that works reliably."""

import os
import sys
from pathlib import Path
import weaviate
from weaviate.classes.config import Property, DataType, Configure
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

sys.path.append(str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("🚀 Quick RAG Setup")
print("=" * 60)

# Connect to Weaviate
print("\n📡 Connecting to Weaviate...")
client = weaviate.connect_to_local(
    host='localhost',
    port=8080,
    headers={'X-OpenAI-Api-Key': os.getenv('OPENAI_API_KEY')},
    skip_init_checks=True
)

if not client.is_ready():
    print("❌ Weaviate not ready")
    sys.exit(1)

print("✅ Connected to Weaviate")

# Delete existing collection
if client.collections.exists("SupportDocs"):
    client.collections.delete("SupportDocs")
    print("🗑️  Deleted existing collection")

# Create collection
print("\n📝 Creating SupportDocs collection...")
client.collections.create(
    name="SupportDocs",
    properties=[
        Property(name="content", data_type=DataType.TEXT),
        Property(name="document", data_type=DataType.TEXT),
        Property(name="section", data_type=DataType.TEXT),
        Property(name="category", data_type=DataType.TEXT),
        Property(name="chunk_index", data_type=DataType.INT),
    ],
    vectorizer_config=Configure.Vectorizer.text2vec_openai(
        model="text-embedding-3-small"
    )
)
print("✅ Collection created")

# Initialize text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
    separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""]
)

# Process documents
kb_path = Path(__file__).parent.parent / "knowledge_base"
md_files = list(kb_path.glob("*.md"))

print(f"\n📚 Found {len(md_files)} documents")

all_chunks = []

for md_file in md_files:
    print(f"\n📄 Processing: {md_file.name}")

    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Determine category
    category_map = {
        "billing": "Billing & Payments",
        "technical": "Technical Support",
        "features": "Features & Usage"
    }
    category = "General"
    for key, value in category_map.items():
        if key in md_file.stem.lower():
            category = value
            break

    # Extract sections
    sections = []
    current_section = "Introduction"
    current_content = []

    for line in content.split("\n"):
        if line.startswith("## "):
            if current_content:
                sections.append({
                    "section": current_section,
                    "content": "\n".join(current_content).strip()
                })
                current_content = []
            current_section = line.replace("## ", "").strip()
        else:
            current_content.append(line)

    if current_content:
        sections.append({
            "section": current_section,
            "content": "\n".join(current_content).strip()
        })

    # Chunk sections
    doc_chunks = []
    for section_data in sections:
        section_name = section_data["section"]
        section_content = section_data["content"]

        if not section_content.strip():
            continue

        chunks = text_splitter.split_text(section_content)

        for idx, chunk in enumerate(chunks):
            doc_chunks.append({
                "content": chunk,
                "document": md_file.name,
                "section": section_name,
                "category": category,
                "chunk_index": idx
            })

    all_chunks.extend(doc_chunks)
    print(f"   → Created {len(doc_chunks)} chunks")

print(f"\n📊 Total: {len(all_chunks)} chunks")

# Index chunks
print("\n💾 Indexing chunks...")
collection = client.collections.get("SupportDocs")

with collection.batch.dynamic() as batch:
    for i, chunk in enumerate(all_chunks):
        batch.add_object(properties=chunk)
        if (i + 1) % 25 == 0:
            print(f"   ✓ Indexed {i + 1}/{len(all_chunks)}")

print(f"✅ Indexed {len(all_chunks)} chunks")

# Verify
total = collection.aggregate.over_all(total_count=True)
print(f"✅ Verification: {total.total_count} documents in Weaviate")

# Test retrieval
print("\n🧪 Testing Retrieval\n")

test_queries = [
    "How do I request a refund?",
    "API authentication error",
    "How to enable dark mode?"
]

for query in test_queries:
    print(f"\n🔍 Query: '{query}'")

    response = collection.query.hybrid(
        query=query,
        limit=3
    )

    if response.objects:
        print(f"   ✓ Found {len(response.objects)} results:")
        for i, obj in enumerate(response.objects, 1):
            props = obj.properties
            print(f"      {i}. [{props['category']}] {props['document']} - {props['section']}")
            print(f"         {props['content'][:80]}...")
    else:
        print("   ❌ No results")

client.close()

print("\n" + "=" * 60)
print("✅ RAG Setup Complete!")
print("=" * 60)
