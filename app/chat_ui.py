"""'Ask' tab: chat about the stored statement. AI is opt-in per session; without it (or without an API key) rule-based answers are used."""
import streamlit as st

from app import chatbot
from app.chat_tools import ChatTools

MAX_AI_MESSAGES = 30          # per browser session: caps API spend on a public demo
EXAMPLES = ["How much did I spend on Groceries last month?", "What are my subscriptions?", "Any unusual transactions?",
            "What will I spend next month?", "What is my savings rate?", "How is my data stored?"]


def render(full):
    ai_available = chatbot.make_client() is not None
    use_ai = False
    if ai_available:
        use_ai = st.checkbox("Use the AI assistant (Gemini)", value=False, key="chat_use_ai",
                             help="Off: answers come from built-in rules. On: Gemini chooses which summaries to look up.")
        if use_ai:
            st.caption("With this on, the summary numbers and merchant names needed to answer each question are sent to Google's Gemini API. "
                       "Raw transaction rows are not sent, but on the free tier Google may use what it receives to improve its products, "
                       "so avoid this with a real statement. Turn it off to keep everything on this server.")
    else:
        st.caption("Answers come from built-in rules (no AI key configured), so nothing leaves this app. "
                   "Set `GEMINI_API_KEY` (free from Google AI Studio) to enable the AI assistant.")

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
            out = chatbot.answer(q, [{"role": m["role"], "content": m["content"]} for m in hist], ChatTools(full),
                                 use_ai=use_ai and not capped)
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
