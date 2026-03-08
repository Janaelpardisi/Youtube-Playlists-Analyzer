# 🎬 YouTube Playlist Analyzer

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Gemini AI](https://img.shields.io/badge/Gemini_AI-Powered-8E75B2?style=for-the-badge&logo=google&logoColor=white)
![YouTube API](https://img.shields.io/badge/YouTube_API-v3-FF0000?style=for-the-badge&logo=youtube&logoColor=white)

**An AI-powered web app that analyzes YouTube playlists using Google Gemini — helping you learn smarter, not harder.**

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 **Playlist Discovery** | Search YouTube channels or paste a playlist link directly |
| 🤖 **AI Video Analysis** | Each video is analyzed for difficulty level, type, topics & estimated watch time |
| 📋 **Executive Summary** | Get an AI-generated overview of the entire playlist |
| 🗺️ **Smart Learning Path** | AI-curated watching order for maximum learning efficiency |
| 💬 **Chat with Playlist** | Ask questions about the playlist content in natural language |
| ⚖️ **Compare Playlists** | Side-by-side AI comparison between two playlists |
| 💾 **Session Memory** | Resume previous analysis sessions anytime |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- A [YouTube Data API v3](https://console.cloud.google.com/apis/credentials) key
- A [Google Gemini API](https://aistudio.google.com/app/apikey) key

### Installation

**1. Clone the repository**
```bash
git clone https://github.com/Janaelpardisi/Youtube-Playlists-Analyzer.git
cd Youtube-Playlists-Analyzer
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Set up environment variables**
```bash
cp .env.example .env
```
Then edit `.env` and fill in your API keys:
```env
YOUTUBE_API_KEY=your_youtube_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

**4. Run the server**
```bash
python -m uvicorn backend.main:app --reload
```

**5. Open your browser**
```
http://localhost:8000
```

---

## 🏗️ Project Structure

```
youtube-playlist-analyzer/
│
├── backend/
│   ├── main.py                # FastAPI app & all API endpoints
│   ├── models/
│   │   └── schemas.py         # Pydantic data models
│   └── services/
│       ├── youtube_service.py # YouTube Data API integration
│       ├── gemini_service.py  # Google Gemini AI integration
│       ├── cache_service.py   # Local results caching
│       └── memory_service.py  # Session memory management
│
├── frontend/
│   ├── index.html             # Main UI
│   ├── css/                   # Stylesheets
│   └── js/                    # Frontend JavaScript
│
├── static/                    # Served static files
├── data/                      # Cached session data (auto-generated)
├── .env.example               # Environment variables template
├── requirements.txt           # Python dependencies
└── README.md
```

---

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI, Uvicorn
- **AI:** Google Gemini (gemini-1.5-flash)
- **Data:** YouTube Data API v3, YouTube Transcript API
- **Frontend:** Vanilla HTML, CSS, JavaScript
- **Storage:** Local JSON-based session caching

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/search` | Search for channels or playlist by URL |
| `GET` | `/api/channels/{id}/playlists` | Get playlists for a channel |
| `POST` | `/api/sessions/start` | Start a new analysis session |
| `POST` | `/api/sessions/{id}/analyze-next` | Analyze the next batch of videos |
| `POST` | `/api/sessions/{id}/summary` | Generate AI playlist summary |
| `POST` | `/api/sessions/{id}/learning-path` | Generate smart learning path |
| `POST` | `/api/sessions/{id}/chat` | Chat with the playlist using AI |
| `POST` | `/api/compare` | Compare two analyzed playlists |
| `GET` | `/api/sessions` | List all sessions |
| `DELETE` | `/api/sessions/{id}` | Delete a session |

---

## ⚙️ Environment Variables

| Variable | Description | Where to Get |
|---|---|---|
| `YOUTUBE_API_KEY` | YouTube Data API v3 key | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |
| `GEMINI_API_KEY` | Google Gemini API key | [Google AI Studio](https://aistudio.google.com/app/apikey) |

> ⚠️ **Never commit your `.env` file to GitHub.** It's already listed in `.gitignore`.

---

## 📬 Contact

<div align="center">

**Jana Ashraf El-Pardisi**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Jana_Ashraf-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/jana-ashraf-elpardisi)
[![Email](https://img.shields.io/badge/Email-janaelpardisi%40gmail.com-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:janaelpardisi@gmail.com)

</div>

---

<div align="center">

Made with ❤️ using FastAPI & Google Gemini AI

</div>
