import streamlit as st
import query_02 as dense_rag
import query_hybrid as hybrid_rag

st.set_page_config(page_title="Enterprise Compliance RAG", page_icon="🛡️", layout="wide")

st.title("🛡️ Enterprise Compliance RAG Knowledge Base")
st.caption("Built from scratch: Token-aware chunking, Dense & Sparse Hybrid Search, and Anti-Hallucination guardrails.")

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("⚙️ Retrieval Architecture")
    search_mode = st.radio(
        "Select Retrieval Strategy:",
        ("Hybrid (Dense Vector + BM25 Lexical)", "Dense Vector Only (ChromaDB)"),
        help="Compare standard semantic retrieval with fused hybrid retrieval."
    )
    st.divider()
    st.markdown("""
    **Architecture Overview:**
    - **Dense Model:** `all-MiniLM-L6-v2`
    - **Lexical Index:** BM25Okapi
    - **Fusion:** Reciprocal Rank Fusion (RRF)
    - **LLM Inference:** Groq (`gpt-oss-20b`)
    """)

# --- CHAT HISTORY ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- CHAT INPUT ---
if prompt := st.chat_input("E.g., What are the incident response deadlines under GDPR vs SOC 2?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner(f"Executing retrieval via {search_mode}..."):
            try:
                # Route based on selected mode
                if "Hybrid" in search_mode:
                    output = hybrid_rag.query_rag_system(prompt)
                else:
                    output = dense_rag.query_rag_system(prompt)

                st.markdown(output["answer"])

                # Transparent chunk inspect for recruiters
                with st.expander(f"🔍 Inspect Retrieved Context ({search_mode})"):
                    for i, ctx in enumerate(output["contexts"], 1):
                        st.markdown(f"**Retrieved Chunk {i}:**\n{ctx}")
                        st.divider()

                st.session_state.messages.append({"role": "assistant", "content": output["answer"]})

            except Exception as e:
                st.error(f"Error during retrieval: {str(e)}")