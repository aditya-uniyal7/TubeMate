import hashlib
import html
import os
import re
import streamlit as st
from engine import Engine
from transcription import extract_youtube_id

st.set_page_config(
    page_title="TubeMate: ask a video anything",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400;500;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap');

:root {
  --bg: #ECEFF3;
  --surface: #FFFFFF;
  --soft: #F5F7FA;
  --ink: #151A21;
  --muted: #5B6573;
  --line: #D5DBE3;
  --accent: #D9351F;
  --on-accent: #FFFFFF;
  --ui: "Schibsted Grotesk", system-ui, sans-serif;
  --read: "Source Serif 4", Georgia, serif;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0E1217;
    --surface: #161B22;
    --soft: #1C222B;
    --ink: #E9EDF2;
    --muted: #9AA5B3;
    --line: #27303B;
    --accent: #FF6B55;
    --on-accent: #1A0B08;
  }
}

html, body, [class*="css"], .stApp {
  font-family: var(--ui);
  background: var(--bg) !important;
  color: var(--ink) !important;
}
#MainMenu, footer, [data-testid="stHeader"] {display: none !important;}
.block-container {
  max-width: 1180px !important;
  padding: 0 24px 64px !important;
  margin: 0 auto !important;
}

.tm-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 0;
}
.tm-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 20px;
  letter-spacing: -.01em;
  color: var(--ink);
}
.tm-logo i {
  display: inline-block;
  width: 30px;
  height: 21px;
  background: var(--accent);
  border-radius: 6px;
  position: relative;
}
.tm-logo i::after {
  content: "";
  position: absolute;
  left: 12px;
  top: 5.5px;
  border-left: 8px solid var(--on-accent);
  border-top: 5px solid transparent;
  border-bottom: 5px solid transparent;
}
.tm-nav a {color: var(--muted); text-decoration: none; font-size: 14px;}
.tm-nav a:hover {color: var(--ink);}

.tm-intro {padding: 4px 0 18px; max-width: 780px;}
.tm-intro h1 {
  font-size: clamp(32px, 5vw, 52px);
  line-height: 1.04;
  letter-spacing: -.03em;
  margin: 0 0 12px;
  font-weight: 700;
  color: var(--ink);
}
.tm-intro p {
  color: var(--muted);
  font-size: 18px;
  margin: 0;
  max-width: 56ch;
}

.st-key-input_wrap {max-width: 780px; margin-bottom: 24px !important;}
.st-key-paste_bar {
  background: var(--surface) !important;
  border: 1px solid var(--line) !important;
  border-radius: 14px !important;
  padding: 6px 8px !important;
}
.st-key-paste_bar [data-testid="stForm"] {border: 0 !important; padding: 0 !important;}
.st-key-paste_bar input {
  background: transparent !important;
  border: 0 !important;
  color: var(--ink) !important;
  font-size: 16px !important;
  box-shadow: none !important;
}
.st-key-upload_box {
  background: var(--surface) !important;
  border: 1px solid var(--line) !important;
  border-radius: 14px !important;
  padding: 12px 14px !important;
}

.st-key-video_card, .st-key-chat_card {
  background: var(--surface) !important;
  border: 1px solid var(--line) !important;
  border-radius: 16px !important;
  padding: 0 !important;
  overflow: hidden !important;
}
.st-key-video_card {padding-bottom: 16px !important;}
.st-key-video_card iframe, .st-key-video_card video {border-radius: 0 !important;}

.tm-meta {padding: 12px 18px 4px;}
.tm-meta h2 {margin: 0; font-size: 20px; letter-spacing: -.01em; color: var(--ink); font-weight: 700;}
.tm-meta p {margin: 4px 0 0; color: var(--muted); font-size: 14px;}
.tm-badge {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: var(--soft);
  border: 1px solid var(--line);
  color: var(--muted);
}

.st-key-chat_head {
  padding: 10px 16px !important;
  border-bottom: 1px solid var(--line) !important;
}
.tm-chead-title {margin: 0; font-size: 16px; font-weight: 700; color: var(--ink); line-height: 32px;}
.st-key-chat_actions button,
.st-key-chat_actions [data-testid="stDownloadButton"] button {
  white-space: nowrap !important;
  padding: 3px 9px !important;
  font-size: 12px !important;
}

