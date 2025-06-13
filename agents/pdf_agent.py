from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
import asyncio
from langchain.prompts import SystemMessagePromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from langchain.callbacks.streaming_aiter import AsyncIteratorCallbackHandler
from dotenv import load_dotenv
load_dotenv()  # 載入環境變數
import os
# 確保已經設定了 OPENAI_API_KEY 環境變數
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # 取得環境變數的值
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set.")
from rag.vectorstore import build_vectorstore  # 你自己的 FAISS 載入器

async def run_retriever(question, file_name1, file_name2):
    # Step 1: 準備向量資料庫與檢索器
    vectordb1 = build_vectorstore(file_name1)
    retriever1 = vectordb1.as_retriever()
    vectordb2 = build_vectorstore(file_name2)
    retriever2 = vectordb2.as_retriever()

    def format_docs(docs: list[Document]) -> str:
        return "\n\n".join(doc.page_content for doc in docs)

    # 用非 streaming LLM 執行兩段回答（先執行好 RAG）
    static_llm = ChatOpenAI(api_key=OPENAI_API_KEY, temperature=0)

    # Step 3: 對兩份文件個別執行 RAG 查詢
    system_prompt = SystemMessagePromptTemplate.from_template(
    template= """
        你是一位專業的文件處理員，請針對這份文件，依據使用者的問題，合理回答問題，務必稱呼為『這份文件』：

        PDF 內容：
        {context}

        問題：
        {question}

        請回答：
        """,
        template_format="f-string"  # 👈 明確指定格式
    )

    base_prompt = ChatPromptTemplate.from_messages([
        system_prompt
    ])
    
    base_chain = (
        {"context": retriever1 | RunnableLambda(format_docs), "question": RunnablePassthrough()}
        | base_prompt
        | static_llm
        | StrOutputParser()
    )

    base_chain2 = (
        {"context": retriever2 | RunnableLambda(format_docs), "question": RunnablePassthrough()}
        | base_prompt
        | static_llm
        | StrOutputParser()
    )
    
    answer1 = await base_chain.ainvoke(question)
    answer2 = await base_chain2.ainvoke(question)
    
    return {'answer1':answer1, 'answer2':answer2}

from openai import AsyncOpenAI
openai = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def pdf_qa_agent_stream(question, answer1, answer2, memory):
    prompt = f"""
    根據以下文件內容回答使用者問題：
    文件1: {answer1}
    文件2: {answer2}
    
    問題: {question}
    """
    response = await openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    full_response = ''
    i = 0
    async for chunk in response:
        delta = chunk.choices[0].delta.content or ""
        if delta != '':
            full_response += delta
            i += 1
            yield delta

    memory.save_context({"input": question}, {"output": full_response})

if __name__ == '__main__':
    print(0)