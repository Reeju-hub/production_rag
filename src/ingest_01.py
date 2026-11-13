# 🧠 SMART CACHE: Ek baar jo image padh li, uska description yahan save ho jayega taaki quota bar-bar waste na ho
processed_images_cache = {}
import os
import re
import json
import time
import tiktoken
import requests
from io import BytesIO
from PIL import Image
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
import google.generativeai as genai 
from google import genai
# 🔥 Pinecone Cloud Database import
from pinecone import Pinecone, ServerlessSpec 

load_dotenv()

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))


print("⏳ Loading AI Model into Memory (Ek baar time lagega, fir superfast chalega)...")
model = SentenceTransformer('all-MiniLM-L6-v2')

def get_image_description(image_url):
    """👁️ Smart Image Reader with Caching to save Gemini Quota"""
    if image_url in processed_images_cache:
        print("⚡ Cache hit! Image pehle se read hai, Gemini ko call nahi kiya.")
        return processed_images_cache[image_url]
        
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(image_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return f"Image download failed with status {response.status_code}"
            
        img = Image.open(BytesIO(response.content))
        vision_model = genai.GenerativeModel('gemini-flash-latest')
        
        res = vision_model.generate_content([
            "Describe what is strictly inside this image in detail (e.g., UI layout, artwork, text, or objects). Maximum 2 lines. Answer in English.", 
            img
        ])
        
        description = res.text.strip()
        processed_images_cache[image_url] = description
        return description
        
    except Exception as e:
        print(f"⚠️ Gemini Vision AI quota/error: {e}")
        fallback_text = "Image description unavailable due to API rate limit."
        processed_images_cache[image_url] = fallback_text
        return fallback_text

def get_google_doc_text(doc_id, process_images=True):
    """Google Doc se Text aur Images nikalna"""
    SCOPES = ['https://www.googleapis.com/auth/documents.readonly']
    
    # 🔥 Naya Logic: Environment Variable se securely padhna
    google_creds_string = os.environ.get("GOOGLE_CREDENTIALS")
    
    if google_creds_string:
        # Agar Render par live chal raha hai (Secret read karega)
        creds_info = json.loads(google_creds_string)
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    else:
        # Agar tumhare laptop par local chal raha hai
        SERVICE_ACCOUNT_FILE = 'tumhari_nayi_json_file_ka_naam.json' # Yahan local file ka naam rakh sakte ho
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        
    service = build('docs', 'v1', credentials=creds)
    document = service.documents().get(documentId=doc_id).execute()
    
    inline_objects = document.get('inlineObjects', {})
    text = ""
    # ... iske neeche ka saara code same rahega
    for element in document.get('body').get('content'):
        if 'paragraph' in element:
            para = element.get('paragraph')
            style = para.get('paragraphStyle', {}).get('namedStyleType', '')
            
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
                                print(f"🔗 DEBUG: Image detect hui! AI ko bhej rahe hain...")
                                description = get_image_description(image_url)
                                line_text += f"\n[🖼️ IMAGE DETECTED: {description}]\n"
                                time.sleep(2) 
                            else:
                                line_text += f"\n[🖼️ IMAGE ID: {obj_id}]\n"
            
            line_text = line_text.strip()
            if line_text:
                if style in ['HEADING_1', 'HEADING_2', 'HEADING_3']:
                    text += f"\n\n## {line_text}\n"
                else:
                    text += f"{line_text}\n"
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

# 🔥 MULTI-TENANT UPDATE: Ab yeh function kisi bhi specific team_id ke liye sync karega
def update_database(team_id: str = "company_A"):
    print(f"\n1. Reading data directly from Live Google Doc for Workspace: {team_id}...")
    doc_id = os.environ.get("DESIGN_DOC_ID")
    
    if not doc_id:
        print("❌ Error: DESIGN_DOC_ID is missing in environment variables.")
        return

    raw_document = get_google_doc_text(doc_id, process_images=True)
    
    print("2. Chunking text...")
    chunks = smart_chunker(raw_document)
    
    if not chunks:
        print("⚠️️ No text content found to embed.")
        return

    print("3. Generating embeddings locally...")
    embeddings = model.encode(chunks).tolist()
    
    print("4. Updating Pinecone CLOUD Database...")
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
    index_name = os.environ.get("PINECONE_INDEX_NAME", "docubot-enterprise-index")
    
    # Check if index exists, if not create it (384 dimensions for all-MiniLM-L6-v2)
    if index_name not in pc.list_indexes().names():
        print(f"☁️ Cloud par naya '{index_name}' index ban raha hai (Wait karo)...")
        pc.create_index(
            name=index_name,
            dimension=384,
            metric='cosine',
            spec=ServerlessSpec(cloud='aws', region='us-east-1')
        )
        while not pc.describe_index(index_name).status['ready']:
            time.sleep(1)
            
    index = pc.Index(index_name)
    
    # 🔥 SECURE NAMESPACE ISOLATION: Har company ka data uske apne workspace namespace mein jayega
    namespace = f"workspace_{team_id}"
    
    vectors_to_upsert = []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        vectors_to_upsert.append({
            "id": f"doc_chunk_{i}",
            "values": emb,
            "metadata": {
                "text": chunk, 
                "workspace_id": team_id # 🔥 Dynamic Security Tag
            } 
        })
        
    index.upsert(vectors=vectors_to_upsert, namespace=namespace)
    print(f"✅ BINGO! Google Doc ka sara gyaan CLOUD (Pinecone) ke namespace '{namespace}' mein secure hai.\n")

if __name__ == "__main__":
    update_database("company_A")