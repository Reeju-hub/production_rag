import os
import re
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from pathlib import Path
from supabase import create_client
from pinecone import Pinecone
import google.generativeai as genai
import httpx

load_dotenv()
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")

app = FastAPI(title="DocuBot.ai Enterprise Multi-Tenant Backend")

# Initialize Clients
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# Dhyan rakhna, yeh wahi index naam ho jo ingest_01.py mein (768 dimension ke sath) bana hai
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
    # 1. Handle Slack URL Verification Challenge
    if payload.type == "url_verification":
        return {"challenge": payload.challenge}

    event = payload.event
    if not event:
        return {"status": "ignored"}

    # 2. Process App Mentions (@DocuBot)
    if event.get("type") == "app_mention":
        team_id = payload.team_id
        channel_id = event.get("channel")
        user_id = event.get("user")
        raw_text = event.get("text", "")
        
        user_question = re.sub(r'<@.*?>', '', raw_text).strip()
        if not user_question:
            return {"status": "empty_query"}

        # 3. Fetch Company Bot Token from Supabase dynamically
        db_response = supabase.table("slack_installations").select("access_token").eq("team_id", team_id).execute()
        
        if not db_response.data or len(db_response.data) == 0:
            raise HTTPException(status_code=403, detail="Workspace installation token not found")

        bot_access_token = db_response.data[0]["access_token"]
        history = user_memory.get(user_id, [])

        async with httpx.AsyncClient() as client:
            # Send initial searching message
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
                # 4. Perform Vector Search inside Isolated Pinecone Namespace
                index = pc.Index(INDEX_NAME)
                
                # 🔥 FIX 1: Purane syntax se embedding nikalna
                embed_response = genai.embed_content(
                    model="models/text-embedding-004",
                    content=user_question
                )
                query_vector = embed_response['embedding']

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

                # 5. Generate Answer using Gemini Model
                prompt = f"""You are DocuBot.ai, an elite enterprise AI assistant. Use the following context retrieved from the company's secure Google Docs to answer the user query accurately.

Context:
{context_text}

User Query: {user_question}
Answer:"""

                # 🔥 FIX 2: Purane syntax se AI ka answer nikalna
                vision_model = genai.GenerativeModel('gemini-1.5-flash')
                ai_response = vision_model.generate_content(prompt)
                final_answer = ai_response.text

                citation_url = os.environ.get("GOOGLE_DOC_URL", "https://docs.google.com")

                # 6. Update message with Answer & Interactive Feedback Buttons
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

                # Update memory
                history.append((user_question, final_answer))
                if len(history) > 3:
                    history.pop(0)
                user_memory[user_id] = history

            except Exception as e:
                print(f"RAG / AI Pipeline Error: {e}")
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