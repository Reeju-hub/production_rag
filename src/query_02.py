import os
import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq
from dotenv import load_dotenv

# Load API keys
load_dotenv()
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def query_rag_system(user_question: str) -> dict:
    print(f"\n[Searching for:] {user_question}")
    
    # 1. Connect to ChromaDB
    chroma_client = chromadb.PersistentClient(path="chromadb_store")
    collection = chroma_client.get_collection(name="compliance_docs")
    
    # 2. Embed the user's question locally (Must match the ingestion model)
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_vector = model.encode(user_question).tolist()
    
    # 3. Retrieve the top 2 relevant chunks using vector math
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=2
    )
    
    retrieved_contexts = results["documents"][0]
    formatted_context = "\n---\n".join(retrieved_contexts)
    print("[Context Found!]")
    
    # 4. Build the Strict RAG Prompt
    system_prompt = """
    You are an internal corporate assistant. 
    Answer the user's question strictly using the provided Context. 
    If the answer is not in the context, say 'I cannot find the answer in the provided documents.'
    Do not use outside knowledge.
    """
    
    user_prompt = f"Context:\n{formatted_context}\n\nQuestion: {user_question}"
    
    # 5. Generate the Answer using Llama-3 (Free via Groq)
    print("[Generating Answer...]")
    response = groq_client.chat.completions.create(
       model="openai/gpt-oss-20b", 
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0
    )
    
    generated_answer = response.choices[0].message.content
    
    return {
        "question": user_question,
        "answer": generated_answer,
        "contexts": retrieved_contexts
    }

if __name__ == "__main__":
    # Test the system with a tricky question from our handbook
    test_question = "What is the penalty for violating GDPR, and who must be notified?"
    output = query_rag_system(test_question)
    
    print("\n================ FINAL ANSWER ================")
    print(output['answer'])
    print("==============================================")