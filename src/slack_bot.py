import os
import re
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

# Initialize Clients
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)

# 🔥 DYNAMIC MODEL AUTO-DISCOVERY
def get_working_models():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    try:
        data = requests.get(url, timeout=10).json()
        chat_model = "models/gemini-3.8-flash"
        embed_model = "models/text-embedding-004"
        if 'models' in data:
            valid_embeds = [m['name'] for m in data['models'] if 'embedContent' in m.get('supportedGenerationMethods', [])]
            if valid_embeds:
                embed_model = next((m for m in valid_embeds if '004' in m), valid_embeds[0])
            
            valid_chats = [m['name'] for m in data['models'] if 'generateContent' in m.get('supportedGenerationMethods', []) and 'gemini' in m['name']]
            if valid_chats:
                chat_model = next((m for m in valid_chats if '3.8-flash' in m), valid_chats[0])
        return chat_model, embed_model
    except:
        return "models/gemini-3.8-flash", "models/text-embedding-004"

# 🔥 PERMANENT STABLE OVERRIDE (Bypassing 503 High Demand completely)
CHAT_MODEL = "models/gemini-1.5-flash"
EMBED_MODEL = "models/text-embedding-004"

EMBEDDING_API_URL = f"https://generativelanguage.googleapis.com/v1beta/{EMBED_MODEL}:embedContent?key={GEMINI_API_KEY}"
CHAT_API_URL = f"https://generativelanguage.googleapis.com/v1beta/{CHAT_MODEL}:generateContent?key={GEMINI_API_KEY}"

INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "docubot-gemini-index")
user_memory = {}

class SlackEventPayload(BaseModel):
    token: str = None
    challenge: str = None
    type: str
    event: dict = None
    team_id: str = None

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
                    "text": f"🔍 Searching your secure Google Drive documents for: '{user_question}'..."
                }
            )
            init_data = init_res.json()
            if not init_data.get("ok"):
                return {"status": "slack_error", "detail": init_data.get("error")}
            
            message_ts = init_data["ts"]

            try:
                index = pc.Index(INDEX_NAME)
                
                # 🔥 DYNAMIC MODEL PAYLOAD
                embed_payload = {
                    "model": EMBED_MODEL,
                    "content": {"parts": [{"text": user_question}]}
                }
                embed_res = requests.post(EMBEDDING_API_URL, json=embed_payload, headers={'Content-Type': 'application/json'})
                
                if embed_res.status_code != 200:
                    raise Exception(f"Embedding API Error: {embed_res.text}")
                    
                query_vector = embed_res.json()['embedding']['values']

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
                
                chat_payload = {
                    "contents": [{"parts": [{"text": prompt}]}]
                }
                chat_res = requests.post(CHAT_API_URL, json=chat_payload, headers={'Content-Type': 'application/json'})
                
                if chat_res.status_code != 200:
                    raise Exception(f"Gemini API Error: {chat_res.text}")
                    
                final_answer = chat_res.json()['candidates'][0]['content']['parts'][0]['text']

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
                            },
                            {
                                "type": "actions",
                                "block_id": "feedback_block",
                                "elements": [
                                    {
                                        "type": "button",
                                        "text": {"type": "plain_text", "text": "👍 Helpful", "emoji": True},
                                        "value": "helpful_yes",
                                        "action_id": "btn_helpful"
                                    },
                                    {
                                        "type": "button",
                                        "text": {"type": "plain_text", "text": "👎 Not Helpful", "emoji": True},
                                        "value": "helpful_no",
                                        "action_id": "btn_not_helpful"
                                    }
                                ]
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