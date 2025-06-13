import os
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from dotenv import load_dotenv 
load_dotenv('.env')  # 載入環境變數
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set.")

def build_vectorstore(file_name):
    if not file_name.endswith(".pdf"):
        raise ValueError("File path must point to a PDF file.")
    
    loader = PyMuPDFLoader(f"{file_name}")
    splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = loader.load_and_split(splitter)
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    
    index_path = f"vectorstore/{file_name}/faiss_index"
    if os.path.exists(index_path):
        print("Using existing vectorstore index.")
        vectordb = FAISS.load_local(
            index_path,
            OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY),
            allow_dangerous_deserialization=True
        )
    else:
        vectordb = FAISS.from_documents(docs, embeddings)
        print(f"Vectorstore built with {len(docs)} chunks.")
        os.makedirs(index_path, exist_ok=True)
        vectordb.save_local(index_path)
    return vectordb

if __name__ == '__main__':
    print(0)