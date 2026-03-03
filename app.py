import streamlit as st
from agent import chat_stream_with_tracing
from config import get_config

# Validate configuration on app startup
try:
    get_config()
except ValueError as e:
    st.error(f"Configuration Error: {e}")
    st.stop()

st.set_page_config(
    page_title="BI Agent — Monday.com",
    page_icon="📊",
    layout="wide"
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 BI Agent")
    st.markdown("Your AI-powered business intelligence assistant, connected live to Monday.com.")
    st.markdown("---")

    tone = st.radio(
        "🎭 Response Style",
        options=["Straight Forward", "Informative"],
        index=0,
        help=(
            "**Straight Forward** — Direct answers, numbers first. Best for experienced users.\n\n"
            "**Informative** — Explains context and terms. Best for new users."
        ),
    )

    st.markdown("---")

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.session_state.current_tone = tone
        st.rerun()

    st.markdown("---")
    st.caption("🤖 Powered by [Groq](https://groq.com) · Llama 3.3 70B")
    st.caption("🔗 Data pulled live from [Monday.com](https://monday.com)")


# ── Session State ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_tone" not in st.session_state:
    st.session_state.current_tone = tone

# Reset LLM context (not chat display) when tone changes
if st.session_state.current_tone != tone:
    st.session_state.chat_history = []
    st.session_state.current_tone = tone


# ── Header ─────────────────────────────────────────────────────────────────────
st.title("Executive BI Agent")
st.markdown(
    "Ask any business question about your **Deals Pipeline** or **Work Orders** — "
    "the agent fetches live data from Monday.com and reasons through your question in real time."
)

if tone == "Informative":
    st.info("📖 **Informative mode** — Answers include context, explanations, and key takeaways.")
else:
    st.info("⚡ **Straight Forward mode** — Concise answers, numbers first, no fluff.")

st.markdown("---")


# ── Chat History Display ───────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("traces"):
            with st.expander("🔍 Agent Reasoning Trace", expanded=False):
                for trace in msg["traces"]:
                    st.text(trace)


# ── Chat Input ─────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask a question about your business data..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status = st.status("Thinking...", expanded=True)
        traces = []

        def on_trace(msg):
            traces.append(msg)
            status.write(msg)

        try:
            answer, new_history, followups = chat_stream_with_tracing(
                prompt,
                st.session_state.chat_history,
                on_trace,
                tone=tone,
            )
            status.update(label="✅ Done", state="complete", expanded=False)
            st.markdown(answer)
            st.session_state.chat_history = new_history
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "traces": traces,
            })

            # render follow-up suggestions
            if followups:
                st.markdown("**You might also ask:**")
                for fq in followups:
                    if st.button(fq, key=f"followup_{fq}"):
                        st.session_state.question_input = fq
                        st.rerun()

        except Exception as e:
            status.update(label="❌ Error", state="error", expanded=True)
            st.error(f"Something went wrong: {e}")
