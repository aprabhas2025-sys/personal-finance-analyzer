"""'Ask' tab: chat about the stored statement. A configured Gemini key enables AI answers; otherwise built-in rules are used."""
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
    api_key = chatbot.resolve_api_key(secrets)
    client_error = None
    try:
        client = chatbot.make_client(api_key) if api_key else None
    except Exception as error:
        client = None
        client_error = chatbot._ai_error_hint(error)
    ai_available = client is not None
    use_ai = False
    if ai_available:
        use_ai = st.checkbox("Use the AI assistant (Gemini)", value=True, key="chat_use_ai",
                             help="Gemini uses read-only summaries to answer questions about your statement.")
        if use_ai:
            st.caption("The summary numbers and merchant names needed to answer are sent to Google's Gemini API. "
                       "Raw transaction rows are not sent. On the free tier Google may use submitted content to improve its products, "
                       "so use AI mode with sample data rather than a real statement.")
    elif client_error:
        st.warning(f"Gemini is configured but could not start: {client_error}")
    else:
        st.caption("Answers are using built-in rules because no Gemini key was found. Add `GEMINI_API_KEY` to the project `.env`, "
                   "`.streamlit/secrets.toml`, or the environment, then rerun the app. If using a Windows environment variable, restart Streamlit from a newly opened CMD window.")

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
        meta = ("AI" if out["source"] == "ai" else "Rules") + (f" · looked up: {', '.join(out['tool_calls'])}" if out["tool_calls"] else "")
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
