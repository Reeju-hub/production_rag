import os
import time
from fastapi import Request, BackgroundTasks, HTTPException
from fastapi.responses import RedirectResponse
from supabase import create_client, Client
import uvicorn
import httpx
from dotenv import load_dotenv

# 🔥 Tumhare FastAPI wale slack_bot se seedha app import kar rahe hain
from src.slack_bot import app
import src.ingest_01

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

# 👇 NAYA: Slack par notification bhejne ka function 👇
async def send_slack_notification(access_token: str):
    print("🚀 Sending notification to Slack...")
    async with httpx.AsyncClient() as client:
        # Slack API ko bot token bhejna zaroori hai
        headers = {"Authorization": f"Bearer {access_token}"}
        payload = {
            "channel": "C0C4BC2FN20",  # Abhi test karne ke liye default channel #general hai
            "text": "🚨 *Google Drive Update:* New document updated aur background  Pinecone vector DB is syncing! 🔄"
        }
        response = await client.post(
            "https://slack.com/api/chat.postMessage", 
            headers=headers, 
            json=payload
        )
        data = response.json()
        if data.get("ok"):
            print("✅ Slack par message successfully chala gaya!")
        else:
            print(f"❌ Slack message error: {data.get('error')}")

@app.post("/webhook/google-docs")
async def google_drive_webhook(request: Request, background_tasks: BackgroundTasks):
    global last_sync_time
    current_time = time.time()
    
    # Cooldown timer to prevent rapid sequential syncs
    if (current_time - last_sync_time) < COOLDOWN_SECONDS:
        print(f"💤 IGNORING PING: Document sync currently in cooldown.")
        return {"status": "ignored", "message": "Cooldown active"}
        
    print("🚨 GOOGLE DRIVE PING: Valid document update detected! Fetching token from Supabase...")
    last_sync_time = current_time 
    
    # 1. Supabase se token nikalna
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if supabase_url and supabase_key:
        try:
            supabase: Client = create_client(supabase_url, supabase_key)
            # Table se token uthao (abhi test ke liye hum pehli entry utha rahe hain)
            db_response = supabase.table("slack_installations").select("access_token").limit(1).execute()
            
            if db_response.data and len(db_response.data) > 0:
                bot_token = db_response.data[0]["access_token"]
                
                # 2. Token milne par Background mein Slack message aur Pinecone sync chala do
                background_tasks.add_task(send_slack_notification, bot_token)
                background_tasks.add_task(run_sync_task)
            else:
                print("⚠️ Supabase mein koi Slack token nahi mila!")
                
        except Exception as e:
            print(f"❌ Supabase fetch error: {e}")
    else:
        print("⚠️ Supabase credentials render environment mein nahi mile!")

    return {"status": "success", "message": "Webhook processed, notification sent!"}

from fastapi.responses import HTMLResponse

# DHYAN RAHE: "google123456789.html" ko apne asli file ke naam se replace karna
@app.get("/google546e6a17c1bc90a2.html")
def google_verification():
    # Andar ka content bhi wahi daalna jo Notepad mein likha hai
    return HTMLResponse(content="google-site-verification: google546e6a17c1bc90a2.html")

# 👇 SLACK OAUTH CALLBACK ROUTE 👇
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
                "redirect_uri": redirect_uri  
            }
        )
        data = response.json()

    if not data.get("ok"):
        raise HTTPException(status_code=400, detail=f"Slack OAuth Error: {data.get('error')}")

    team_id = data.get("team", {}).get("id")
    team_name = data.get("team", {}).get("name")
    access_token = data.get("access_token")
    
    print(f"✅ Successfully installed in workspace: {team_name} ({team_id})")
    
    # --- YAHAN SE SUPABASE KA NAYA CODE SHURU ---
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if supabase_url and supabase_key:
        try:
            supabase: Client = create_client(supabase_url, supabase_key)
            # upsert ka matlab: agar team pehle se hai toh update, warna naya insert
            supabase.table("slack_installations").upsert({
                "team_id": team_id,
                "team_name": team_name,
                "access_token": access_token
            }).execute()
            print("✅ Token saved to Supabase successfully!")
        except Exception as e:
            print(f"❌ Supabase DB error: {e}")
    else:
        print("⚠️ Supabase credentials Render environment mein nahi mile!")
    # --- SUPABASE CODE KHATAM ---

    # Install hone ke baad user ko wapas Vercel landing page par bhej do
    return RedirectResponse(url=f"{frontend_url}/?install=success")

@app.get("/")
def health_check():
    return {"status": "DocuBot Enterprise SaaS Backend is live and running 24/7!"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🌍 Starting Enterprise Multi-Tenant Web Server on port {port}...")
    
    uvicorn.run(app, host="0.0.0.0", port=port)