.st-key-chat_log {padding: 14px 18px !important;}
.st-key-chat_log [data-testid="stMarkdownContainer"] p,
.st-key-chat_log [data-testid="stMarkdownContainer"] li {
  font-family: var(--read);
  font-size: 17px;
  line-height: 1.62;
  color: var(--ink);
}
.tm-hint {color: var(--muted); font-family: var(--read); font-size: 17px; margin: 0 0 8px;}
.tm-u-row {display: flex; justify-content: flex-end; margin: 10px 0;}
.tm-u {
  max-width: 85%;
  background: var(--ink);
  color: var(--surface);
  padding: 10px 14px;
  border-radius: 14px 14px 4px 14px;
  font-family: var(--ui);
  font-size: 15px;
  line-height: 1.5;
}

.st-key-chat_ask {
  border-top: 1px solid var(--line) !important;
  padding: 12px 14px 14px !important;
}
.st-key-chat_ask [data-testid="stForm"] {border: 0 !important; padding: 0 !important;}
.st-key-chat_ask input {
  background: var(--soft) !important;
  border: 1px solid var(--line) !important;
  border-radius: 10px !important;
  color: var(--ink) !important;
}
.st-key-chat_ask input:focus {border-color: var(--accent) !important;}

button[kind="primary"], button[kind="primaryFormSubmit"] {
  background: var(--accent) !important;
  color: var(--on-accent) !important;
  border: 0 !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
}
button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {filter: brightness(.94);}

button[kind="secondary"], [data-testid="stDownloadButton"] button {
  background: transparent !important;
  border: 1px solid var(--line) !important;
  border-radius: 8px !important;
  color: var(--muted) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  padding: 4px 11px !important;
  min-height: 32px !important;
}
button[kind="secondary"]:hover, [data-testid="stDownloadButton"] button:hover {
  color: var(--ink) !important;
  border-color: var(--accent) !important;
}
.st-key-sugg_row button[kind="secondary"] {
  background: var(--soft) !important;
  border-radius: 999px !important;
}

.tm-how {border-top: 1px solid var(--line); padding: 40px 0 36px; margin-top: 32px;}
.tm-how h2 {margin: 0 0 20px; font-size: 22px; letter-spacing: -.02em; color: var(--ink);}
.tm-steps {
  list-style: none; counter-reset: s; margin: 0; padding: 0;
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 24px;
}
.tm-steps li {counter-increment: s;}
.tm-steps li::before {
  content: counter(s); display: grid; place-items: center;
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--ink); color: var(--surface);
  font-weight: 700; font-size: 14px; margin-bottom: 10px;
}
.tm-steps b {display: block; margin-bottom: 2px; color: var(--ink);}
.tm-steps span {color: var(--muted); font-size: 15px;}
.tm-foot {color: var(--muted); font-size: 14px; margin: 0;}
@media (max-width: 900px) {.tm-steps {grid-template-columns: 1fr;}}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_url_engine(youtube_url: str) -> Engine:
    eng = Engine(youtube_url)
    if not eng.process_transcription():
        raise RuntimeError(eng.error or "Transcript unavailable")
    return eng


@st.cache_resource
def initialize_upload_engine(file_hash: str, filename: str, _file_bytes: bytes) -> Engine:
    eng = Engine(filename, file_bytes=_file_bytes, filename=filename)
    if not eng.process_transcription():
        raise RuntimeError(eng.error or "Transcript unavailable")
    return eng


st.markdown("""
<nav class="tm-nav" aria-label="Main">
  <div class="tm-logo"><i aria-hidden="true"></i>TubeMate</div>
  <a href="#how">How it works</a>
</nav>
<div class="tm-intro">
  <h1>Ask a YouTube video anything.</h1>
  <p>Paste a YouTube link or upload a recording. TubeMate reads or transcribes it with Whisper and answers your questions in English.</p>
</div>
""", unsafe_allow_html=True)

with st.container(key="input_wrap"):
    mode = st.radio(
        "Source mode",
        ["YouTube Link", "Upload File (.mp4 / .mp3 / .vtt)"],
        horizontal=True,
        label_visibility="collapsed",
    )

    yt_id = None
    clean_url = ""
    uploaded_file = None

    if mode == "YouTube Link":
        with st.container(key="paste_bar", border=True):
            with st.form("load_video_form", border=False):
                c_in, c_btn = st.columns([5, 1.3], gap="small", vertical_alignment="center")
                with c_in:
                    url_input = st.text_input(
                        "YouTube link",
                        value=st.session_state.get("url_value", ""),
                        placeholder="Paste a YouTube link",
                        label_visibility="collapsed",
                    )
                with c_btn:
                    submitted_url = st.form_submit_button("Load video", type="primary", use_container_width=True)
        if submitted_url:
            st.session_state.url_value = url_input.strip()
        clean_url = st.session_state.get("url_value", "").strip()
    else:
        with st.container(key="upload_box", border=True):
            uploaded_file = st.file_uploader(
                "Upload recording or transcript",
                type=["mp4", "m4a", "mp3", "wav", "webm", "ogg", "flac", "vtt", "srt", "txt"],
                label_visibility="collapsed",
            )

