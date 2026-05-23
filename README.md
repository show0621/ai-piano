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

- **ffmpeg**：YouTube 下載必備（[下載](https://ffmpeg.org/) 並加入 PATH）

## 部署到 Streamlit Cloud

1. 將專案推送到 **GitHub**（見下方指令）
2. 前往 [share.streamlit.io](https://share.streamlit.io)
3. **New app** → 選擇 Repo → Main file path：`app.py`
4. 等待安裝完成（含 `basic-pitch` / TensorFlow，約 5–10 分鐘）

### 專案已包含的 Cloud 設定

| 檔案 | 用途 |
|------|------|
| `requirements.txt` | Python 依賴（含 `tensorflow-cpu`） |
| `packages.txt` | 系統套件 `ffmpeg`（YouTube 用） |
| `.streamlit/config.toml` | 主題與上傳大小上限 |

### Cloud 注意事項

- **記憶體**：`basic-pitch` 推論建議 Streamlit **Memory 2GB+**（App settings → Advanced）
- **冷啟動**：首次抓譜較慢，可能超過預設 timeout
- **YouTube**：雲端環境可能受網路/政策限制，建議以**上傳音檔**為主
- 音檔過大（>12MB）嵌入 iframe 可能變慢，請剪輯至 3 分鐘內

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
