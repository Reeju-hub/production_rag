import streamlit as st
import query_02 as dense_rag
import query_hybrid as hybrid_rag
from multi_agent_auditor import run_autonomous_audit

st.set_page_config(page_title="Enterprise AI Systems", page_icon="🛡️", layout="wide")

st.title("🛡️ Enterprise AI Operations Center")
st.caption("Built from scratch: Hybrid RAG & Autonomous Multi-Agent Workflows")

# UI Tabs create kar rahe hain
tab1, tab2 = st.tabs(["📚 RAG Knowledge Base", "🤖 Autonomous Invoice Auditor"])

with tab1:
    st.header("Corporate Compliance Search")
    search_mode = st.radio("Retrieval Architecture:", ("Hybrid (Dense + BM25)", "Dense Vector Only"))
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a compliance question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching database..."):
                output = hybrid_rag.query_rag_system(prompt) if "Hybrid" in search_mode else dense_rag.query_rag_system(prompt)
                st.markdown(output["answer"])
                with st.expander("🔍 Inspect Context"):
                    for i, ctx in enumerate(output["contexts"], 1): st.markdown(f"**Chunk {i}:**\n{ctx}")
                st.session_state.messages.append({"role": "assistant", "content": output["answer"]})

with tab2:
    st.header("Multi-Agent Financial Auditor")
    st.markdown("This system uses a 3-agent loop (Extractor -> Validator -> Reporter) with **Pydantic self-correction** to audit invoices against the RAG knowledge base.")
    
    invoice_input = st.text_area("Paste Raw Invoice Text here:", height=200, 
                                 value="INVOICE #9942\nFrom: Globex Tech Solutions\nAmount Due: 4500.00\nTax Applied: 35%")
    
    if st.button("Run Multi-Agent Audit"):
        with st.status("Initializing Agents...", expanded=True) as status:
            st.write("🕵️ Agent 1: Fetching RAG Context & Extracting Data...")
            st.write("⚖️ Agent 2: Validating against Pydantic Schema & Business Rules...")
            
            result = run_autonomous_audit(invoice_input)
            
            if result["status"] == "Success":
                st.write("📝 Agent 3: Generating final markdown report...")
                status.update(label="Audit Complete!", state="complete", expanded=False)
                
                st.subheader("Final Audit Report")
                st.markdown(result["report"])
                
                with st.expander("🛠️ View Agent 2 Raw Validated JSON"):
                    st.json(result["raw_data"])
            else:
                status.update(label="Audit Failed", state="error")
                st.error(result["reason"])