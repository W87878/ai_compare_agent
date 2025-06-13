
# 🎓 analyze Agent - 文件比較與分析 AI 助理

## 功能特色
- 📄 比較兩份 PDF 文件，根據使用者提問做分析與回答
- 💬 支援 WebSocket 串流回應，即時呈現回答內容，提高互動體驗

## 快速開始

### 1. 安裝套件
```bash
pip install -r requirements.txt
```

### 2. 設定環境變數
建立 `.env` 檔案，內容如下：

```env
OPENAI_API_KEY=your_key_here
```

或直接在 CLI 中執行：
```bash
export OPENAI_API_KEY=your_key_here
```

### 3. 執行伺服器
```bash
python main.py
```

預設會啟動在 `ws://localhost:8000/ws/compare`

### 4. 前端頁面
若你已建立 `frontend.html` 前端，可使用 VSCode 的 Live Server 外掛打開(使用 VSCode Live Server 或其他即時刷新工具時，頁面可能會自動刷新，影響測試流程。
建議改用瀏覽器直接打開本地 HTML 檔案（file:/// 路徑），或使用不會自動刷新的 HTTP 伺服器（例如 python3 -m http.server）避免自動刷新。):
```bash
# 或手動開啟 HTML 檔案
open frontend.html
```

## 輸入資料範例 （WebSocket 傳送 JSON）
```
{
  "file1": "./docs/2-3圓方程式.pdf", 
  "file2": "./docs/2-4圓與直線的關係.pdf",
  "question": "請比較這兩份文件"
}
```

## 資料來源
請將 PDF 檔案放到 `docs/` 資料夾中，會自動建立向量索引。

## 聯絡作者
Steve Wang | 2025
