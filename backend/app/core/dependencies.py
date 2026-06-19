from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun
from app.core.config import GROQ_API_KEY

embedding_model = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=GROQ_API_KEY,
    temperature=0.1
)

web_search_tool = DuckDuckGoSearchRun()
