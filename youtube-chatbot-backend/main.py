import os
from fastapi import FastAPI, Path, Query
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import asyncio
import threading

if threading.current_thread() is not threading.main_thread():
    asyncio.set_event_loop(asyncio.new_event_loop())


load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

@app.post("/init")
async def init_video(data: dict):
    video_id = data["video_id"]
    print(video_id)
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.fetch(video_id=video_id, languages=['en']).to_raw_data()
    except TranscriptsDisabled:
        print("Transcripts are disabled for this video.")
        return {"enabled": False, "message": "Transcripts are disabled for this video."}
    
    transcript = " ".join(chunk["text"] for chunk in transcript_list)
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.create_documents([transcript])
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    vector_store = FAISS.from_documents(chunks, embeddings)

    save_dir = f"vectorstores/{video_id}"
    os.makedirs(save_dir, exist_ok=True)

    # Save vector store
    vector_store.save_local(save_dir)

def format_docs(retrieved_docs):
  context = "\n\n".join(doc.page_content for doc in retrieved_docs)
  return context


@app.post("/chat")
async def chat(data: dict):
    video_id = data["video_id"]
    question = data["question"]
    print(video_id, question)
    load_dir = f"vectorstores/{video_id}"
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    vector_store = FAISS.load_local(load_dir, embeddings, allow_dangerous_deserialization=True)
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})
    prompt = PromptTemplate(
    template="""
    You are a helpful assistant.
    Answer ONLY from the transcript context.
    If the context is insufficient, just say you don't know

    {context}
    Question: {question}
    """,
    input_variables=["context", "question"]
    )
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2)
    parser = StrOutputParser()
    parallel_chain = RunnableParallel({
    'context': retriever | RunnableLambda(format_docs),
    'question': RunnablePassthrough()
    })
    generation_chain = parallel_chain | prompt | model | parser
    answer = generation_chain.invoke(question)
    return {"answer": answer}