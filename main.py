import re
import streamlit as st
from engine import Engine

st.set_page_config(page_title="Video QA", page_icon="🎬", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"], .stApp {font-family: 'Inter', sans-serif;}
.stApp {
    background: radial-gradient(1200px 600px at 10% -10%, #2a1f5c 0%, transparent 60%),
                radial-gradient(1000px 500px at 100% 0%, #0f3a4a 0%, transparent 55%),
                #0b0e16;
}
#MainMenu, footer, header {visibility: hidden;}
.block-container {padding-top: 1.5rem; max-width: 1250px;}

/* hero */
.hero {text-align: center; padding: 1.5rem 0 1rem;}
.hero h1 {
    font-size: 2.6rem; font-weight: 700; margin: 0;
    background: linear-gradient(90deg, #a78bfa, #38bdf8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero p {color: #9aa4b8; margin-top: .4rem; font-size: 1.05rem;}

/* cards */
.card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px; padding: 1.1rem 1.3rem;
    backdrop-filter: blur(8px);
}
.card-title {font-weight: 600; color: #c9d1e3; margin-bottom: .6rem;}

/* chat bubbles */
[data-testid="stChatMessage"] {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px; padding: .8rem 1rem; margin-bottom: .6rem;
}

/* inputs */
.stTextInput input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(167,139,250,0.4) !important;
    border-radius: 12px !important; color: #fff !important;
    padding: .75rem 1rem !important;
}
.stTextInput input:focus {border-color: #a78bfa !important;}
[data-testid="stChatInput"] {border-radius: 14px;}
.stButton button {
    border-radius: 12px; border: none; color: white; font-weight: 600;
    background: linear-gradient(90deg, #7c5cff, #38bdf8);
}
iframe {border-radius: 14px;}
</style>
""", unsafe_allow_html=True)

def extract_video_id(url: str):
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None

@st.cache_resource
def initialize_engine(vid):
    engine = Engine(vid)
    if not engine.process_transcription():
        raise RuntimeError("Transcript unavailable")
    return engine

# hero
st.markdown("""
<div class="hero">
  <h1>🎬 Video Q&A</h1>
  <p>Paste a YouTube link and ask anything about it.</p>
</div>
""", unsafe_allow_html=True)

_, mid, _ = st.columns([1, 2.2, 1])
with mid:
    url = st.text_input("link", placeholder="Paste YouTube link here...",
                        label_visibility="collapsed")

video_id = extract_video_id(url) if url else None
if not video_id:
    st.stop()

if st.session_state.get("current_video") != video_id:
    st.session_state.current_video = video_id
    st.session_state.chat_history = [
        {"role": "assistant", "content": "Transcript is ready. Ask me anything about this video."}
    ]

try:
    with st.spinner("Analyzing transcript and creating embeddings..."):
        engine = initialize_engine(video_id)
except Exception as e:
    st.error(f"Could not load transcript: {e}")
    st.stop()

st.write("")
left, right = st.columns([1, 1.2], gap="large")

with left:
    st.markdown('<div class="card"><div class="card-title">▶ Video</div></div>',
                unsafe_allow_html=True)
    st.video(f"https://www.youtube.com/watch?v={video_id}")
    if st.button("🗑 Clear chat", use_container_width=True):
        st.session_state.pop("current_video", None)
        st.rerun()

with right:
    st.markdown('<div class="card"><div class="card-title">💬 Chat</div></div>',
                unsafe_allow_html=True)
    box = st.container(height=470, border=False)
    with box:
        for c in st.session_state.chat_history:
            with st.chat_message(c["role"], avatar="🧑‍💻" if c["role"] == "user" else "✨"):
                st.markdown(c["content"])

    if q := st.chat_input("Ask a question about the video..."):
        st.session_state.chat_history.append({"role": "user", "content": q})
        try:
            with st.spinner("Searching context..."):
                ans = engine.query(q)
        except Exception as e:
            ans = f"Something went wrong: {e}"
        st.session_state.chat_history.append({"role": "assistant", "content": ans})
        st.rerun()