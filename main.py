from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
# from agents.pdf_agent import pdf_qa_agent
from agents.pdf_agent import pdf_qa_agent_stream, run_retriever
from memory.chat_memory import get_memory
from langchain_openai import OpenAI
from dotenv import load_dotenv 
from starlette.websockets import WebSocketDisconnect
import json
import shutil
import os
import uuid
from fastapi.middleware.cors import CORSMiddleware
import re
import asyncio

load_dotenv()  # 載入環境變數
import os
# 確保已經設定了 OPENAI_API_KEY 環境變數
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # 取得環境變數的值
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set.")

app = FastAPI()

# 允許前端跨網域連線
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 可指定前端網址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "./docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    safe_filename = re.sub(r'[-]', '_', file.filename)
    safe_file_id = re.sub(r'[-]', '_', file_id)
    file_path = UPLOAD_DIR + f"/{safe_file_id}_{safe_filename}"
    # 檢查 副檔名 是否不符合 .pdf
    if file.filename.split('.')[-1] != 'pdf':
        return '只支援 .pdf 格式的文件'
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"path": file_path}

llm = OpenAI(temperature=0, openai_api_key=OPENAI_API_KEY)

def detect_intent(text):
    prompt = f"""
    你是一個專門用來判斷語句意圖的分類器，請根據句子的內容，推理並分類為以下其中一類：
    - PDF：如果是與比較文件的問題相關的話，屬於 PDF。
    - OTHER：單純詢問與文件比較無關的問題。

    請模仿以下範例的格式與推理方式進行判斷，並只輸出分類名稱（PDF 或 OTHER）：

    ---

    **範例 1：**  
    句子：請比較這兩份文件中關於補習費用的差異？  
    推理：這是對兩份文件作比較的詢問，屬於文件分析比較問題。  
    分類：PDF

    ---

    **範例 2：**  
    句子：你今天心情怎麼樣？  
    推理：這是一句日常對話，與文件分析比較無關。  
    分類：OTHER

    ---

    **請根據上述邏輯推理以下句子：**  
    句子：{text}

    請直接輸出分類名稱（PDF、OTHER），不要包含推理過程。
    """
    intent = llm.invoke(prompt).strip().replace("分類：", "").upper()
    if intent != "PDF":
        intent = "OTHER"
    return intent

@app.websocket("/ws/compare")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()  # 一定要先呼叫 accept，才算正式連線成功
    print("✅ WebSocket connected and accepted")
    
    async def heartbeat(websocket, interval=10):
        try:
            while True:
                await asyncio.sleep(interval)
                await websocket.send_text("ping")
        except Exception:
            print("Heartbeat task cancelled")
    heartbeat_task = asyncio.create_task(heartbeat(websocket))
    memory = get_memory()
    try:
        while True:
            try:
                data = await websocket.receive_text()
            except WebSocketDisconnect:
                print("🟠 Client disconnected before sending message")
                break
            except RuntimeError as e:
                print("🔴 WebSocket runtime error while receiving:", e)
                break

            
            payload = json.loads(data)
            file1 = payload["file1"]
            file2 = payload["file2"]
            question = payload["question"]
            answer1 = ""
            answer2 = ""

            intent = detect_intent(question)
            
            async def stream_agent(agent_func):
                try:
                    async for chunk in agent_func(question, answer1, answer2, memory):
                        print(">> Streaming chunk:", repr(chunk))  # 👈 Log token
                        try:
                            await websocket.send_text(chunk)
                        except RuntimeError as e:
                            print("Client disconnected while streaming:", e)
                            break
                except WebSocketDisconnect:
                    print("🟠 Client disconnected, stop streaming")
                except Exception as e:
                    print("🔴 Unexpected error:", e)
                    try:
                        await websocket.send_text(f"[錯誤] {str(e)}")
                    except RuntimeError:
                        print("🟠 Cannot send error message, websocket closed")

            if intent == "PDF":
                # 先跑 retreiver 跟第一次 base_chain
                answers = await run_retriever(question, file1, file2)
                answer1 = answers['answer1']
                answer2 = answers['answer2']
                print(repr(answers))
                await stream_agent(pdf_qa_agent_stream)
                # await websocket.send_text("[DONE]")
            else:
                # OTHER 類型：讓 LLM 根據整段歷史給出一般性對答
                history = memory.load_memory_variables({})["history"]
                print(repr(history))  # 避免非 ascii 字元出錯
                prompt = f"""
                    你是一位日常對話的顧問，請根據以下歷史對話與使用者的最新問題，給出自然且有幫助的回應。

                    歷史對話：
                    {history}

                    使用者提問：
                    {question}

                    請回覆：
                    
                    若不太清楚使用者的意思，請給出一些引導性問題或建議，幫助使用者更清楚地表達需求。
                    例如：請明確輸入您的需求，例如PDF文件比較分析..
                """
                response = llm.invoke(prompt)
                await websocket.send_text(response)

    except WebSocketDisconnect:
        print("客戶端中斷連線")
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            print("Heartbeat task cancelled")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
