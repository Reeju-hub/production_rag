import os
from sentence_transformers import SentenceTransformer
from groq import Groq
from dotenv import load_dotenv
from pinecone import Pinecone  # 🔥 Pinecone cloud search

load_dotenv()
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# 🔥 SPEED OPTIMIZATION: Model ko global kar diya taaki baar-baar load na ho
print("⏳ Loading embedding model globally...")
model = SentenceTransformer('all-MiniLM-L6-v2')

def query_rag_system(user_question: str, top_k: int = 2, chat_history: list = None) -> dict:
    """Purana non-streaming function (Safe-keeping ke liye)"""
    res, best_contexts = query_rag_system_stream(user_question, top_k, chat_history, stream=False)
    
    # Non-streaming response generate karna
    full_answer = ""
    for chunk in res:
        delta = chunk.choices[0].delta.content
        if delta:
            full_answer += delta
            
            # Environment variable ya direct doc link yahan daal do
    google_doc_url = os.environ.get("GOOGLE_DOC_URL", "https://docs.google.com/document/d/1zJLTPR2DTa9Zty7lrPEEYuAQak-WtOLdYgiUXSd0-F8/edit?tab=t.0#heading=h.rg2hekih0iri")
            
    return {
        "question": user_question,
        "answer": full_answer,
        "contexts": best_contexts,
        "source_link": google_doc_url
    }

def query_rag_system_stream(user_question: str, top_k: int = 2, chat_history: list = None, stream: bool = True):
    """🔥 NAYA: Streaming aur Non-streaming dono support karne wala smart engine"""
    if chat_history is None:
        chat_history = []
        
    search_query = user_question
    
    # 🧠 Query Reformulation (Chat History ke sath)
    if chat_history:
        print("🧠 Rewriting query using Chat History...")
        history_str = "\n".join([f"User: {q}\nAI: {a}" for q, a in chat_history])
        
        rewrite_prompt = f"""Chat History:
{history_str}

Follow-up Question: {user_question}

Rewrite the Follow-up Question into a clear, standalone search query by replacing pronouns (like 'uski', 'it') with the actual subject from the history. 
Return ONLY the rewritten query, no extra words."""

        try:
            rewrite_res = groq_client.chat.completions.create(
                model="openai/gpt-oss-20b", 
                messages=[{"role": "user", "content": rewrite_prompt}],
                temperature=0
            )
            search_query = rewrite_res.choices[0].message.content.strip()
            print(f"🔄 Original: '{user_question}' --> Smart Search: '{search_query}'")
        except Exception as e:
            print(f"⚠️ Query rewrite failed: {e}")

    # 1. ☁️ Connect to Pinecone CLOUD Database
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
    index_name = os.environ.get("PINECONE_INDEX_NAME")
    index = pc.Index(index_name)
    
    # 2. Dense Vector Search with Multi-Tenant Security Filter
    print("🔍 Searching Pinecone Cloud Database...")
    query_vector = model.encode(search_query).tolist()
    
    vector_results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
        filter={"workspace_id": {"$eq": "company_A"}} # 🔥 MULTI-TENANT SECURITY
    )
    
    best_contexts = []
    for match in vector_results.get("matches", []):
        if match.get("metadata") and "text" in match["metadata"]:
            best_contexts.append(match["metadata"]["text"])
            
    formatted_context = "\n---\n".join(best_contexts) if best_contexts else "No context found."
    
    # 3. Groq Answer Generation System Prompt
    system_prompt = """
    You are an internal corporate assistant. 
    Answer the user's question strictly using the provided Context and Chat History. 
    If the answer is not in the context, say 'I cannot find the answer in the provided documents.'
    Do not use outside knowledge.
    
    The provided context contains section headings formatted with '##' (e.g., ## Design Rules). 
    You MUST start your answer by stating exactly which heading the information was found in. 
    Format the first line of your answer exactly like this:
    📍 Source Section: [Name of Heading]
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    
    for past_q, past_a in chat_history:
        messages.append({"role": "user", "content": past_q})
        messages.append({"role": "assistant", "content": past_a})
        
    user_prompt = f"Context:\n{formatted_context}\n\nQuestion: {user_question}"
    messages.append({"role": "user", "content": user_prompt})
    
    # 🔥 Groq API Call with Streaming support
    stream_response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=messages,
        temperature=0,
        stream=stream
    )
    
    return stream_response, best_contexts

if __name__ == "__main__":
    test_q = "What are the design guidelines?"
    print("\n[Testing Cloud Pinecone Pipeline...]")
    res, _ = query_rag_system_stream(test_q, stream=False)
    for chunk in res:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="")
    print()