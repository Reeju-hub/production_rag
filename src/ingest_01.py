import os
import re
import tiktoken
import chromadb
from sentence_transformers import SentenceTransformer

def smart_chunker(text: str, max_tokens: int = 300) -> list[str]:
    encoder = tiktoken.encoding_for_model("text-embedding-3-small")
    paragraphs = re.split(r'\n\s*\n', text)
    chunks, current_chunk, current_tokens = [], "", 0
    
    for para in paragraphs:
        para_tokens = len(encoder.encode(para))
        if current_tokens + para_tokens > max_tokens and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk, current_tokens = "", 0
        current_chunk += "\n\n" + para
        current_tokens += para_tokens
        
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

if __name__ == "__main__":
    print("1. Reading proprietary data...")
    with open("data/compliance_handbook.txt", "r", encoding="utf-8") as file:
        raw_document = file.read()
    
    print("2. Chunking text...")
    chunks = smart_chunker(raw_document)
    
    print("3. Generating embeddings locally (FREE)...")
    # Downloads a small AI model to your PC and runs it locally
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(chunks).tolist()
    
    print("4. Storing in ChromaDB...")
    chroma_client = chromadb.PersistentClient(path="chromadb_store")
    collection = chroma_client.get_or_create_collection(name="compliance_docs")
    
    ids = [f"handbook_chunk_{i}" for i in range(len(chunks))]
    collection.upsert(ids=ids, embeddings=embeddings, documents=chunks)
    print("Ingestion complete! You should see a 'chromadb_store' folder appear.")