engine = None
source_key = None
upload_bytes = None
upload_ext = ""

if mode == "YouTube Link" and clean_url:
    yt_id = extract_youtube_id(clean_url)
    if not yt_id:
        st.warning("Please enter a valid YouTube link.")
    else:
        source_key = f"yt::{yt_id}"
        try:
            with st.spinner("Reading transcript (with Whisper fallback if needed)..."):
                engine = initialize_url_engine(f"https://www.youtube.com/watch?v={yt_id}")
        except Exception as e:
            st.error(f"Could not load transcript: {e}")

elif mode != "YouTube Link" and uploaded_file is not None:
    upload_bytes = uploaded_file.getvalue()
    file_hash = hashlib.sha256(upload_bytes).hexdigest()
    upload_ext = os.path.splitext(uploaded_file.name)[1].lower()
    source_key = f"upload::{file_hash}::{uploaded_file.name}"
    spinner_msg = (
        f"Parsing transcript from {uploaded_file.name}..."
        if upload_ext in {".vtt", ".srt", ".txt"}
        else f"Transcribing {uploaded_file.name} with Whisper..."
    )
    try:
        with st.spinner(spinner_msg):
            engine = initialize_upload_engine(file_hash, uploaded_file.name, upload_bytes)
    except Exception as e:
        st.error(f"Could not process file: {e}")

