# AI 互動鋼琴教學

上傳 MP3、MIDI 檔或從曲庫載入樂譜，以 Synthesia 式下落音符 + 雙八度鍵盤進行跟彈教學。可選 **basic-pitch** 從音檔自動抓譜。

## 功能

- **📁 上傳 MP3 / WAV / M4A** → AI 轉鋼琴譜（需 TensorFlow）
- **🎹 MIDI 檔**：BitMidi、MuseScore、EOP 等下載 `.mid` 後上傳 → 立即練習
- **📚 曲庫**：`scores/` 內預先轉好的 JSON（免 AI）
- **🔍 搜尋樂譜**：BitMidi、IMSLP、GitHub ABC + 外站搜尋連結
- **🔗 直接音檔網址**：僅支援 `.mp3` / `.wav` 等直連（**不含 YouTube / Spotify**）
- **🌸 示範曲**：小星星、簡單愛＋10 首兒歌／動畫＋貝多芬／卡農等公版曲
- 雙八度鍵盤（C4–B5）· 跟彈判定、A-B 循環

### 流行樂 MIDI 從哪裡找？

| 類型 | 推薦來源 |
|------|----------|
| 華語流行 | 廷廷的鋼琴窩、Everyone Piano、影片說明欄 MIDI 連結 |
| 歐美流行 | BitMidi、FreeMidi、MuseScore |

App 內 **🎹 MIDI 檔** 或側邊欄 **流行樂 MIDI 哪裡找？** 有完整說明與一鍵搜尋連結。

### 混合模式（推薦）

1. 外站下載 **.mid** → **🎹 MIDI 檔** 上傳；或本機 MP3 → AI 抓譜 → **匯出 JSON**
2. 將 JSON 放入 `scores/`、更新 `scores/index.json`、push GitHub（建議 **私有倉庫**，見下方）
3. **雲端 / 手機**：**📚 曲庫** 直接載入練習

```bash
python tools/export_scores.py   # 從內建示範曲產生 scores/*.json
```

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
- **ffmpeg**：AI 抓譜轉檔時建議安裝（[下載](https://ffmpeg.org/) 並加入 PATH）

本機安裝（含 AI）：

```bash
pip install -r requirements.txt -r requirements-ml.txt
```

## 將 GitHub 設為不公開（私有倉庫）

適合：自己上傳 MIDI 轉成的 `scores/*.json`，**不想公開給所有人下載**。

### 在 GitHub 網站設定（約 1 分鐘）

1. 打開 [github.com/show0621/ai-piano](https://github.com/show0621/ai-piano)
2. **Settings**（倉庫設定，不是個人設定）
3. 拉到最下方 **Danger Zone**
4. **Change repository visibility** → 選 **Private** → 依畫面輸入倉庫名確認

設成 Private 後：

- 只有**你邀請的協作者**能看程式與 `scores/` 裡的樂譜
- 仍可用 `git push` 正常同步（遠端網址不變）
- **不等於**可任意上傳有版權的流行歌對外散布；但比公開 repo 適合放個人練習用扒譜

### 私有倉庫 + 曲庫 + Streamlit Cloud

| 項目 | 說明 |
|------|------|
| **📚 曲庫** | `scores/` 跟著專案一起部署，**不必**設 `github_raw_base` |
| **Secrets** | 私有倉庫的 `raw.githubusercontent.com` **無法**給外人讀；請**刪除或不要填** `[scores] github_raw_base` |
| **Streamlit** | [share.streamlit.io](https://share.streamlit.io) 連到你的 GitHub 時，選同一個 **private** repo 即可部署（需授權 Streamlit 讀取私有倉庫） |

## 部署到 Streamlit Cloud

1. 將專案推送到 **GitHub**（可為 Private）
2. 前往 [share.streamlit.io](https://share.streamlit.io) → **New app** → Repo：`app.py`
3. **Python 3.11**、**Memory 2GB+**，部署後 **Reboot**

### 專案已包含的 Cloud 設定

| 檔案 | 用途 |
|------|------|
| `runtime.txt` | Python 3.11 |
| `requirements.txt` | 核心依賴 + ML |
| `packages.txt` | `ffmpeg` 等系統套件 |
| `.streamlit/config.toml` | 主題與上傳上限 |

### Cloud 注意事項

- **記憶體**：App settings → **Memory 2GB+**
- **練習流行歌**：優先 **MIDI 上傳** 或 **曲庫**，勿依賴串流平台下載
- 選填 Secrets：`[scores] github_raw_base`（僅**公開**倉庫或另建公開鏡像時需要；**私有倉庫請勿使用**）

## 鍵盤對照（雙八度）

| 八度 | Do Re Mi Fa Sol La Si | 鍵盤 |
|------|------------------------|------|
| C4–B4 | 下排 | **A S D F G H J** |
| C5–B5 | 上排 | **Q W E R T Y U** |

## 專案結構

```
├── app.py
├── audio_processor.py     # AI 抓譜
├── media_fetch.py           # 直接音檔網址下載
├── score_library.py         # 曲庫
├── sheet_search.py          # 樂譜搜尋
├── midi_resources.py        # MIDI 資源指南
├── frontend.html
├── scores/                  # 曲庫 JSON
└── tools/export_scores.py
```
