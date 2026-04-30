# KhauBot — Mumbai's Hyperlocal Food Discovery Platform

> AI-powered hyperlocal food discovery for Mumbai — street stalls, neighbourhood cafes, and cloud kitchens that Zomato/Swiggy don't cover. Now powered by real-time OpenStreetMap data across all of Mumbai.

> 71+ production deployments · Multilingual NLP · GPS "near me" detection · Real-time food discovery via OpenStreetMap · Mumbai's informal food economy, made searchable.

## What is KhauBot?

KhauBot is a two-sided hyperlocal food discovery platform:
- **For Users** — Search for food using natural language: *"momos near Dharavi"* or *"chai tapri near me"* and KhauBot finds real places instantly using your GPS location.
- **For Vendors** — Any informal food business (street stall, cafe, cloud kitchen) can register for free. No GST, no FSSAI, no paperwork. Get discovered by users who can't find you on Zomato or Swiggy.

---

## ⚙️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI (Python) |
| AI / LLM | Groq (llama3-70b-8192) |
| NLP Pipeline | langdetect + keyword extraction |
| Maps & Discovery | OpenStreetMap + Overpass API |
| Geocoding | Nominatim (free, no API key) |
| GPS Detection | Browser Geolocation API |
| Database | PostgreSQL (Neon DB) |
| Frontend | Django 5 + Tailwind CSS |
| API Communication | httpx |

---

## 🌐 Live Deployment

- Frontend: https://khaubot-171u.vercel.app/
- Backend API Docs: https://khaubot.vercel.app/docs

---

## 🗺️ How Real-Time Discovery Works

KhauBot uses a two-layer discovery system:

**GPS "near me" queries:**
```
User types: "chai near me"
        ↓
Browser Geolocation API sends real GPS coordinates
        ↓
Overpass API searches real food places within 5km of user
        ↓
Real nearby restaurants, cafes, street stalls shown first
        ↓
Registered KhauBot vendors shown below
```

**Area-based queries:**
```
User types: "momos near Versova"
        ↓
NLP extracts area → "versova"
        ↓
Nominatim geocodes → lat/lng coordinates
        ↓
Overpass API searches real food places within 5km
        ↓
Real Mumbai restaurants, cafes, street stalls shown
        ↓
(If vendor registered on KhauBot → shown first)
```

This means KhauBot works for **every Mumbai area** — Dharavi, Versova, Ghatkopar, anywhere — with zero manual data entry.

---

## 🧠 How the NLP Pipeline Works

```
User types query
      ↓
Language detection (English / Hindi / Hinglish)
      ↓
Groq AI extracts structured intent
      ↓
Extract area (Bandra, Andheri, Juhu...) OR use GPS if "near me"
      ↓
Extract cuisine / dish (vada pav, biryani, chai...)
      ↓
Extract price limit (under ₹100)
      ↓
Detect vibe (budget meal, study cafe, late night...)
      ↓
Search OpenStreetMap + vendor database
      ↓
Return ranked results
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/discover | Natural language food search |
| POST | /api/vendor/register | Register a new vendor |
| GET | /api/vendor/all | List all vendors |
| PATCH | /api/vendor/{id}/approve | Approve a vendor |
| GET | /api/destinations | List all approved vendors |

---

## 📁 Project Structure

```
khaubot/
├── backend/                  # FastAPI backend
│   ├── main.py               # App entry point
│   ├── models.py             # Vendor DB models
│   ├── database.py           # DB connection (SQLite local / Neon DB on prod)
│   ├── routers/
│   │   ├── vendors.py        # Vendor endpoints
│   │   └── discover.py       # Discovery + OSM + GPS integration
│   └── nlp/
│       └── pipeline.py       # NLP brain
│
└── frontend/                 # Django frontend
    └── khaubot_web/
        ├── config/           # Django settings
        ├── core/             # Main app + OSM search
        └── templates/        # HTML pages
```

---

## 🚀 Running Locally

### 1. Backend (FastAPI)
```bash
cd khaubot/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### 2. Frontend (Django)
```bash
cd khaubot/frontend/khaubot_web
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8002
```

### 3. Open in browser
- Frontend: http://127.0.0.1:8002
- API Docs: http://127.0.0.1:8001/docs

---

## ☁️ Deploy Frontend On Vercel

### Vercel project settings

1. Import repository in Vercel.
2. Set **Root Directory** to `khaubot/frontend/khaubot_web`.
3. Framework preset can stay **Other**.
4. Build command: No build command required (leave blank)
5. Install command: `pip install -r requirements.txt`

### Required environment variables

- `SECRET_KEY` = strong random value
- `DEBUG` = `False`
- `ALLOWED_HOSTS` = `.vercel.app`
- `CSRF_TRUSTED_ORIGINS` = `https://*.vercel.app`
- `KHAUBOT_API_URL` = your deployed backend URL

---

## ☁️ Deploy Backend On Vercel

### Backend Vercel project settings

1. Import the same repository as a second Vercel project.
2. Set **Root Directory** to `khaubot/backend`.
3. Install command: `pip install -r requirements.txt`
4. No custom build command is required.

### Required environment variables

- `DATABASE_URL` = Neon connection string
- `CORS_ORIGINS` = comma-separated allowed frontend origins
- `GROQ_API_KEY` = your Groq API key

---

## 🗄️ Neon DB Setup

Example `DATABASE_URL` format:

```
postgresql://<user>:<password>@<host>/<dbname>?sslmode=require
```

---

## 🗺️ Roadmap

- [x] FastAPI backend with vendor registration + discovery API
- [x] Django frontend deployed on Vercel
- [x] PostgreSQL (Neon DB) connected on production
- [x] Natural language search with Groq AI + NLP pipeline
- [x] OpenStreetMap real-time food discovery across all of Mumbai
- [x] Auto geocoding for any Mumbai area via Nominatim
- [x] GPS-based "near me" detection
- [ ] ChatGPT-style conversational responses
- [ ] WhatsApp Business API integration
- [ ] Vendor claim flow ("Is this your stall?")
- [ ] Mobile PWA

---

## 👩‍💻 Author

**Ketki Vijay Mohite**  
📧 [ketkimohite214@gmail.com](mailto:ketkimohite214@gmail.com)  
🎓 MCA Student | Backend Developer & AI Engineer