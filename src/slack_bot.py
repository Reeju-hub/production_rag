print("⏳ Starting bot and loading AI models (please wait 20-30 seconds)...")
import os
import re
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import query_hybrid  # Tumhara purana RAG query engine

load_dotenv()
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

@app.event("app_mention")
def handle_mention(body, say):
    print("🔔 YAY! Slack se message Python tak pahunch gaya!") # <-- YEH LINE ADD KARO
    raw_text = body["event"]["text"]
    user_question = re.sub(r'<@.*?>', '', raw_text).strip()
    
    say(f"🔍 Searching the design guidelines for: '{user_question}'...")
    
    try:
        # ChromaDB aur LLM se answer nikalna
        output = query_hybrid.query_rag_system(user_question)
        answer = output["answer"]
        say(f"💡 *Answer:*\n{answer}")
        
    except Exception as e:
        say(f"⚠️ Oops, error fetching data: {str(e)}")

if __name__ == "__main__":
    print("🤖 Slack Answering Bot is running! Waiting for team questions...")
    SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN")).start()