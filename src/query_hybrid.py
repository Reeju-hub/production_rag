import os
import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq
from rank_bm25 import BM25Okapi
from dotenv import load_dotenv

load_dotenv()
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def reciprocal_rank_fusion(vector_results: list, bm25_results: list, k: int = 60) -> list:
    """
    RRF algorithm: Ranks combine karta hai bina arbitrary scores compare kiye.
    """
    rrf_scores = {}
    
    # Dense vector ranks score
    for rank, doc in enumerate(vector_results, start=1):
        rrf_scores[doc] = rrf_scores.get(doc, 0.0) + 1 / (k + rank)
        
    # BM25 sparse ranks score
    for rank, doc in enumerate(bm25_results, start=1):
        rrf_scores[doc] = rrf_scores.get(doc, 0.0) + 1 / (k + rank)
        
    # Sort descending by score
    sorted_fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return [doc for doc, score in sorted_fused]

def query_rag_system(user_question: str, top_k: int = 2) -> dict:
    # 1. Connect to ChromaDB
    chroma_client = chromadb.PersistentClient(path="chromadb_store")
    collection = chroma_client.get_collection(name="design_docs_live")
    all_documents = collection.get()["documents"]
    
    # 2. Dense Vector Search (Semantic)
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_vector = model.encode(user_question).tolist()
    vector_results = collection.query(query_embeddings=[query_vector], n_results=5)
    vector_top_docs = vector_results["documents"][0]
    
    # 3. Sparse Keyword Search (BM25 Lexical)
    tokenized_corpus = [doc.lower().split() for doc in all_documents]
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = user_question.lower().split()
    bm25_top_docs = bm25.get_top_n(tokenized_query, all_documents, n=5)
    
    # 4. Fuse using RRF
    fused_docs = reciprocal_rank_fusion(vector_top_docs, bm25_top_docs)
    best_contexts = fused_docs[:top_k]
    formatted_context = "\n---\n".join(best_contexts)
    
    # 5. Groq Answer Generation
    system_prompt = """
    You are an internal corporate assistant. 
    Answer the user's question strictly using the provided Context. 
    If the answer is not in the context, say 'I cannot find the answer in the provided documents.'
    Do not use outside knowledge.
    """
    user_prompt = f"Context:\n{formatted_context}\n\nQuestion: {user_question}"
    
    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0
    )
    
    return {
        "question": user_question,
        "answer": response.choices[0].message.content,
        "contexts": best_contexts
    }

if __name__ == "__main__":
    test_q = "What is the penalty for violating GDPR?"
    print("\n[Testing Hybrid Search Pipeline...]")
    res = query_rag_system(test_q)
    print("\nAnswer:", res["answer"])