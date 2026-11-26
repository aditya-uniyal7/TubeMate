import json
import os
import re
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from transcription import Transcription, extract_youtube_id

load_dotenv()


def _fmt_ts(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hrs, rem = divmod(seconds, 3600)
    mins, secs = divmod(rem, 60)
    return f"{hrs}:{mins:02d}:{secs:02d}" if hrs else f"{mins}:{secs:02d}"


def _parse_json_list(raw: str) -> list | None:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, list) else None
    except Exception:
        return None


class Engine:
    def __init__(self, source, file_bytes=None, filename=None):
        self.source = source
        self.vid = extract_youtube_id(source) or source
        self.error = None

        if file_bytes is not None and filename:
            self.segments, self.transcript_source, self.error = Transcription.transcribe_uploaded_file(
                file_bytes, filename
            )
            self.video_info = {"title": filename, "author": "Uploaded File"}
        else:
            self.segments, self.transcript_source, extra_meta, self.error = (
                Transcription.get_segments_with_source(source)
            )
            info = Transcription.get_video_info(source)
            if extra_meta:
                info["title"] = extra_meta.get("title") or info["title"]
                info["author"] = extra_meta.get("author") or info["author"]
            self.video_info = info

        self.transcription = " ".join(seg["text"] for seg in self.segments) if self.segments else None
        self.total_duration = (
            int(max(seg["start"] + seg.get("duration", 0.0) for seg in self.segments))
            if self.segments
            else 0
        )
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=1024)
        self.vectorstore = None
        self._summary = None
        self._anki_txt = None
        self._quiz = None

    def _build_timestamped_chunks(self):
        if not self.segments:
            chunks = self.text_splitter.split_text(self.transcription)
            return chunks, [{"start": 0} for _ in chunks]

        if len(self.segments) == 1 and len(self.segments[0]["text"]) > 1000:
            chunks = self.text_splitter.split_text(self.segments[0]["text"])
            start_val = int(self.segments[0]["start"])
            return chunks, [{"start": start_val} for _ in chunks]

        chunks, metadatas, current_texts = [], [], []
        current_start = int(self.segments[0]["start"])
        current_len = 0

        for seg in self.segments:
            text = seg["text"].strip()
            if not text:
                continue
            if current_len + len(text) + 1 > 1000 and current_texts:
                chunks.append(" ".join(current_texts))
                metadatas.append({"start": current_start})
                overlap_texts, overlap_len = [], 0
                for prev in reversed(current_texts):
                    if overlap_len + len(prev) > 200:
                        break
                    overlap_texts.insert(0, prev)
                    overlap_len += len(prev) + 1
                current_texts, current_len = overlap_texts, overlap_len
                current_start = int(seg["start"])

            if not current_texts:
                current_start = int(seg["start"])
            current_texts.append(text)
            current_len += len(text) + 1

        if current_texts:
            chunks.append(" ".join(current_texts))
            metadatas.append({"start": current_start})

        return chunks, metadatas

    def process_transcription(self):
        if not self.transcription:
            print("No transcription available.")
            return False

        chunks, metadatas = self._build_timestamped_chunks()
        self.vectorstore = FAISS.from_texts(chunks, self.embeddings, metadatas=metadatas)
        return True

    def _ask_llm(self, template: str, temperature: float = 0, **kwargs) -> str:
        prompt = PromptTemplate(input_variables=list(kwargs.keys()), template=template)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=temperature)
        return (prompt | llm).invoke(kwargs).content

    def query_with_moments(self, question):
        if not self.vectorstore:
            return "Vector store has not been initialized yet. Call process_transcription() first.", []

        docs = self.vectorstore.similarity_search(question, k=4)
        context = "\n\n".join(doc.page_content for doc in docs)
        answer = self._ask_llm(
            "Answer the question in English using only the transcript context provided. "
            "Even if the transcript is in another language, translate the relevant details into clear English. "
            "If something isn't in the transcript, say so clearly in English.\n\n"
            "Context: {context}\n\nQuestion: {question}\n\nAnswer (in English):",
            context=context,
            question=question,
        )
        moments = sorted({
            int(doc.metadata["start"])
            for doc in docs
            if doc.metadata and "start" in doc.metadata
        })
        return answer, moments[:4]

    def query(self, question):
        answer, _ = self.query_with_moments(question)
        return answer

    def _sampled_transcript(self, max_chars: int = 14000) -> str:
        full = (
            "\n".join(f"[{_fmt_ts(int(s['start']))}] {s['text']}" for s in self.segments)
            if self.segments
            else (self.transcription or "")
        )
        if len(full) <= max_chars:
            return full
        step = max(1, len(full) // 10)
        excerpts = [full[i:i + 1200] for i in range(0, len(full), step)][:10]
        return "\n\n...\n\n".join(excerpts)

    def get_summary(self):
        if self._summary:
            return self._summary
        if not self.transcription:
            return "No transcript available to summarize."

        content = self._ask_llm(
            "Create a clear, structured Markdown summary in English based strictly on the transcript. "
            "If the transcript is in another language, translate the content into clear English.\n"
            "Include:\n"
            "1. Overview (2-3 sentences)\n"
            "2. Key Takeaways (bullet points with timestamps when available)\n"
            "3. Notable Details / Advice\n\n"
            "Title: {title}\n\nTranscript:\n{transcript}\n\nSummary (in English):",
            title=self.video_info.get("title", "Video"),
            transcript=self._sampled_transcript(),
        )
        self._summary = f"# {self.video_info.get('title', 'Video Summary')}\n\n{content.strip()}\n"
        return self._summary

    def get_anki_txt(self):
        if self._anki_txt:
            return self._anki_txt
        if not self.transcription:
            return ""

        raw = self._ask_llm(
            "Generate 10 to 14 high-yield Anki flashcards in English strictly from this transcript. "
            "If the transcript is in another language, translate both questions and answers into clear English.\n"
            "Return ONLY a valid JSON array of objects, each with 'front' (a concise question or concept) "
            "and 'back' (a clear, accurate answer, including the timestamp like [2:08] when available).\n"
            "Do not wrap the JSON in extra explanation.\n\n"
            "Title: {title}\n\nTranscript:\n{transcript}\n\nJSON:",
            title=self.video_info.get("title", "Video"),
            transcript=self._sampled_transcript(),
        ).strip()

        cards = _parse_json_list(raw) or [
            {"front": f"Key takeaway from {self.video_info.get('title', 'this video')}", "back": raw}
        ]
        lines = ["#separator:tab"]
        for card in cards:
            if isinstance(card, dict):
                front = " ".join(str(card.get("front", "")).split())
                back = " ".join(str(card.get("back", "")).split())
                if front and back:
                    lines.append(f"{front}\t{back}")

        self._anki_txt = "\n".join(lines) + "\n"
        return self._anki_txt

    def get_quiz(self, force_refresh: bool = False):
        if self._quiz and not force_refresh:
            return self._quiz
        if not self.transcription:
            return []

        raw = self._ask_llm(
            "Create a 5-question multiple-choice quiz in English strictly based on this transcript. "
            "If the transcript is in another language, translate questions and options into clear English.\n"
            "Return ONLY a valid JSON array of 5 objects. Each object must have:\n"
            "- 'question': string\n"
            "- 'options': array of exactly 4 short answer strings\n"
            "- 'answer_index': integer 0-3 indicating the correct option\n"
            "- 'explanation': 1-2 sentence explanation citing why it is correct\n"
            "- 'timestamp': integer seconds where this topic is discussed (or 0 if unknown)\n\n"
            "Title: {title}\n\nTranscript:\n{transcript}\n\nJSON:",
            temperature=0.2,
            title=self.video_info.get("title", "Video"),
            transcript=self._sampled_transcript(),
        ).strip()

        quiz = []
        for item in _parse_json_list(raw) or []:
            if not isinstance(item, dict):
                continue
            q_text = str(item.get("question", "")).strip()
            opts = [str(o).strip() for o in (item.get("options") or []) if str(o).strip()]
            idx = item.get("answer_index", 0)
            expl = str(item.get("explanation", "")).strip()
            try:
                ts = max(0, int(item.get("timestamp", 0)))
            except Exception:
                ts = 0
            if q_text and len(opts) >= 2 and isinstance(idx, int) and 0 <= idx < len(opts):
                quiz.append({
                    "question": q_text,
                    "options": opts[:4],
                    "answer_index": idx,
                    "explanation": expl,
                    "timestamp": ts,
                })

        self._quiz = quiz
        return self._quiz
