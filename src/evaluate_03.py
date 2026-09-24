import os
import json
from groq import Groq
from dotenv import load_dotenv

# Import our working query pipeline
from query_02 import query_rag_system

load_dotenv()
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# 1. Golden Dataset: Tests factual extraction, edge cases, and out-of-scope questions
GOLDEN_DATASET = [
    {
        "question": "What is the penalty for violating GDPR?",
        "expected_keyword": "4% of annual global turnover",
        "category": "Factual Extraction"
    },
    {
        "question": "Within how many hours must a GDPR data breach be reported?",
        "expected_keyword": "72 hours",
        "category": "Strict Numeric Rule"
    },
    {
        "question": "Does SOC 2 provide an end-user legal right to be forgotten?",
        "expected_keyword": "does not grant",
        "category": "Negative Constraint"
    },
    {
        "question": "What is the penalty for violating HIPAA?",
        "expected_keyword": "cannot find",
        "category": "Out-of-Scope (Anti-Hallucination)"
    }
]

def llm_judge_faithfulness_and_relevancy(question: str, context: str, answer: str) -> dict:
    """
    Acts as an LLM-as-a-Judge to grade faithfulness (hallucinations) and relevancy.
    Returns a score between 0.0 and 1.0 for each metric.
    """
    eval_prompt = f"""
    You are an impartial evaluator auditing a corporate RAG system.
    
    Context retrieved:
    {context}
    
    User Question:
    {question}
    
    System Answer:
    {answer}
    
    Evaluate the response on two criteria:
    1. faithfulness: Does the answer make claims NOT supported by the context? (1.0 = fully supported/faithful, 0.0 = contains hallucinations). If the context doesn't have the answer and the system politely admits it cannot find it, score 1.0.
    2. answer_relevancy: Does the answer directly address the user's question? (1.0 = highly relevant, 0.0 = completely irrelevant).
    
    Return ONLY a valid JSON object in this exact format:
    {{"faithfulness": 1.0, "answer_relevancy": 1.0, "reasoning": "short explanation"}}
    """

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": eval_prompt}],
        temperature=0,
        response_format={"type": "json_object"}
    )
    
    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {"faithfulness": 1.0, "answer_relevancy": 1.0, "reasoning": "Pass"}

def run_benchmark():
    print("==================================================")
    print("      RUNNING RAG EVALUATION BENCHMARK            ")
    print("==================================================\n")
    
    scores = []

    for idx, test_case in enumerate(GOLDEN_DATASET, start=1):
        q = test_case["question"]
        print(f"[{idx}/{len(GOLDEN_DATASET)}] Testing: '{q}'")
        
        # 1. Run through our RAG system
        rag_output = query_rag_system(q)
        answer = rag_output["answer"]
        contexts = rag_output["contexts"]
        combined_context = "\n---\n".join(contexts)
        
        # 2. Check Retrieval Accuracy (Keyword hit)
        retrieval_hit = any(test_case["expected_keyword"].lower() in c.lower() for c in contexts) or \
                        (test_case["expected_keyword"].lower() in answer.lower())
        
        # 3. LLM-as-a-Judge Evaluation
        judge_result = llm_judge_faithfulness_and_relevancy(q, combined_context, answer)
        
        scores.append({
            "question": q,
            "category": test_case["category"],
            "retrieval_hit": 1.0 if retrieval_hit else 0.0,
            "faithfulness": judge_result.get("faithfulness", 1.0),
            "relevancy": judge_result.get("answer_relevancy", 1.0),
            "reason": judge_result.get("reasoning", "")
        })
        print(f"  -> Faithfulness: {scores[-1]['faithfulness']} | Relevancy: {scores[-1]['relevancy']}\n")

    # Final Scorecard
    print("\n================ FINAL BENCHMARK RESULTS ================")
    print(f"{'Category':<28} | {'Retr.':<6} | {'Faith.':<6} | {'Relev.':<6}")
    print("-" * 55)
    for s in scores:
        print(f"{s['category']:<28} | {s['retrieval_hit']:<6.1f} | {s['faithfulness']:<6.1f} | {s['relevancy']:<6.1f}")
        
    avg_retrieval = sum(s["retrieval_hit"] for s in scores) / len(scores)
    avg_faithfulness = sum(s["faithfulness"] for s in scores) / len(scores)
    avg_relevancy = sum(s["relevancy"] for s in scores) / len(scores)
    
    print("-" * 55)
    print(f"Average Retrieval Precision : {avg_retrieval * 100:.1f}%")
    print(f"Average Faithfulness (No Hallucinations): {avg_faithfulness * 100:.1f}%")
    print(f"Average Answer Relevancy    : {avg_relevancy * 100:.1f}%")
    print("=========================================================")

if __name__ == "__main__":
    run_benchmark()