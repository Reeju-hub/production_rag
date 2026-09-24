import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from groq import Groq
from slack_bolt import App
from dotenv import load_dotenv

load_dotenv()
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
slack_app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

def get_google_doc_sections(doc_id):
    """Google Doc padhta hai aur Headings ke Deep-links extract karta hai"""
    creds = service_account.Credentials.from_service_account_file(
        "credentials.json", scopes=['https://www.googleapis.com/auth/documents.readonly']
    )
    docs_service = build('docs', 'v1', credentials=creds)
    document = docs_service.documents().get(documentId=doc_id).execute()
    
    sections = {}
    current_heading = "General"
    current_heading_id = ""
    current_text = ""

    for element in document.get('body').get('content'):
        if 'paragraph' in element:
            para = element.get('paragraph')
            style = para.get('paragraphStyle', {}).get('namedStyleType', '')
            
            # Text extract karna
            text = "".join([run.get('textRun', {}).get('content', '') for run in para.get('elements', []) if 'textRun' in run])
            
            if "HEADING" in style and text.strip():
                # Purana section save karo
                if current_heading:
                    sections[current_heading] = {"text": current_text.strip(), "id": current_heading_id}
                
                # Naya section shuru karo
                current_heading = text.strip()
                current_heading_id = para.get('paragraphStyle', {}).get('headingId', '')
                current_text = ""
            else:
                current_text += text

    # Last section save karo
    sections[current_heading] = {"text": current_text.strip(), "id": current_heading_id}
    return sections

def detect_changes_and_notify(doc_id, channel_id="#design-updates"):
    """Changes check karta hai aur Slack par Summary bhejta hai"""
    print("[1] Fetching live Google Doc...")
    live_sections = get_google_doc_sections(doc_id)
    
    state_file = "data/doc_state.json"
    changes_detected = []

    # Purana state load karo
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            old_sections = json.load(f)
    else:
        old_sections = {}

    # Diffing (Compare karna)
    for heading, content in live_sections.items():
        if heading not in old_sections or old_sections[heading]["text"] != content["text"]:
            changes_detected.append({
                "section": heading,
                "new_text": content["text"],
                "link": f"https://docs.google.com/document/d/{doc_id}/edit#heading={content['id']}"
            })

    if not changes_detected:
        print("✅ No changes detected in the design system.")
        return

    print(f"[2] Found {len(changes_detected)} changes! Generating AI Summary...")
    
    # LLM se Summary banwana
    prompt = f"Summarize these design updates in 1 short sentence for developers:\n{json.dumps(changes_detected)}"
    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "system", "content": "You are a concise technical summarizer."}, {"role": "user", "content": prompt}]
    )
    summary = response.choices[0].message.content

    # Slack Message Format karna (Deep links ke sath)
    slack_blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "🚨 Design System Updated!", "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*AI Summary:*\n{summary}"}},
        {"type": "divider"}
    ]

    for change in changes_detected:
        slack_blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{change['section']}* was updated.\n<{change['link']}|🔗 Click here to view in Google Docs (including GIFs/Images)>"}
        })

    print("[3] Sending notification to Slack...")
    slack_app.client.chat_postMessage(channel=channel_id, text="Design Update", blocks=slack_blocks)

    # Naya state save kar lo taaki agli baar yahi dobara alert na kare
    os.makedirs("data", exist_ok=True)
    with open(state_file, "w") as f:
        json.dump(live_sections, f, indent=4)
    print("✅ Sync Complete!")

if __name__ == "__main__":
    detect_changes_and_notify(os.environ.get("DESIGN_DOC_ID"), channel_id="#design-updates")