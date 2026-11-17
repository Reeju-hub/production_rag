processed_images_cache = {}

import os
import re
import json
import time
import hashlib
import tiktoken
import requests
import base64
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from pinecone import Pinecone, ServerlessSpec 

load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 🔥 ULTIMATE AUTO-DISCOVERY (Never gives 404)
def get_working_models():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    try:
        data = requests.get(url, timeout=10).json()
        valid_embeds = [m['name'] for m in data.get('models', []) if 'embedContent' in m.get('supportedGenerationMethods', [])]
        valid_chats = [m['name'] for m in data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', []) and 'gemini' in m['name']]
        
        embed_model = valid_embeds[0] if valid_embeds else "models/text-embedding-004"
        chat_model = valid_chats[0] if valid_chats else "models/gemini-1.5-flash"
        return chat_model, embed_model
    except:
        return "models/gemini-1.5-flash", "models/text-embedding-004"

CHAT_MODEL, EMBED_MODEL = get_working_models()

VISION_API_URL = f"https://generativelanguage.googleapis.com/v1beta/{CHAT_MODEL}:generateContent?key={GEMINI_API_KEY}"
EMBEDDING_API_URL = f"https://generativelanguage.googleapis.com/v1beta/{EMBED_MODEL}:embedContent?key={GEMINI_API_KEY}"

section_memory_file = "section_hashes.json"

# 🔥 EXPONENTIAL RETRY WRAPPER (Never fails on 503)
def call_gemini_with_retry(url, payload, max_retries=5):
    headers = {'Content-Type': 'application/json'}
    for attempt in range(max_retries):
        res = requests.post(url, json=payload, headers=headers)
        if res.status_code == 200:
            return res
        elif res.status_code == 503:
            wait_time = 2 ** attempt
            print(f"⚠️ Gemini 503 High Demand. Retrying attempt {attempt+2} in {wait_time}s...")
            time.sleep(wait_time)
        else:
            return res
    return None

def get_image_description(image_url):
    if image_url in processed_images_cache:
        return processed_images_cache[image_url]
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(image_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return f"Image download failed with status {response.status_code}"
            
        img_base64 = base64.b64encode(response.content).decode('utf-8')
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Describe what is strictly inside this image in detail. Maximum 2 lines. Answer in English."},
                    {"inlineData": {"mimeType": "image/jpeg", "data": img_base64}}
                ]
            }]
        }
        res = call_gemini_with_retry(VISION_API_URL, payload)
        if res and res.status_code == 200:
            description = res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            processed_images_cache[image_url] = description
            return description
        else:
            fallback_text = "Image description unavailable."
            processed_images_cache[image_url] = fallback_text
            return fallback_text
    except Exception as e:
        return "Image description unavailable."

def get_google_doc_sections(doc_id, process_images=True):
    SCOPES = ['https://www.googleapis.com/auth/documents.readonly']
    google_creds_string = os.environ.get("GOOGLE_CREDENTIALS")
    if google_creds_string:
        creds_info = json.loads(google_creds_string)
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    else:
        creds = service_account.Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        
    service = build('docs', 'v1', credentials=creds)
    document = service.documents().get(documentId=doc_id).execute()
    
    inline_objects = document.get('inlineObjects', {})
    sections = {}
    current_h2 = "Introduction (Top Section)"
    current_link = f"https://docs.google.com/document/d/{doc_id}/edit"
    current_text = ""

    for element in document.get('body').get('content'):
        if 'paragraph' in element:
            para = element.get('paragraph')
            style = para.get('paragraphStyle', {}).get('namedStyleType', '')
            heading_id = para.get('paragraphStyle', {}).get('headingId', '')
            
            line_text = ""
            for p_element in para.get('elements'):
                if 'textRun' in p_element:
                    line_text += p_element.get('textRun').get('content')
                elif 'inlineObjectElement' in p_element:
                    obj_id = p_element.get('inlineObjectElement').get('inlineObjectId')
                    if obj_id in inline_objects:
                        image_url = inline_objects[obj_id].get('inlineObjectProperties', {}).get('embeddedObject', {}).get('imageProperties', {}).get('contentUri')
                        if image_url:
                            if process_images:
                                description = get_image_description(image_url)
                                line_text += f"\n[🖼️ IMAGE DETECTED: {description}]\n"
                            else:
                                line_text += f"\n[🖼️ IMAGE ID: {obj_id}]\n"
            
            if style == 'HEADING_2' and line_text.strip():
                if current_text.strip():
                    sections[current_h2] = {"link": current_link, "text": current_text.strip()}
                current_h2 = line_text.strip()
                current_link = f"https://docs.google.com/document/d/{doc_id}/edit#heading={heading_id}"
                current_text = f"## {current_h2}\n"
            else:
                current_text += line_text
                
    if current_text.strip():
        sections[current_h2] = {"link": current_link, "text": current_text.strip()}
        
    return sections

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

