import os
import time
import difflib  # Naya jadoo jo changes pakdega
from slack_sdk import WebClient
from dotenv import load_dotenv

from ingest_01 import get_google_doc_text, update_database 

load_dotenv()

# Slack Client Setup
slack_client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
DOC_ID = os.environ.get("DESIGN_DOC_ID")
CHANNEL_NAME = "#design-updates"

def get_diff_summary(old_text, new_text):
    """Headings ke hisaab se changes ko track karta hai, par Images ke wording changes ignore karta hai"""
    old_lines = [line.strip() for line in old_text.split('\n') if line.strip()]
    new_lines = [line.strip() for line in new_text.split('\n') if line.strip()]
    
    diff = list(difflib.ndiff(old_lines, new_lines))
    
    summary_dict = {}
    current_heading = "General Information" # Default agar heading na ho
    
    for line in diff:
        code = line[:2]
        content = line[2:].strip()
        
        # Agar line '##' se shuru hoti hai, toh current_heading update karlo
        if content.startswith('## '):
            current_heading = content.replace('## ', '').strip()
        elif content.startswith('# '):
            current_heading = content.replace('# ', '').strip()
            
        # Headings ko aur khali lines ko changes mein add nahi karna hai
        if not content or content.startswith('#'):
            continue
            
        # 🔥 THE PRO FIX: Image tags, IDs, aur errors ko ignore karega 
        if "[🖼️ IMAGE" in content or "Ek image add ki gayi hai" in content or "IMAGE ID:" in content:
            continue
            
        # Changes ko uski heading ke dabe (box) mein daalo
        if code == '+ ':
            if current_heading not in summary_dict:
                summary_dict[current_heading] = {'added': [], 'removed': []}
            summary_dict[current_heading]['added'].append(content)
        elif code == '- ':
            if current_heading not in summary_dict:
                summary_dict[current_heading] = {'added': [], 'removed': []}
            summary_dict[current_heading]['removed'].append(content)
    
    # Slack ke liye khubsurat message format
    summary = ""
    for heading, changes in summary_dict.items():
        if changes['added'] or changes['removed']:
            summary += f"\n📍 *Section:* `{heading}`\n"
            for item in changes['added']:
                summary += f"> 🟢 *Added:* {item}\n"
            for item in changes['removed']:
                summary += f"> 🔴 *Removed:* {item}\n"
    
    return summary if summary else "*Minor formatting ya Image Description update hua hai.*\n\n"

def start_tracker():
    print("🔄 Auto-Sync Tracker Started! Har 15 seconds mein check karega...")
    last_text = None  # Ab hum hash ki jagah poora text dimaag mein rakhenge
    
    while True:
        try:
            print("⏳ Checking Google Doc for updates (Fast Mode - No API cost)...")
            current_text = get_google_doc_text(DOC_ID, process_images=False)
            
            # Pehli baar chalne par
            if last_text is None:
                last_text = current_text
                print("✅ Tracker ready. Waiting for any changes in the Doc...")
                
            # Agar text change hua hai!
            elif current_text != last_text:
                print("🚨 Naya Update pakda gaya! Summary bana raha hoon...")
                
                # 1. Kya change hua uski summary nikalna
                changes_summary = get_diff_summary(last_text, current_text)
                
                # 2. AI database update karna (Super fast wala)
                update_database()
                
                # 3. Naya zabardast Slack Message Format
                slack_message = (
                    f"🚨 *Design Guidelines Updated!*\n\n"
                    f"*Changes Made:*\n"
                    f"{changes_summary}"
                    f"🔗 <https://docs.google.com/document/d/{DOC_ID}|Click here to view full Document>\n"
                    f"_(These changes are updated in my mind!)_"
                )
                
                slack_client.chat_postMessage(
                    channel=CHANNEL_NAME,
                    text=slack_message
                )
                
                last_text = current_text
                print("✅ Summary has been sent to Slack and AI is updated!")
            else:
                print("💤 No changes detected. All up-to-date.")
                
        except Exception as e:
            print(f"❌ Error : {e}")
            
        # 15 seconds ke liye script ko sula do
        time.sleep(15)

if __name__ == "__main__":
    start_tracker()