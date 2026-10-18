import os
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from transcription import Transcription

load_dotenv()

class Engine:
    def __init__(self, vid):
        self.vid = vid
        self.transcription = Transcription.get_transcription(vid)
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=1024                
        )
        self.vectorstore = None

    def process_transcription(self):
        if not self.transcription:
            print("No transcription available.")
            return False

        chunks = self.text_splitter.split_text(self.transcription)

        self.vectorstore = FAISS.from_texts(chunks, self.embeddings)
        return True

    def query(self, question):
        if not self.vectorstore:
            return "Vector store has not been initialized yet. Call process_transcription() first."

        docs = self.vectorstore.similarity_search(question, k=4) # Optional: explicit document count
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template="Answer the question based on the context provided.\n\nContext: {context}\n\nQuestion: {question}\n\nAnswer:"
        )
        
        chain = prompt_template | llm
        
        context = "\n\n".join([doc.page_content for doc in docs])
        response = chain.invoke({"context": context, "question": question})
        
        return response.content                              
