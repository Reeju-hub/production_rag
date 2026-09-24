import os
import re
import tiktoken
import chromadb
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

def get_google_doc_text(doc_id):
    """Google Doc se live text nikalne ka function"""
    SCOPES = ['https://www.googleapis.com/auth/documents.readonly']
    SERVICE_ACCOUNT_FILE = 'credentials.json'
    
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('docs', 'v1', credentials=creds)
    document = service.documents().get(documentId=doc_id).execute()
    
    text = ""
    for element in document.get('body').get('content'):
        if 'paragraph' in element:
            for p_element in element.get('paragraph').get('elements'):
                if 'textRun' in p_element:
                    text += p_element.get('textRun').get('content')
    return text

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
    print("1. Reading data directly from Live Google Doc...")
    doc_id = os.environ.get("DESIGN_DOC_ID")
    raw_document = get_google_doc_text(doc_id)
    
    print("2. Chunking text...")
    chunks = smart_chunker(raw_document)
    
    print("3. Generating embeddings locally (FREE)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(chunks).tolist()
    
    print("4. Updating ChromaDB...")
    chroma_client = chromadb.PersistentClient(path="chromadb_store")
    
    # Purana kachra saaf karke nayi collection banao taaki koi confusion na ho
    try:
        chroma_client.delete_collection("design_docs_live")
    except:
        pass
        
    collection = chroma_client.get_or_create_collection(name="design_docs_live")
    
    ids = [f"doc_chunk_{i}" for i in range(len(chunks))]
    collection.upsert(ids=ids, embeddings=embeddings, documents=chunks)
    print("✅ Ingestion complete! Google Doc ka sara gyaan ab AI ke dimaag mein hai.")