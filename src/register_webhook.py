import os
import uuid
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

def register_google_drive_webhook():
    print("⏳ Registering Webhook with Google Drive...")
    
    # 1. Credentials (jo ingest_01 mein use hote hain)
    SCOPES = ['https://www.googleapis.com/auth/drive'] # Drive API chahiye (docs.readonly nahi chalega)
    SERVICE_ACCOUNT_FILE = 'credentials.json'
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    
    service = build('drive', 'v3', credentials=creds)
    
    # 2. Tumhari Details
    FILE_ID = os.environ.get("DESIGN_DOC_ID") # Ya yahan hardcode kar do: '1abcXYZ...'
    
    # 🔥 Yahan Apna Cloudflare URL daalo (aakhir mein /webhook/google-docs zaroor lagana)
    WEBHOOK_URL = "https://quantitative-rounds-integrated-philip.trycloudflare.com/webhook/google-docs"
    
    channel_id = str(uuid.uuid4()) # Har baar ek unique ID deni hoti hai
    
    body = {
        "id": channel_id,
        "type": "web_hook",
        "address": WEBHOOK_URL
    }
    
    try:
        # 3. Google ko bolo track karna shuru kare
        response = service.files().watch(fileId=FILE_ID, body=body).execute()
        print("✅ SUCCESS! Google Drive Webhook is now active!")
        print(f"Channel ID: {response['id']}")
        print(f"Webhook URL: {WEBHOOK_URL}")
        print("Ab jab bhi doc update hoga, Google is URL par turant ping karega.")
    except Exception as e:
        print(f"⚠️ Webhook registration failed: {e}")

if __name__ == "__main__":
    register_google_drive_webhook()