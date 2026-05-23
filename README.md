# AI 互動鋼琴教學

上傳 MP3、YouTube 連結或選擇示範曲，透過 **basic-pitch** 自動抓譜，並以 Synthesia 式下落音符 + 雙八度鍵盤進行跟彈教學。

## 功能

- 上傳 MP3 / WAV / M4A → AI 轉 MIDI 樂譜
- YouTube 連結下載（需 ffmpeg）
- 雙八度鍵盤（C4–B4、C5–B5）
- 跟彈判定、观摩教學、A-B 段落循環

## 本機執行

```bash
cd 鋼琴專案
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
streamlit run app.py
```

首次 AI 抓譜會下載模型，請耐心等候。

### 本機額外需求

- **Python 3.11**（TensorFlow / basic-pitch 不支援 3.14）
- **ffmpeg**：YouTube 下載必備（[下載](https://ffmpeg.org/) 並加入 PATH）

本機安裝（含 AI）：

```bash
pip install -r requirements.txt -r requirements-ml.txt
```

## Spotify API 與金鑰安全

**不要把** `client_id` / `client_secret` 寫進程式或 push 到 GitHub。

| 環境 | 金鑰放哪裡 |
|------|------------|
| **Streamlit Cloud** | App → **Settings** → **Secrets**（加密，不進 repo） |
| **本機** | `.streamlit/secrets.toml` 或 `.env`（已在 `.gitignore`） |
| **GitHub Actions** | Repo → **Settings** → **Secrets and variables** → **Actions** |

`secrets.toml` 範例見 `.streamlit/secrets.toml.example`。  
CI 會執行 `.github/workflows/secret-hygiene.yml`，防止誤提交金鑰檔。

## 部署到 Streamlit Cloud

1. 將專案推送到 **GitHub**
2. 前往 [share.streamlit.io](https://share.streamlit.io) → **New app** → Repo：`app.py`
3. **重要（Python 版本）**：日誌若顯示 `Using Python 3.14.x`，請到 [share.streamlit.io](https://share.streamlit.io) → 你的 App → **Settings** → **Advanced settings** → **Python version** 選 **3.11**，儲存後 Reboot。  
   若進階設定裡沒有 3.11 或改完仍是 3.14：**刪除 App** → 重新 **Deploy**，在進階設定中選 **Python 3.11**（TensorFlow / basic-pitch 需要 3.11，無法在 3.14 安裝）。

### AI 抓譜

`requirements.txt` 已包含 `-r requirements-ml.txt`（TensorFlow + basic-pitch）。  
部署時請使用 **Python 3.11** 與 **Memory 2GB+**，首次啟動需等待安裝與模型下載。

### 專案已包含的 Cloud 設定

| 檔案 | 用途 |
|------|------|
| `.python-version` / `runtime.txt` | 建議值 3.11（新 App 可參考） |
| `pyproject.toml` | 核心依賴；ML 在 `[project.optional-dependencies]` |
| `packages.txt` | `ffmpeg` + Pillow 編譯用 `zlib` / `jpeg` / `png` 開發套件 |
| `requirements.txt` | 核心依賴 |
| `requirements-ml.txt` | TensorFlow + basic-pitch |
| `packages.txt` | 系統套件 `ffmpeg` |
| `.streamlit/config.toml` | 主題與上傳大小上限 |

### Cloud 注意事項

- **記憶體**：App settings → Advanced → **Memory 2GB+**
- **冷啟動**：首次 AI 抓譜會下載模型，較慢
- **YouTube 403**：雲端機房 IP 常被 YouTube 封鎖 → **請改上傳 MP3**。進階可在 Streamlit Secrets 設定：
  ```toml
  [youtube]
  cookies_txt = """
  # Netscape HTTP Cookie File
  .youtube.com	TRUE	...
  """
  ```
  （用瀏覽器擴充「Get cookies.txt」匯出後貼上全文）

## 鍵盤對照（雙八度）

| 八度 | Do Re Mi Fa Sol La Si | 鍵盤 |
|------|------------------------|------|
| C4–B4 | 下排 | **A S D F G H J** |
| C5–B5 | 上排 | **Q W E R T Y U** |

## 推送到 GitHub

```bash
cd 鋼琴專案
git init
git add .
git commit -m "AI piano: Streamlit app with basic-pitch and dual-octave keyboard"
git branch -M main
git remote add origin https://github.com/你的帳號/ai-piano.git
git push -u origin main
```

## 專案結構

```
├── app.py                 # Streamlit 主程式
├── audio_processor.py     # AI 抓譜、YouTube 下載
├── frontend.html          # 互動鋼琴 UI
├── requirements.txt
├── packages.txt           # Streamlit Cloud 系統套件
├── .streamlit/config.toml
└── README.md
```
