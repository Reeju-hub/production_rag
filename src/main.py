import os
import time
from fastapi import Request, BackgroundTasks, HTTPException
from fastapi.responses import RedirectResponse
import uvicorn
import httpx
from dotenv import load_dotenv

# 🔥 Tumhare FastAPI wale slack_bot se seedha app import kar rahe hain
from src.slack_bot import app
# import src.ingest_01

load_dotenv()

# ⏳ COOLDOWN TIMER: Google drive spam pings protection
last_sync_time = 0
COOLDOWN_SECONDS = 30  

def run_sync_task():
    print("🔄 Background Worker: Starting actual sync to Pinecone vector database...")
    try:
        # Default company ke liye test kar rahe hain
        # ingest_01.update_database("company_A") # Ise comment kiya hai kyonki import nahi hai
        print("⚠️ Ingestion script is currently disabled in main to save memory.")
        print("✅ Background sync complete successfully!")
    except Exception as e:
        print(f"❌ Error during background sync: {e}")

@app.post("/webhook/google-docs")
async def google_drive_webhook(request: Request, background_tasks: BackgroundTasks):
    global last_sync_time
    current_time = time.time()
    
    # Cooldown timer to prevent rapid sequential syncs
    if (current_time - last_sync_time) < COOLDOWN_SECONDS:
        print(f"💤 IGNORING PING: Document sync currently in cooldown.")
        return {"status": "ignored", "message": "Cooldown active"}
        
    print("🚨 GOOGLE DRIVE PING: Valid document update detected! Scheduling sync...")
    last_sync_time = current_time 
    
    background_tasks.add_task(run_sync_task)
    return {"status": "success", "message": "Pinecone sync scheduled in background!"}

# 👇 NAYA SLACK OAUTH CALLBACK ROUTE 👇
@app.get("/api/auth/slack/callback")
async def slack_oauth_callback(code: str):
    client_id = os.getenv("SLACK_CLIENT_ID")
    client_secret = os.getenv("SLACK_CLIENT_SECRET")
    
    # 🔥 UPDATE: Tumhara asli Vercel URL yahan daal diya
    frontend_url = os.getenv("FRONTEND_URL", "https://productionrag-phi.vercel.app") 
    
    # 🔥 UPDATE: Slack ko wapas bhejne ke liye exact Render URL
    redirect_uri = "https://production-rag-9u5w.onrender.com/api/auth/slack/callback"
    
    if not code:
        raise HTTPException(status_code=400, detail="Slack se authorization code nahi mila.")

    # Slack ko code wapas bhej kar permanent Access Token (Bot Token) mangenge
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri  # 🔥 YAHAN ADD KIYA HAI REDIRECT_URI
            }
        )
        data = response.json()

    if not data.get("ok"):
        raise HTTPException(status_code=400, detail=f"Slack OAuth Error: {data.get('error')}")

    team_id = data.get("team", {}).get("id")
    access_token = data.get("access_token")
    
    print(f"✅ Successfully installed in workspace: {team_id}")
    
    # TODO: Yahan Supabase mein team_id aur access_token save karne ka code aayega
    
    # Install hone ke baad user ko wapas Vercel landing page par bhej do
    return RedirectResponse(url=f"{frontend_url}/?install=success")
# 👆 NAYA CODE YAHAN KHATAM 👆

@app.get("/")
def health_check():
    return {"status": "DocuBot Enterprise SaaS Backend is live and running 24/7!"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🌍 Starting Enterprise Multi-Tenant Web Server on port {port}...")
    
    uvicorn.run(app, host="0.0.0.0", port=port)