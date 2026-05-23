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

## 部署到 Streamlit Cloud

1. 將專案推送到 **GitHub**
2. 前往 [share.streamlit.io](https://share.streamlit.io) → **New app** → Repo：`app.py`
3. **重要**：Community Cloud **無法在部署後改 Python 版本**。若 App 是用 Python 3.14 建的，必須 **刪除 App 後重新 Deploy**，才會讀取 repo 的 `.python-version`（`3.11`）。

### 兩階段部署（建議）

| 階段 | `requirements.txt` | 效果 |
|------|-------------------|------|
| 先讓網站能開 | 維持 ML 那行**註解** | 示範曲、鍵盤教學可用 |
| 啟用 AI 抓譜 | 取消 `# -r requirements-ml.txt` 註解 + **用 3.11 重新 Deploy** | 上傳 / YouTube / 搜尋抓譜 |

### 專案已包含的 Cloud 設定

| 檔案 | 用途 |
|------|------|
| `.python-version` | 部署時使用 **Python 3.11** |
| `runtime.txt` | 同上（`python-3.11`） |
| `pyproject.toml` | 宣告 `requires-python >=3.11,<3.13` |
| `requirements.txt` | 核心依賴 |
| `requirements-ml.txt` | TensorFlow + basic-pitch |
| `packages.txt` | 系統套件 `ffmpeg` |
| `.streamlit/config.toml` | 主題與上傳大小上限 |

### Cloud 注意事項

- **記憶體**：App settings → Advanced → **Memory 2GB+**
- **冷啟動**：首次 AI 抓譜會下載模型，較慢
- **YouTube**：雲端可能受限，建議以上傳音檔為主

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
