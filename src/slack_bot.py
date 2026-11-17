import os
import re
import time
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from pathlib import Path
from supabase import create_client
from pinecone import Pinecone
import httpx
import requests

load_dotenv()
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="DocuBot.ai Enterprise Multi-Tenant Backend")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)

# 🔥 DOUBLE ENTERPRISE FAILOVER (For both Chat & Embeddings)
def get_working_models():
    stable_chat_models = [
        "models/gemini-1.5-flash", 
        "models/gemini-1.5-pro",
        "models/gemini-pro" 
    ]
    # Naya Waterfall: Pehle 004 try karega, fir 001
    stable_embed_models = [
        "models/text-embedding-004",
        "models/embedding-001"
    ]
    return stable_chat_models, stable_embed_models

ALL_CHAT_MODELS, ALL_EMBED_MODELS = get_working_models()
BASE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "docubot-index").lower()
user_memory = {}

class SlackEventPayload(BaseModel):
    token: str = None
    challenge: str = None
    type: str
    event: dict = None
    team_id: str = None

# 🔥 EXPONENTIAL BACKOFF
def call_gemini_with_retry(url, payload, max_retries=3):
    headers = {'Content-Type': 'application/json'}
    res = None
    for attempt in range(max_retries):
        res = requests.post(url, json=payload, headers=headers)
        if res.status_code == 200:
            return res
        elif res.status_code in [503, 429]:
            wait_time = 2 ** attempt 
            print(f"⚠️ API Overloaded ({res.status_code}). Retrying in {wait_time}s...")
            time.sleep(wait_time)
        else:
            return res
    return res # Return exact error instead of None

@app.post("/api/slack/events")
async def slack_events(payload: SlackEventPayload):
    if payload.type == "url_verification":
        return {"challenge": payload.challenge}

    event = payload.event
    if not event:
        return {"status": "ignored"}

    if event.get("type") == "app_mention":
        team_id = payload.team_id
        channel_id = event.get("channel")
        user_id = event.get("user")
        raw_text = event.get("text", "")
        
        user_question = re.sub(r'<@.*?>', '', raw_text).strip()
        if not user_question:
            return {"status": "empty_query"}

        db_response = supabase.table("slack_installations").select("access_token").eq("team_id", team_id).execute()
        
        if not db_response.data or len(db_response.data) == 0:
            raise HTTPException(status_code=403, detail="Workspace installation token not found")

        bot_access_token = db_response.data[0]["access_token"]
        history = user_memory.get(user_id, [])

        async with httpx.AsyncClient() as client:
            init_res = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {bot_access_token}"},
                json={
                    "channel": channel_id,
                    "text": f"🔍 Searching secure documents for: '{user_question}'..."
                }
            )
            init_data = init_res.json()
            if not init_data.get("ok"):
                return {"status": "slack_error", "detail": init_data.get("error")}
            
            message_ts = init_data["ts"]

            try:
                # 1. 🔥 EMBEDDING WATERFALL (Agar fail hua toh doosra model use karega)
                query_vector = None
                last_embed_error = "Service Unavailable"
                
                for emb_model in ALL_EMBED_MODELS:
                    print(f"🔄 Trying embedding model: {emb_model}...")
                    emb_url = f"https://generativelanguage.googleapis.com/v1beta/{emb_model}:embedContent?key={GEMINI_API_KEY}"
                    embed_payload = {"model": emb_model, "content": {"parts": [{"text": user_question}]}}
                    
                    embed_res = call_gemini_with_retry(emb_url, embed_payload, max_retries=2)
                    
                    if embed_res and embed_res.status_code == 200:
                        query_vector = embed_res.json()['embedding']['values']
                        break 
                    else:
                        last_embed_error = embed_res.text if embed_res else "503/429 Error"
                        print(f"⚠️ Embedding model {emb_model} failed. Switching to next...")

                if not query_vector:
                    raise Exception(f"All Embedding Models failed! Last error: {last_embed_error}")
                    
                vector_dim = len(query_vector)
                
                # 2. Search Pinecone
                dynamic_index_name = f"{BASE_INDEX_NAME}-{vector_dim}"
                index = pc.Index(dynamic_index_name)

                namespace = f"workspace_{team_id}"
                search_results = index.query(
                    namespace=namespace,
                    vector=query_vector,
                    top_k=3,
                    include_metadata=True
                )

                context_text = "\n\n".join([match["metadata"].get("text", "") for match in search_results.get("matches", [])])
                if not context_text:
                    context_text = "No relevant enterprise documents found in your synchronized Google Drive repository."

                prompt = f"You are DocuBot.ai, an elite enterprise AI assistant. Use the following context retrieved from the company's secure Google Docs to answer the user query accurately.\n\nContext:\n{context_text}\n\nUser Query: {user_question}\nAnswer:"
                
                # 3. 🔥 CHAT MODEL WATERFALL
                final_answer = None
                last_chat_error = "Service Unavailable"
                
                for model_name in ALL_CHAT_MODELS:
                    print(f"🤖 Attempting answer with chat model: {model_name}...")
                    chat_url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={GEMINI_API_KEY}"
                    chat_payload = {"contents": [{"parts": [{"text": prompt}]}]}
                    
                    chat_res = call_gemini_with_retry(chat_url, chat_payload, max_retries=2)
                    
                    if chat_res and chat_res.status_code == 200:
                        final_answer = chat_res.json()['candidates'][0]['content']['parts'][0]['text']
                        break 
                    else:
                        last_chat_error = chat_res.text if chat_res else "503/429 Error"
                        print(f"⚠️ Chat Model {model_name} failed. Switching to next...")
                        
                if not final_answer:
                    raise Exception(f"All Chat Models failed! Last error: {last_chat_error}")

                citation_url = os.environ.get("GOOGLE_DOC_URL", "https://docs.google.com")

                await client.post(
                    "https://slack.com/api/chat.update",
                    headers={"Authorization": f"Bearer {bot_access_token}"},
                    json={
                        "channel": channel_id,
                        "ts": message_ts,
                        "text": f"💡 *Answer:*\n{final_answer}",
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"💡 *Answer:*\n{final_answer}\n\n🔗 *<{citation_url}|View Source Document & Deep-Dive>*"
                                }
                            },
                            {
                                "type": "divider"
                            }
                        ]
                    }
                )

                history.append((user_question, final_answer))
                if len(history) > 3:
                    history.pop(0)
                user_memory[user_id] = history

            except Exception as e:
                print(f"RAG / AI Pipeline Error: {str(e)}")
                await client.post(
                    "https://slack.com/api/chat.update",
                    headers={"Authorization": f"Bearer {bot_access_token}"},
                    json={
                        "channel": channel_id,
                        "ts": message_ts,
                        "text": f"⚠️ Oops, error fetching data: {str(e)}"
                    }
                )

    return {"status": "success"}