"""'Ask' tab: chat about the stored statement. Configured Groq and/or Gemini keys enable AI answers; otherwise built-in rules are used."""
import streamlit as st

from app import chatbot
from app.chat_tools import ChatTools

MAX_AI_MESSAGES = 30          # per browser session: caps API spend on a public demo
EXAMPLES = ["How much did I spend on Groceries last month?", "What are my subscriptions?", "Any unusual transactions?",
            "What will I spend next month?", "What is my savings rate?", "Am I over budget?", "How is my data stored?"]


def render(full, budgets=None):
    try:
        secrets = st.secrets
    except Exception:
        secrets = None

    client = chatbot.make_multi_client(secrets)
    ai_available = client.is_available
    use_ai = False

    if ai_available:
        if client.groq_client and client.gemini_client:
            label = "Use AI assistant (Groq primary, Gemini backup)"
            desc = f"Primary: Groq ({client.groq_model}) · Backup: Gemini ({client.gemini_model})."
        elif client.groq_client:
            label = f"Use AI assistant (Groq: {client.groq_model})"
            desc = f"Connected to Groq ({client.groq_model})."
        else:
            label = f"Use AI assistant (Gemini: {client.gemini_model})"
            desc = f"Connected to Google Gemini ({client.gemini_model})."

        use_ai = st.checkbox(label, value=True, key="chat_use_ai",
                             help="The AI assistant uses read-only summaries to answer questions about your statement.")
        if use_ai:
            st.caption(f"{desc} Summary numbers and merchant names needed to answer are sent to the AI API. "
                       "Raw transaction rows are never sent.")
    else:
        st.caption("Answers are using built-in rules because neither Groq nor Gemini API key was found. "
                   "Add `GROQ_API_KEY` (and optionally `GEMINI_API_KEY` as backup) to `.env`, "
                   "`.streamlit/secrets.toml`, or the environment, then rerun the app.")

    hist = st.session_state.setdefault("chat", [])
    n_ai = st.session_state.setdefault("chat_ai_count", 0)
    if not hist:
        st.markdown("**Try:** " + " · ".join(f"*{e}*" for e in EXAMPLES))
    for m in hist:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m.get("meta"):
                st.caption(m["meta"])

    q = st.chat_input("Ask about your spending or how the app works")
    if q:
        capped = use_ai and n_ai >= MAX_AI_MESSAGES
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"), st.spinner("Thinking…"):
            out = chatbot.answer(q, [{"role": m["role"], "content": m["content"]} for m in hist], ChatTools(full, budgets=budgets),
                                 use_ai=use_ai and not capped, client=client)
        source_label = "AI"
        if out["source"] == "ai" and out.get("provider"):
            source_label += f" ({out['provider'].capitalize()})"
        meta = (source_label if out["source"] == "ai" else "Rules") + (f" · looked up: {', '.join(out['tool_calls'])}" if out["tool_calls"] else "")
        if capped:
            meta += f" · AI limit of {MAX_AI_MESSAGES} messages per session reached"
        if out.get("note"):
            meta += f" · {out['note']}"
        if out["source"] == "ai":
            st.session_state["chat_ai_count"] = n_ai + 1
        hist += [{"role": "user", "content": q}, {"role": "assistant", "content": out["text"], "meta": meta}]
        del hist[:-40]
        st.rerun()
    if hist and st.button("Clear chat"):
        st.session_state["chat"] = []
        st.rerun()
