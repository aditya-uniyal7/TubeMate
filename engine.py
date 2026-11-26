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
            self.transcription, self.transcript_source, self.error = Transcription.transcribe_uploaded_file(
                file_bytes, filename
            )
            self.video_info = {"title": filename, "author": "Uploaded File"}
        else:
            self.transcription, self.transcript_source, extra_meta, self.error = (
                Transcription.get_transcription_with_source(source)
            )
            info = Transcription.get_video_info(source)
            if extra_meta:
                info["title"] = extra_meta.get("title") or info["title"]
                info["author"] = extra_meta.get("author") or info["author"]
            self.video_info = info

        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=1024)
        self.vectorstore = None
        self._anki_txt = None
        self._quiz = None

    def process_transcription(self):
        if not self.transcription:
            print("No transcription available.")
            return False

        chunks = self.text_splitter.split_text(self.transcription)
        self.vectorstore = FAISS.from_texts(chunks, self.embeddings)
        return True

    def _ask_llm(self, template: str, temperature: float = 0, **kwargs) -> str:
        prompt = PromptTemplate(input_variables=list(kwargs.keys()), template=template)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=temperature)
        return (prompt | llm).invoke(kwargs).content

    def query(self, question):
        if not self.vectorstore:
            return "Vector store has not been initialized yet. Call process_transcription() first."

        docs = self.vectorstore.similarity_search(question, k=4)
        context = "\n\n".join(doc.page_content for doc in docs)
        return self._ask_llm(
            "Answer the question in English using only the transcript context provided. "
            "Even if the transcript is in another language, translate the relevant details into clear English. "
            "If something isn't in the transcript, say so clearly in English.\n\n"
            "Context: {context}\n\nQuestion: {question}\n\nAnswer (in English):",
            context=context,
            question=question,
        )

    def _sampled_transcript(self, max_chars: int = 14000) -> str:
        full = self.transcription or ""
        if len(full) <= max_chars:
            return full
        step = max(1, len(full) // 10)
        excerpts = [full[i:i + 1200] for i in range(0, len(full), step)][:10]
        return "\n\n...\n\n".join(excerpts)

    def get_anki_txt(self):
        if self._anki_txt:
            return self._anki_txt
        if not self.transcription:
            return ""

        raw = self._ask_llm(
            "Generate 10 to 14 high-yield Anki flashcards in English strictly from this transcript. "
            "If the transcript is in another language, translate both questions and answers into clear English.\n"
            "Return ONLY a valid JSON array of objects, each with 'front' (a concise question or concept) "
            "and 'back' (a clear, accurate answer).\n"
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
            "- 'explanation': 1-2 sentence explanation citing why it is correct\n\n"
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
            if q_text and len(opts) >= 2 and isinstance(idx, int) and 0 <= idx < len(opts):
                quiz.append({
                    "question": q_text,
                    "options": opts[:4],
                    "answer_index": idx,
                    "explanation": expl,
                })

        self._quiz = quiz
        return self._quiz