def update_database(team_id: str = "company_A"):
    print(f"\nReading data directly from Live Google Doc for Workspace: {team_id}...")
    doc_id = os.environ.get("DESIGN_DOC_ID")
    
    if not doc_id:
        print("❌ Error: DESIGN_DOC_ID is missing in environment variables.")
        return []

    sections = get_google_doc_sections(doc_id, process_images=True)
    
    old_hashes = {}
    if os.path.exists(section_memory_file):
        with open(section_memory_file, "r") as f:
            old_hashes = json.load(f)
            
    new_hashes = {}
    updated_sections_info = []
    all_chunks = []

    print("2. Comparing Sections and Chunking text...")
    for sec_name, sec_data in sections.items():
        sec_text = sec_data["text"]
        sec_link = sec_data["link"]
        
        sec_hash = hashlib.md5(sec_text.encode('utf-8')).hexdigest()
        new_hashes[sec_name] = sec_hash
        
        if old_hashes.get(sec_name) != sec_hash:
            updated_sections_info.append(f"• *{sec_name}* | <{sec_link}|🔗 Jump to this section>")
            
        sec_chunks = smart_chunker(sec_text)
        all_chunks.extend(sec_chunks)

    with open(section_memory_file, "w") as f:
        json.dump(new_hashes, f)

    if not all_chunks:
        print("⚠ No text content found to embed.")
        return []

    print("3. Generating embeddings via Google REST API (Zero RAM)...")
    embeddings = []
    for i, chunk in enumerate(all_chunks):
        payload = {
            "model": EMBED_MODEL,
            "content": {"parts": [{"text": chunk}]}
        }
        res = call_gemini_with_retry(EMBEDDING_API_URL, payload)
        
        if res and res.status_code == 200:
            embeddings.append(res.json()['embedding']['values'])
            print(f"   Chunk {i+1}/{len(all_chunks)} embedded...")
        else:
            print(f"❌ Error embedding chunk {i+1}: {res.text if res else 'Service Unavailable'}")
            
    if not embeddings:
        print("⚠️ Koi valid vectors nahi mile, Pinecone update skip kar rahe hain.")
        return updated_sections_info

    print("4. Updating Pinecone CLOUD Database...")
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
    base_index = os.environ.get("PINECONE_INDEX_NAME", "docubot-index").lower()
    vector_dim = len(embeddings[0])
    
    # 🔥 IMMUNE TO DIMENSION MISMATCH: Appends dimension to index name!
    index_name = f"{base_index}-{vector_dim}"
    
    if index_name not in pc.list_indexes().names():
        print(f"☁️ Cloud par naya '{index_name}' index ban raha hai (Wait karo)...")
        pc.create_index(name=index_name, dimension=vector_dim, metric='cosine', spec=ServerlessSpec(cloud='aws', region='us-east-1'))
        while not pc.describe_index(index_name).status['ready']:
            time.sleep(1)
            
    index = pc.Index(index_name)
    namespace = f"workspace_{team_id}"
    
    vectors_to_upsert = []
    for i, (chunk, emb) in enumerate(zip(all_chunks, embeddings)):
        vectors_to_upsert.append({
            "id": f"doc_chunk_{i}",
            "values": emb,
            "metadata": {"text": chunk, "workspace_id": team_id} 
        })
        
    index.upsert(vectors=vectors_to_upsert, namespace=namespace)
    print(f"✅ BINGO! Google Doc ka sara gyaan Pinecone mein secure hai.\n")
    
    return updated_sections_info

if __name__ == "__main__":
    update_database("company_A")