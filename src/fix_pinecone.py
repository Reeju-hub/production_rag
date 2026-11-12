import os
import time
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
index_name = "docubot-enterprise-index"

# Agar purana index hai toh usko delete karo
if index_name in pc.list_indexes().names():
    print(f"🚨 Purana 768 dimension wala '{index_name}' delete kar rahe hain...")
    pc.delete_index(index_name)
    print("⏳ Wait karo, Pinecone ko safai karne mein 10 second lagenge...")
    time.sleep(15)
    print("✅ Purana kachra delete ho gaya!")

# Naya 3072 index banao
print("🚀 Naya 3072 dimension wala Vector Index create kar rahe hain...")
pc.create_index(
    name=index_name,
    dimension=3072,
    metric="cosine",
    spec=ServerlessSpec(
        cloud="aws",
        region="us-east-1"
    )
)

print("🎉 YAY! Naya 3072 Index Successfully Created!")