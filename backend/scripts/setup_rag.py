"""
State-of-the-Art RAG Setup Script
- Smart document chunking with overlap
- Metadata tracking (document, section, page)
- Weaviate v4 with Hybrid Search (Vector + BM25)
- OpenAI embeddings (text-embedding-3-small)
"""

import os
import sys
from pathlib import Path
from typing import List, Dict
import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.init import Auth
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
import re

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


class RAGIndexer:
    """State-of-the-art RAG indexer with smart chunking and metadata."""

    def __init__(self):
        self.weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
        self.weaviate_key = os.getenv("WEAVIATE_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

        # Smart chunking configuration
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,  # Optimal for retrieval
            chunk_overlap=150,  # Preserve context across chunks
            length_function=len,
            separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""]
        )

    def connect(self):
        """Connect to Weaviate."""
        url_parts = self.weaviate_url.replace("http://", "").replace("https://", "")
        if ":" in url_parts:
            host, port_str = url_parts.split(":")
            port = int(port_str)
        else:
            host = url_parts
            port = 8080

        try:
            if "localhost" in self.weaviate_url or "127.0.0.1" in self.weaviate_url:
                self.client = weaviate.connect_to_local(
                    host=host,
                    port=port,
                    headers={"X-OpenAI-Api-Key": self.openai_key} if self.openai_key else {},
                    skip_init_checks=True  # Skip gRPC health check for Docker compatibility
                )
            else:
                self.client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self.weaviate_url,
                    auth_credentials=Auth.api_key(self.weaviate_key) if self.weaviate_key else None,
                    headers={"X-OpenAI-Api-Key": self.openai_key} if self.openai_key else {},
                    skip_init_checks=True
                )

            if self.client.is_ready():
                print("✅ Connected to Weaviate successfully")
                return True
            else:
                print("❌ Weaviate connection failed")
                return False

        except Exception as e:
            print(f"❌ Error connecting to Weaviate: {e}")
            return False

    def create_schema(self):
        """Create Weaviate schema with Hybrid Search capabilities."""
        try:
            # Delete existing collection if it exists
            if self.client.collections.exists("SupportDocs"):
                self.client.collections.delete("SupportDocs")
                print("🗑️  Deleted existing SupportDocs collection")

            # Create collection with hybrid search (vector + BM25)
            from weaviate.classes.config import VectorDistances

            self.client.collections.create(
                name="SupportDocs",
                vectorizer_config=[Configure.NamedVectors.text2vec_openai(
                    name="default",
                    model="text-embedding-3-small"
                )],
                properties=[
                    Property(
                        name="content",
                        data_type=DataType.TEXT,
                        description="The chunk content"
                    ),
                    Property(
                        name="document",
                        data_type=DataType.TEXT,
                        description="Source document name"
                    ),
                    Property(
                        name="section",
                        data_type=DataType.TEXT,
                        description="Section within document"
                    ),
                    Property(
                        name="category",
                        data_type=DataType.TEXT,
                        description="Document category (Billing, Technical, Features)"
                    ),
                    Property(
                        name="chunk_index",
                        data_type=DataType.INT,
                        description="Index of chunk in document"
                    ),
                    Property(
                        name="total_chunks",
                        data_type=DataType.INT,
                        description="Total number of chunks in document"
                    )
                ]
            )
            print("✅ Created SupportDocs collection with Hybrid Search")
            return True

        except Exception as e:
            print(f"❌ Error creating schema: {e}")
            return False

    def extract_sections(self, content: str, filename: str) -> List[Dict]:
        """Extract sections from markdown document."""
        sections = []
        current_section = "Introduction"
        current_content = []

        lines = content.split("\n")

        for line in lines:
            # Check for section headers
            if line.startswith("## "):
                # Save previous section
                if current_content:
                    sections.append({
                        "section": current_section,
                        "content": "\n".join(current_content).strip()
                    })
                    current_content = []

                # Start new section
                current_section = line.replace("## ", "").strip()
            else:
                current_content.append(line)

        # Add last section
        if current_content:
            sections.append({
                "section": current_section,
                "content": "\n".join(current_content).strip()
            })

        return sections

    def chunk_document(self, filepath: Path) -> List[Dict]:
        """Chunk document with metadata."""
        print(f"\n📄 Processing: {filepath.name}")

        # Read document
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Determine category from filename
        category_map = {
            "billing": "Billing & Payments",
            "technical": "Technical Support",
            "features": "Features & Usage"
        }
        category = "General"
        for key, value in category_map.items():
            if key in filepath.stem.lower():
                category = value
                break

        # Extract sections
        sections = self.extract_sections(content, filepath.name)

        all_chunks = []

        for section_data in sections:
            section_name = section_data["section"]
            section_content = section_data["content"]

            if not section_content.strip():
                continue

            # Chunk the section
            chunks = self.text_splitter.split_text(section_content)

            for idx, chunk in enumerate(chunks):
                all_chunks.append({
                    "content": chunk,
                    "document": filepath.name,
                    "section": section_name,
                    "category": category,
                    "chunk_index": idx,
                    "total_chunks": len(chunks)
                })

        print(f"   → Created {len(all_chunks)} chunks")
        return all_chunks

    def index_documents(self, knowledge_base_path: str):
        """Index all documents in knowledge base."""
        kb_path = Path(knowledge_base_path)

        if not kb_path.exists():
            print(f"❌ Knowledge base path not found: {knowledge_base_path}")
            return False

        # Get all markdown files
        md_files = list(kb_path.glob("*.md"))

        if not md_files:
            print(f"❌ No markdown files found in {knowledge_base_path}")
            return False

        print(f"\n📚 Found {len(md_files)} documents to index")

        # Process all documents
        all_chunks = []
        for md_file in md_files:
            chunks = self.chunk_document(md_file)
            all_chunks.extend(chunks)

        print(f"\n📊 Total chunks to index: {len(all_chunks)}")

        # Batch insert into Weaviate
        try:
            collection = self.client.collections.get("SupportDocs")

            # Insert in batches of 100
            batch_size = 100
            for i in range(0, len(all_chunks), batch_size):
                batch = all_chunks[i:i + batch_size]

                with collection.batch.dynamic() as batch_context:
                    for chunk in batch:
                        batch_context.add_object(properties=chunk)

                print(f"   ✓ Indexed {min(i + batch_size, len(all_chunks))}/{len(all_chunks)} chunks")

            print(f"\n✅ Successfully indexed {len(all_chunks)} chunks")

            # Verify
            total = collection.aggregate.over_all(total_count=True)
            print(f"✅ Verification: {total.total_count} documents in Weaviate")

            return True

        except Exception as e:
            print(f"❌ Error indexing documents: {e}")
            return False

    def test_retrieval(self):
        """Test retrieval with sample queries."""
        print("\n🧪 Testing Retrieval\n")

        test_queries = [
            ("How do I request a refund?", "Billing & Payments"),
            ("API authentication error 401", "Technical Support"),
            ("How to enable dark mode?", "Features & Usage")
        ]

        collection = self.client.collections.get("SupportDocs")

        for query, expected_category in test_queries:
            print(f"\n🔍 Query: '{query}'")
            print(f"   Expected Category: {expected_category}")

            # Hybrid search (vector + keyword)
            response = collection.query.hybrid(
                query=query,
                limit=3,
                return_metadata=["score"]
            )

            if response.objects:
                print(f"   ✓ Found {len(response.objects)} results:")
                for i, obj in enumerate(response.objects, 1):
                    props = obj.properties
                    score = obj.metadata.score if hasattr(obj.metadata, 'score') else 'N/A'
                    print(f"      {i}. [{props['category']}] {props['document']} - {props['section']}")
                    print(f"         Score: {score}")
                    print(f"         Preview: {props['content'][:100]}...")
            else:
                print("   ❌ No results found")

    def close(self):
        """Close Weaviate connection."""
        if self.client:
            self.client.close()
            print("\n✅ Connection closed")


def main():
    """Main setup function."""
    print("=" * 60)
    print("🚀 State-of-the-Art RAG Setup")
    print("=" * 60)

    indexer = RAGIndexer()

    # Step 1: Connect
    if not indexer.connect():
        print("\n❌ Setup failed: Could not connect to Weaviate")
        print("\nℹ️  Make sure Weaviate is running:")
        print("   docker run -d -p 8080:8080 -e OPENAI_APIKEY=$OPENAI_API_KEY cr.weaviate.io/semitechnologies/weaviate:latest")
        return

    # Step 2: Create schema
    if not indexer.create_schema():
        print("\n❌ Setup failed: Could not create schema")
        indexer.close()
        return

    # Step 3: Index documents
    kb_path = Path(__file__).parent.parent / "knowledge_base"
    if not indexer.index_documents(str(kb_path)):
        print("\n❌ Setup failed: Could not index documents")
        indexer.close()
        return

    # Step 4: Test retrieval
    indexer.test_retrieval()

    # Close connection
    indexer.close()

    print("\n" + "=" * 60)
    print("✅ RAG Setup Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