if engine is not None and source_key:
    if st.session_state.get("current_source") != source_key:
        st.session_state.current_source = source_key
        st.session_state.chat_history = []
        st.session_state.quiz_mode = False
        st.session_state.quiz_checked = False

    def submit_question(q_text: str):
        q_text = q_text.strip()
        if not q_text:
            return
        st.session_state.chat_history.append({"role": "user", "content": q_text})
        try:
            with st.spinner("Searching transcript..."):
                ans = engine.query(q_text)
        except Exception as e:
            ans = f"Something went wrong: {e}"
        st.session_state.chat_history.append({"role": "assistant", "content": ans})

    title = engine.video_info.get("title", "Recording")
    author = engine.video_info.get("author", "Media")
    source_badge = {
        "youtube": "YouTube captions",
        "whisper": "Whisper audio",
        "transcript_file": "Transcript file",
    }.get(engine.transcript_source, "Transcript")

    col_left, col_right = st.columns([1.15, 1], gap="medium")

    with col_left:
        with st.container(key="video_card", border=True):
            if mode == "YouTube Link":
                st.video(f"https://www.youtube.com/watch?v={yt_id}")
            elif upload_ext in {".mp4", ".webm"}:
                st.video(upload_bytes)
            elif upload_ext in {".m4a", ".mp3", ".wav", ".ogg", ".flac"}:
                st.audio(upload_bytes)
            else:
                st.info(f"Transcript loaded from {uploaded_file.name} ({len(engine.transcription or ''):,} characters).")

            st.markdown(
                f'<div class="tm-meta"><h2>{html.escape(title)}</h2>'
                f'<p>{html.escape(author)}<span class="tm-badge">{source_badge}</span></p></div>',
                unsafe_allow_html=True,
            )

    with col_right:
        with st.container(key="chat_card", border=True):
            with st.container(key="chat_head"):
                h_title, h_actions = st.columns([0.8, 3.2], vertical_alignment="center")
                with h_title:
                    panel_title = "Quiz" if st.session_state.get("quiz_mode") else "Chat"
                    st.markdown(f'<p class="tm-chead-title">{panel_title}</p>', unsafe_allow_html=True)
                with h_actions:
                    with st.container(key="chat_actions", horizontal=True, wrap=False, horizontal_alignment="right", gap="small"):
                        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", title)[:30].strip("-") or "video"
                        quiz_label = "Back to chat" if st.session_state.get("quiz_mode") else "Quiz"
                        if st.button(quiz_label, key="toggle_quiz_btn"):
                            st.session_state.quiz_mode = not st.session_state.get("quiz_mode", False)
                            st.rerun()
                        st.download_button(
                            "Download Anki",
                            data=lambda: engine.get_anki_txt(),
                            file_name=f"tubemate-anki-{slug}.txt",
                            mime="text/plain",
                            on_click="ignore",
                        )
                        if st.button("Clear"):
                            st.session_state.chat_history = []
                            st.session_state.quiz_checked = False
                            st.rerun()

            if st.session_state.get("quiz_mode"):
                with st.container(key="chat_log", height=480, border=False):
                    try:
                        with st.spinner("Generating quiz from transcript..."):
                            quiz_items = engine.get_quiz()
                    except Exception as e:
                        quiz_items = []
                        st.error(f"Could not generate quiz: {e}")

                    if not quiz_items:
                        st.info("No quiz questions could be generated from this transcript.")
                    else:
                        for q_idx, item in enumerate(quiz_items):
                            st.markdown(f"**Q{q_idx + 1}. {item['question']}**")
                            st.radio(
                                f"Question {q_idx + 1}",
                                item["options"],
                                key=f"quiz_q_{source_key}_{q_idx}",
                                index=None,
                                label_visibility="collapsed",
                            )
                            if st.session_state.get("quiz_checked"):
                                chosen = st.session_state.get(f"quiz_q_{source_key}_{q_idx}")
                                correct_opt = item["options"][item["answer_index"]]
                                if chosen == correct_opt:
                                    st.success(f"Correct! {item['explanation']}")
                                else:
                                    st.error(f"Answer: {correct_opt}. {item['explanation']}")
                            st.write("")

                with st.container(key="chat_ask"):
                    q_b1, q_b2 = st.columns([2, 1], gap="small")
                    with q_b1:
                        if st.button("Check answers", type="primary", use_container_width=True, disabled=not quiz_items):
                            st.session_state.quiz_checked = True
                            st.rerun()
                    with q_b2:
                        if st.button("New quiz", use_container_width=True):
                            engine.get_quiz(force_refresh=True)
                            st.session_state.quiz_checked = False
                            for q_idx in range(10):
                                st.session_state.pop(f"quiz_q_{source_key}_{q_idx}", None)
                            st.rerun()
                    if st.session_state.get("quiz_checked") and quiz_items:
                        score = sum(
                            1
                            for q_idx, item in enumerate(quiz_items)
                            if st.session_state.get(f"quiz_q_{source_key}_{q_idx}") == item["options"][item["answer_index"]]
                        )
                        st.markdown(f"**Score: {score} / {len(quiz_items)}**")
            else:
                with st.container(key="chat_log", height=420, border=False, autoscroll=True):
                    st.markdown('<p class="tm-hint">Transcript is ready. Ask anything about this recording.</p>', unsafe_allow_html=True)
                    for msg in st.session_state.chat_history:
                        if msg["role"] == "user":
                            st.markdown(
                                f'<div class="tm-u-row"><div class="tm-u">{html.escape(msg["content"])}</div></div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(msg["content"])

                with st.container(key="chat_ask"):
                    with st.container(key="sugg_row", horizontal=True, gap="small"):
                        for idx, suggestion in enumerate(["Summarize in 5 bullets", "What is the main advice?", "Key takeaways"]):
                            if st.button(suggestion, key=f"sugg_{idx}"):
                                submit_question(suggestion)
                                st.rerun()

                    with st.form("ask_form", clear_on_submit=True, border=False):
                        q_col, send_col = st.columns([4.5, 1.2], gap="small", vertical_alignment="center")
                        with q_col:
                            question = st.text_input(
                                "Ask about this video",
                                placeholder="Ask about this video",
                                label_visibility="collapsed",
                            )
                        with send_col:
                            sent = st.form_submit_button("Send", type="primary", use_container_width=True)
                    if sent and question.strip():
                        submit_question(question)
                        st.rerun()

st.markdown("""
<section class="tm-how" id="how">
  <h2>How it works</h2>
  <ol class="steps tm-steps">
    <li><b>Paste a link or upload</b><span>Any YouTube video, recording file (.mp4/.mp3), or .vtt/.txt transcript.</span></li>
    <li><b>TubeMate reads it</b><span>It uses YouTube captions when available and falls back to Whisper audio transcription when they aren't.</span></li>
    <li><b>Ask, quiz & export</b><span>Ask questions in English, test yourself with a 5-question quiz, and download Anki flashcards (.txt).</span></li>
  </ol>
</section>
<p class="tm-foot">Answers come only from the transcript. If something isn't in the recording, TubeMate says so.</p>
""", unsafe_allow_html=True)
