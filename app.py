"""Streamlit UI — Singapore Travel Assistant."""
import streamlit as st
from agent import handle_message

st.set_page_config(page_title="Singapore Travel Assistant", page_icon="🌴")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "preferences" not in st.session_state:
    st.session_state.preferences = {}

with st.sidebar:
    st.header("Settings")
    show_sources = st.checkbox("Show KB sources", True)
    show_tools = st.checkbox("Show MCP tool output", True)
    st.markdown("---")
    st.caption("KB: 4 Singapore docs (FAISS)")
    st.caption("MCP: weather (Open-Meteo), currency (frankfurter.app)")

st.title("🌴 AI Travel Planning Assistant — Singapore")
st.caption("Ask about attractions, transport, food, itineraries, weather, or currency.")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m["role"] == "assistant" and show_sources and m.get("sources"):
            with st.expander("Sources"):
                for s in m["sources"]:
                    st.write(f"- {s}")

prompt = st.chat_input("e.g., Plan a 3-day Singapore trip for next week, adjust for weather")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            out = handle_message(prompt, st.session_state.messages, st.session_state.preferences)

        st.markdown(out.get("answer", "(no answer)"))

        if show_sources and out.get("sources"):
            with st.expander("Sources"):
                for s in out["sources"]:
                    st.write(f"- {s}")

        if show_tools and out.get("tool_data"):
            with st.expander("MCP tool output"):
                st.json(out["tool_data"])

    st.session_state.messages.append({
        "role": "assistant",
        "content": out.get("answer", ""),
        "sources": out.get("sources", []),
    })