import os
import time
from fastapi import Request, BackgroundTasks, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
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

# 👇 NAYA: Slack par updated sections ke sath message bhejne ka function 👇
async def send_slack_notification(access_token: str, updated_sections: list):
    print("🚀 Sending smart notification to Slack...")
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Agar list khali hai (koi changes pakad mein nahi aaye)
        if not updated_sections:
             text_message = "🚨 *Google Drive Sync Complete:* The document was scanned, but no new H2 section changes were detected. 🔄"
        else:
             # List ko naye lines mein jod kar message banao
             sections_text = "\n".join(updated_sections)
             text_message = f"🚨 *Google Drive Update Detected!*\nThe following sections were updated:\n\n{sections_text}\n\n✅ *Background Pinecone Sync Complete!*"
             
        payload = {
            "channel": "C0C4BC2FN20",  # Abhi test karne ke liye default channel
            "text": text_message
        }
        
        response = await client.post(
            "https://slack.com/api/chat.postMessage", 
            headers=headers, 
            json=payload
        )
        data = response.json()
        if data.get("ok"):
            print("✅ Slack par Smart Message successfully chala gaya!")
        else:
            print(f"❌ Slack message error: {data.get('error')}")

# 👇 UPDATE: Ab yeh sync karega, updated list niklaega, aur uske baad notification bhejega 👇
async def run_sync_and_notify(bot_token: str):
    print("🔄 Background Worker: Starting actual sync to Pinecone vector database...")
    try:
        # H2 Updates wali list hume ingest_01 se yahan mil jayegi
        updated_sections = src.ingest_01.update_database("company_A") 
        
        print("✅ Background sync complete successfully!")
        
        # Sync khatam hone ke baad ab message bhejenge
        await send_slack_notification(bot_token, updated_sections)
        
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
        
    print("🚨 GOOGLE DRIVE PING: Valid document update detected! Fetching token from Supabase...")
    last_sync_time = current_time 
    
    # 1. Supabase se token nikalna
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if supabase_url and supabase_key:
        try:
            supabase: Client = create_client(supabase_url, supabase_key)
            db_response = supabase.table("slack_installations").select("access_token").limit(1).execute()
            
            if db_response.data and len(db_response.data) > 0:
                bot_token = db_response.data[0]["access_token"]
                
                # 2. Token milne par Background mein sirf ek task chala do jo sync karke notify karega
                background_tasks.add_task(run_sync_and_notify, bot_token)
            else:
                print("⚠️ Supabase mein koi Slack token nahi mila!")
                
        except Exception as e:
            print(f"❌ Supabase fetch error: {e}")
    else:
        print("⚠️ Supabase credentials render environment mein nahi mile!")

    return {"status": "success", "message": "Webhook processed, background sync started!"}

# DHYAN RAHE: "google123456789.html" ko apne asli file ke naam se replace karna
@app.get("/google546e6a17c1bc90a2.html")
def google_verification():
    return HTMLResponse(content="google-site-verification: google546e6a17c1bc90a2.html")

# 👇 SLACK OAUTH CALLBACK ROUTE 👇
@app.get("/api/auth/slack/callback")
async def slack_oauth_callback(code: str):
    client_id = os.getenv("SLACK_CLIENT_ID")
    client_secret = os.getenv("SLACK_CLIENT_SECRET")
    frontend_url = os.getenv("FRONTEND_URL", "https://productionrag-phi.vercel.app") 
    redirect_uri = "https://production-rag-9u5w.onrender.com/api/auth/slack/callback"
    
    if not code:
        raise HTTPException(status_code=400, detail="Slack se authorization code nahi mila.")

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

    return RedirectResponse(url=f"{frontend_url}/?install=success")

@app.get("/")
def health_check():
    return {"status": "DocuBot Enterprise SaaS Backend is live and running 24/7!"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🌍 Starting Enterprise Multi-Tenant Web Server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)