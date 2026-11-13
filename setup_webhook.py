from google.oauth2 import service_account
from googleapiclient.discovery import build
import uuid

# 👇 YAHAN APNI DETAILS DAALNA 👇

# 1. Apni JSON file ka exact naam yahan likho (jo abhi download ki hai)
SERVICE_ACCOUNT_FILE = 'gifted-slice-472109-g6-86e986eae8e0.json'

# 2. Apne Google Doc ka File ID yahan daalo (Google doc ke URL mein d/... aur .../edit ke beech ka lamba code)
FILE_ID = '1zJLTPR2DTa9Zty7lrPEEYuAQak-WtOLdYgiUXSd0-F8' 

# 3. Tumhara Render ka Webhook URL (Yeh same hi rahega)
WEBHOOK_URL = 'https://production-rag-9u5w.onrender.com/webhook/google-docs'


def setup_drive_webhook():
    print("Google se connect kar rahe hain...")
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/drive.readonly']
    )
    drive_service = build('drive', 'v3', credentials=credentials)

    body = {
        "id": str(uuid.uuid4()),  # Ek random ID generate hoti hai
        "type": "web_hook",
        "address": WEBHOOK_URL
    }

    try:
        response = drive_service.files().watch(fileId=FILE_ID, body=body).execute()
        print("✅ SUCCESS! Google Drive Webhook setup ho gaya!")
        print("Google ka response:", response)
    except Exception as e:
        print("❌ Error aayi:", e)

if __name__ == '__main__':
    setup_drive_webhook()