
# 🍛 KhauBot — Mumbai's Hyperlocal Food Discovery Platform

> AI-powered food discovery for Mumbai's informal food economy — street stalls, neighbourhood cafes, and cloud kitchens that Zomato/Swiggy don't cover.

## 🌟 What is KhauBot?

KhauBot is a two-sided platform:
- **For Vendors** — Any informal food business (street stall, cafe, cloud kitchen) can register for free. No GST, no FSSAI, no paperwork.
- **For Users** — Search for food using natural language: *"spicy vada pav near Bandra under ₹50"* and KhauBot understands you.

## 🚀 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI (Python) |
| NLP Pipeline | langdetect + keyword extraction |
| Database | SQLite |
| Frontend | Django 5 + Tailwind CSS |
| API Communication | httpx |

## ⚙️ Running Locally

### 1. Backend (FastAPI)
```bash
cd khaubot/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### 2. Frontend (Django)
```bash
cd khaubot/frontend/khaubot_web
pip install -r ../requirements.txt
python manage.py migrate
python manage.py runserver 8002
```

### 3. Open in browser
- Frontend: http://127.0.0.1:8002
- API Docs: http://127.0.0.1:8001/docs

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/discover | Natural language food search |
| POST | /api/vendor/register | Register a new vendor |
| GET | /api/vendor/all | List all vendors |
| PATCH | /api/vendor/{id}/approve | Approve a vendor |
| GET | /api/destinations | List all approved vendors |

## 🧠 How the NLP Pipeline Works

```
User types query
      ↓
Language detection (English / Hindi / Hinglish)
      ↓
Extract area (Bandra, Andheri, Juhu...)
      ↓
Extract cuisine / dish (vada pav, biryani, chai...)
      ↓
Extract price limit (under ₹100)
      ↓
Detect vibe (budget meal, study cafe, late night...)
      ↓
Match against vendor database
      ↓
Return ranked results
```

## 📁 Project Structure

```
khaubot/
├── backend/                  # FastAPI backend
│   ├── main.py               # App entry point
│   ├── models.py             # Vendor DB models
│   ├── database.py           # SQLite connection
│   ├── routers/
│   │   ├── vendors.py        # Vendor endpoints
│   │   └── discover.py       # Discovery endpoints
│   └── nlp/
│       └── pipeline.py       # NLP brain
│
└── frontend/                 # Django frontend
    └── khaubot_web/
        ├── config/           # Django settings
        ├── core/             # Main app
        └── templates/        # HTML pages
```

## 🔜 Roadmap

- [ ] Hindi + Marathi full NLP support
- [ ] PostgreSQL + pgvector semantic search  
- [ ] WhatsApp Business API integration
- [ ] Mobile app
- [ ] Deploy on Railway

## 📄 Research

This project is based on an IEEE-style research paper on AI-powered hyperlocal food discovery for Mumbai's informal food economy.
```
