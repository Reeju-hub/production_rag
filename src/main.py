import os
import time
from fastapi import Request, BackgroundTasks
import uvicorn
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
        ingest_01.update_database("company_A") 
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

@app.get("/")
def health_check():
    return {"status": "DocuBot Enterprise SaaS Backend is live and running 24/7!"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🌍 Starting Enterprise Multi-Tenant Web Server on port {port}...")
    
    # Seedha uvicorn se tumhara webhook API run hoga (No Socket Mode Threads!)
    uvicorn.run(app, host="0.0.0.0", port=port)