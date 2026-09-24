import os
import json
from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import List, Optional
from groq import Groq
from dotenv import load_dotenv

# Tumhara existing Hybrid RAG import kar rahe hain
from query_hybrid import query_rag_system

load_dotenv()
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ==========================================
# STEP 1: Strict Pydantic Schema (The Contract)
# ==========================================
class InvoiceAuditSchema(BaseModel):
    vendor_name: str = Field(description="Name of the company sending the invoice")
    invoice_amount: float = Field(description="Total monetary value listed on the invoice")
    detected_tax_rate: float = Field(description="Tax percentage applied")
    flagged_anomalies: List[str] = Field(default_factory=list, description="List of suspicious items or policy violations")

    @field_validator('invoice_amount')
    @classmethod
    def must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Invoice amount must be strictly greater than zero.")
        return v

# ==========================================
# STEP 2: Agent 1 - Extractor (LLM + JSON Mode)
# ==========================================
def extractor_agent(invoice_text: str, rag_context: str, error_feedback: Optional[str] = None) -> InvoiceAuditSchema:
    system_prompt = (
        "You are an expert financial auditor. Extract data strictly following the JSON schema provided. "
        f"\nCorporate Policy Context: {rag_context}\n"
        "Return ONLY valid JSON matching this schema: "
        "{'vendor_name': str, 'invoice_amount': float, 'detected_tax_rate': float, 'flagged_anomalies': [str]}"
    )
    
    if error_feedback:
        system_prompt += f"\nCRITICAL ERROR IN PREVIOUS ATTEMPT. FIX THIS: {error_feedback}"

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b", # Groq ka best JSON model
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": invoice_text}
        ],
        temperature=0,
        response_format={"type": "json_object"}
    )
    
    raw_json = response.choices[0].message.content
    
    # Pydantic validation (agar LLM ne galat JSON diya toh yahan fail hoga aur Validator isko pakdega)
    return InvoiceAuditSchema.model_validate_json(raw_json)

# ==========================================
# STEP 3: Agent 3 - Compliance Reporter (Markdown)
# ==========================================
def reporter_agent(validated_data: InvoiceAuditSchema) -> str:
    prompt = f"Convert this structured financial audit JSON data into a short, professional markdown compliance report: {validated_data.model_dump_json()}"
    
    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "system", "content": "You are a professional report generator."}, {"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content

# ==========================================
# STEP 4: Agent 2 - Orchestrator / Validator (State Machine)
# ==========================================
def run_autonomous_audit(invoice_text: str) -> dict:
    max_retries = 3
    error_log = None
    
    # Pehle apna existing Hybrid RAG call karte hain taaki rules fetch hon
    print("[Fetching Corporate Rules via Hybrid RAG...]")
    rag_response = query_rag_system("What are our vendor payment and tax compliance rules?")
    corporate_context = "\n".join(rag_response["contexts"])

    for attempt in range(1, max_retries + 1):
        try:
            print(f"[Agent 1] Extraction Attempt {attempt}...")
            # Agent 1 run karega aur Pydantic schema check karega
            extracted_data = extractor_agent(invoice_text, corporate_context, error_feedback=error_log)
            
            print("[Agent 2] Validating Business Logic...")
            # Custom Business Logic (Math check)
            if extracted_data.detected_tax_rate > 30.0:
                extracted_data.flagged_anomalies.append(f"Tax rate {extracted_data.detected_tax_rate}% exceeds global 30% limit.")
            
            print("[Agent 3] Generating Final Markdown Report...")
            # Agent 3 final report banayega
            final_report = reporter_agent(extracted_data)
            
            return {
                "status": "Success",
                "raw_data": extracted_data.model_dump(),
                "report": final_report
            }
            
        except ValidationError as e:
            print(f"  -> Pydantic Schema Error: {str(e)}")
            error_log = f"Schema validation failed: {str(e)}. Ensure data types match perfectly."
        except Exception as e:
            print(f"  -> Unexpected Error: {str(e)}")
            error_log = str(e)
            
    return {"status": "Failed", "reason": "Max retries reached. Agent failed to self-correct."}

# Test the system directly
if __name__ == "__main__":
    dummy_invoice = """
    INVOICE #9942
    From: Globex Tech Solutions
    Amount Due: -500.00
    Tax Applied: 35%
    Notes: Late fee applied.
    """
    result = run_autonomous_audit(dummy_invoice)
    print("\n" + result.get("report", result.get("reason")))