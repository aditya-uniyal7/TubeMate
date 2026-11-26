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

.tm-tl {padding: 10px 18px 4px;}
.tm-tl h3 {margin: 0; font-size: 14px; font-weight: 500; color: var(--muted);}
.tm-track {position: relative; height: 8px; border-radius: 4px; background: var(--line); margin: 20px 0 8px;}
.tm-fill {position: absolute; left: 0; top: 0; bottom: 0; background: var(--muted); border-radius: 4px;}
.tm-head {position: absolute; top: -5px; width: 3px; height: 18px; margin-left: -1.5px; background: var(--ink); border-radius: 2px;}
.tm-pin {
  position: absolute; top: -6px; width: 18px; height: 18px; margin-left: -9px;
  border-radius: 50%; background: var(--surface); border: 3px solid var(--accent);
}
.tm-pin.active {background: var(--accent);}
.tm-times {display: flex; justify-content: space-between; font-size: 12px; color: var(--muted); font-variant-numeric: tabular-nums;}
.st-key-tl_pills {padding: 6px 18px 0 !important;}

.st-key-chat_head {
  padding: 10px 16px !important;
  border-bottom: 1px solid var(--line) !important;
}
.tm-chead-title {margin: 0; font-size: 16px; font-weight: 700; color: var(--ink); line-height: 32px;}
.st-key-chat_actions button,
.st-key-chat_actions [data-testid="stDownloadButton"] button {
  white-space: nowrap !important;
  padding: 3px 7px !important;
  font-size: 11.5px !important;
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
.tm-from {font-size: 13px; color: var(--muted); font-family: var(--ui); margin-right: 4px; line-height: 28px;}

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
.st-key-sugg_row button[kind="secondary"],
[class*="st-key-ts_row_"] button[kind="secondary"],
.st-key-tl_pills button[kind="secondary"] {
  background: var(--soft) !important;
  border-radius: 999px !important;
  font-variant-numeric: tabular-nums;
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


def fmt_time(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hrs, rem = divmod(seconds, 3600)
    mins, secs = divmod(rem, 60)
    return f"{hrs}:{mins:02d}:{secs:02d}" if hrs else f"{mins}:{secs:02d}"


def format_chat_markdown(title: str, source_label: str, history: list[dict]) -> str:
    lines = [f"# TubeMate Chat — {title}", f"Source: {source_label}", ""]
    for msg in history:
        speaker = "You" if msg["role"] == "user" else "TubeMate"
        lines.extend([f"## {speaker}", msg["content"]])
        if msg.get("moments"):
            lines.append(f"\n_Moments: {', '.join(fmt_time(t) for t in msg['moments'])}_")
        lines.append("")
    return "\n".join(lines)


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
  <p>Paste a YouTube link or upload a recording. TubeMate reads or transcribes it with Whisper and answers with the moments it came from.</p>
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
source_label = ""
upload_bytes = None
upload_ext = ""

if mode == "YouTube Link" and clean_url:
    yt_id = extract_youtube_id(clean_url)
    if not yt_id:
        st.warning("Please enter a valid YouTube link.")
    else:
        source_key = f"yt::{yt_id}"
        source_label = f"https://www.youtube.com/watch?v={yt_id}"
        try:
            with st.spinner("Reading transcript (with Whisper fallback if needed) and indexing moments..."):
                engine = initialize_url_engine(source_label)
        except Exception as e:
            st.error(f"Could not load transcript: {e}")

elif mode != "YouTube Link" and uploaded_file is not None:
    upload_bytes = uploaded_file.getvalue()
    file_hash = hashlib.sha256(upload_bytes).hexdigest()
    upload_ext = os.path.splitext(uploaded_file.name)[1].lower()
    source_key = f"upload::{file_hash}::{uploaded_file.name}"
    source_label = uploaded_file.name
    spinner_msg = (
        f"Parsing transcript from {uploaded_file.name} and indexing moments..."
        if upload_ext in {".vtt", ".srt", ".txt"}
        else f"Transcribing {uploaded_file.name} with Whisper and indexing moments..."
    )
    try:
        with st.spinner(spinner_msg):
            engine = initialize_upload_engine(file_hash, uploaded_file.name, upload_bytes)
    except Exception as e:
        st.error(f"Could not process file: {e}")

if engine is not None and source_key:
    if st.session_state.get("current_source") != source_key:
        st.session_state.current_source = source_key
        st.session_state.seek_time = 0
        st.session_state.chat_history = []
        st.session_state.quiz_mode = False
        st.session_state.quiz_checked = False

    def submit_question(q_text: str):
        q_text = q_text.strip()
        if not q_text:
            return
        st.session_state.chat_history.append({"role": "user", "content": q_text})
        try:
            with st.spinner("Searching transcript moments..."):
                ans, moments = engine.query_with_moments(q_text)
        except Exception as e:
            ans, moments = f"Something went wrong: {e}", []
        st.session_state.chat_history.append({"role": "assistant", "content": ans, "moments": moments})
        if moments:
            st.session_state.seek_time = moments[0]

    all_moments = sorted({t for msg in st.session_state.chat_history for t in msg.get("moments", [])})
    seek_time = st.session_state.get("seek_time", 0)
    total_dur = max(engine.total_duration, max(all_moments, default=0), 1)
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
                st.video(f"https://www.youtube.com/watch?v={yt_id}", start_time=seek_time)
            elif upload_ext in {".mp4", ".webm"}:
                st.video(upload_bytes, start_time=seek_time)
            elif upload_ext in {".m4a", ".mp3", ".wav", ".ogg", ".flac"}:
                st.audio(upload_bytes, start_time=seek_time)
            else:
                st.info(f"Transcript loaded from {uploaded_file.name} ({len(engine.transcription or ''):,} characters).")

            dur_label = fmt_time(engine.total_duration) if engine.total_duration else "Unknown"
            st.markdown(
                f'<div class="tm-meta"><h2>{html.escape(title)}</h2>'
                f'<p>{html.escape(author)} &middot; {dur_label}<span class="tm-badge">{source_badge}</span></p></div>',
                unsafe_allow_html=True,
            )

            pct = min(100.0, (seek_time / total_dur) * 100.0)
            pins_html = "".join(
                f'<span class="tm-pin{" active" if t == seek_time else ""}" style="left:{min(100.0, (t / total_dur) * 100.0):.2f}%" title="{fmt_time(t)}"></span>'
                for t in all_moments
            )
            tl_heading = (
                "Moments used in answers. Select one to jump there."
                if all_moments
                else "Ask a question to highlight transcript moments."
            )
            st.markdown(
                f'<div class="tm-tl">'
                f'<h3>{tl_heading}</h3>'
                f'<div class="tm-track">'
                f'<div class="tm-fill" style="width:{pct:.2f}%"></div>'
                f'{pins_html}'
                f'<div class="tm-head" style="left:{pct:.2f}%"></div>'
                f'</div>'
                f'<div class="tm-times"><span>{fmt_time(seek_time)}</span><span>{dur_label}</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if all_moments:
                with st.container(key="tl_pills", horizontal=True, gap="small"):
                    for t in all_moments:
                        if st.button(fmt_time(t), key=f"tl_btn_{t}"):
                            st.session_state.seek_time = t
                            st.rerun()

    with col_right:
        with st.container(key="chat_card", border=True):
            with st.container(key="chat_head"):
                h_title, h_actions = st.columns([0.5, 4.5], vertical_alignment="center")
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
                            "Download chat",
                            data=lambda: format_chat_markdown(title, source_label, st.session_state.get("chat_history", [])),
                            file_name=f"tubemate-chat-{slug}.md",
                            mime="text/markdown",
                            on_click="ignore",
                            disabled=not st.session_state.chat_history,
                        )
                        st.download_button(
                            "Download summary",
                            data=lambda: engine.get_summary(),
                            file_name=f"tubemate-summary-{slug}.md",
                            mime="text/markdown",
                            on_click="ignore",
                        )
                        st.download_button(
                            "Download Anki",
                            data=lambda: engine.get_anki_txt(),
                            file_name=f"tubemate-anki-{slug}.txt",
                            mime="text/plain",
                            on_click="ignore",
                        )
                        if st.button("Clear"):
                            st.session_state.chat_history = []
                            st.session_state.seek_time = 0
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
                                if item.get("timestamp", 0) > 0:
                                    if st.button(f"Jump to {fmt_time(item['timestamp'])}", key=f"quiz_ts_{q_idx}"):
                                        st.session_state.seek_time = item["timestamp"]
                                        st.rerun()
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
                    for idx, msg in enumerate(st.session_state.chat_history):
                        if msg["role"] == "user":
                            st.markdown(
                                f'<div class="tm-u-row"><div class="tm-u">{html.escape(msg["content"])}</div></div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(msg["content"])
                            if moments := msg.get("moments"):
                                with st.container(key=f"ts_row_{idx}", horizontal=True, gap="small"):
                                    st.markdown('<span class="tm-from">From</span>', unsafe_allow_html=True)
                                    for t in moments:
                                        if st.button(fmt_time(t), key=f"msg_{idx}_ts_{t}"):
                                            st.session_state.seek_time = t
                                            st.rerun()

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
    <li><b>Ask, jump & export</b><span>Jump straight to cited timestamps and download the chat, summary, or Anki flashcards (.txt).</span></li>
  </ol>
</section>
<p class="tm-foot">Answers come only from the transcript. If something isn't in the recording, TubeMate says so.</p>
""", unsafe_allow_html=True)
