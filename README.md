# MyDramaList Unofficial API

A serverless FastAPI-based web scraper for MyDramaList.com, designed for deployment on Vercel.

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FB1PL0B%2FMyDramaList-Unofficial-API)

> **Note**: This project is inspired from [@tbdsux/kuryana](https://github.com/tbdsux/kuryana). Special thanks to [@tbdsux](https://github.com/tbdsux)!

---

## 🚀 Features

- **11 Endpoints** — Search, details, cast, episodes (list / single / enriched-all), reviews, recommendations, people, seasonal, lists, user watchlists
- **Episode Deep Scraping** — Visits each `/episode/{n}` page to extract description, cover image, rating, and season
- **Concurrent Fetching** — `episodes/all` batches requests (4 at a time) with anti-ban delays
- **Serverless Ready** — Optimized for Vercel deployment
- **Rate Limiting** — Built-in 1 s delay per endpoint call; 0.5 s pause between episode batches
- **Error Handling** — Consistent JSON error responses with proper HTTP status codes
- **Modular Design** — Separate `scraper.py` for all scraping logic

---

## 📋 API Endpoints

### 🔍 Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/search/q/{query}` | Search dramas by title. Returns up to 20 results. |

### 🎬 Drama

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/id/{slug}` | Full drama details — title, synopsis, genres, cast, rating, etc. |
| GET | `/api/id/{slug}/cast` | Cast & crew grouped by role |
| GET | `/api/id/{slug}/reviews` | User reviews (up to 10) |
| GET | `/api/id/{slug}/recs` | Drama recommendations with reasons and votes |

### 📺 Episodes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/id/{slug}/episodes` | Episode list — number, title, air date |
| GET | `/api/id/{slug}/episodes/{n}` | **Single episode** — title, description, cover image, air date, rating, season |
| GET | `/api/id/{slug}/episodes/all` | **All episodes enriched** — concurrently fetches every episode page for full details |

### 👤 People & Lists

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/people/{people_id}` | Person details — biography, filmography, personal info |
| GET | `/api/seasonal/{year}/{quarter}` | Top dramas for a season (quarter: `1`=Winter `2`=Spring `3`=Summer `4`=Fall) |
| GET | `/api/list/{id}` | Items in a user-created public list |
| GET | `/api/dramalist/{user_id}` | A user's public watchlist |

### ⚙️ Utility

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |

> **Slug format**: `{id}-{drama-name}` — e.g., `58651-run-on`, `746993-my-demon`

---

## 📊 Response Examples

### `GET /api/id/{slug}/episodes/{n}` — Single Episode
```json
{
  "episode_number": "1",
  "url": "https://mydramalist.com/58651-run-on/episode/1",
  "title": "Run On Episode 1",
  "image": "https://i.mydramalist.com/pRvkV_3m.jpg",
  "description": "Ki Seon Gyeom notices bruises on Kim Woo Shik's body. Trying to get back into her professor's good graces, Oh Mi Joo takes on an interpreting gig. (Source: Netflix)",
  "air_date": "December 16, 2020",
  "rating": "8.5/10",
  "season": "1"
}
```

### `GET /api/id/{slug}/episodes/all` — All Episodes Enriched
```json
{
  "episodes": [
    {
      "episode_number": "1",
      "title": "Run On Episode 1",
      "air_date": "Dec 16, 2020",
      "description": "Ki Seon Gyeom notices bruises on Kim Woo Shik's body...",
      "image": "https://i.mydramalist.com/pRvkV_3m.jpg",
      "rating": "8.5/10",
      "season": "1"
    }
  ],
  "total": 16
}
```

### `GET /api/id/{slug}/episodes` — Episode List
```json
{
  "episodes": [
    { "episode_number": "1", "title": "Run On Episode 1", "air_date": "Dec 16, 2020" },
    { "episode_number": "2", "title": "Run On Episode 2", "air_date": "Dec 17, 2020" }
  ],
  "total": 16
}
```

### `GET /api/search/q/{query}`
```json
{
  "results": [
    {
      "title": "Squid Game",
      "slug": "40257-round-six",
      "year": "2021",
      "image": "https://i.mydramalist.com/X6vkX_4s.jpg",
      "rating": "8.4",
      "url": "https://mydramalist.com/40257-round-six"
    }
  ],
  "total": 20
}
```

### `GET /api/id/{slug}/recs`
```json
{
  "recommendations": [
    {
      "title": "My Secret Romance",
      "year": "2017",
      "slug": "21465-my-secret-romance",
      "url": "https://mydramalist.com/21465-my-secret-romance",
      "image": "https://i.mydramalist.com/...",
      "rating": "7.3",
      "reasons": ["Both have office romance", "Similar chemistry between leads"],
      "recommended_by": "username",
      "votes": "42"
    }
  ],
  "total": 25,
  "pages_fetched": 1
}
```

### Error Response
```json
{
  "code": 404,
  "error": true,
  "description": "404 Not Found"
}
```

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.12 | Primary language |
| FastAPI | Web framework + auto `/docs` |
| BeautifulSoup4 | HTML parsing |
| curl_cffi | Anti-bot HTTP requests (browser impersonation) |
| Uvicorn | ASGI server |

---

## 📁 Project Structure

```
project_root/
├── main.py              # FastAPI routes
├── scraper.py           # All scraping logic
├── requirements.txt     # Dependencies
├── vercel.json          # Vercel serverless config
├── static/
│   └── index.html       # Interactive API docs UI
└── README.md
```

---

## 🔧 Local Development

1. **Clone and setup**:
   ```bash
   git clone https://github.com/B1PL0B/MyDramaList-Unofficial-API.git
   cd MyDramaList-Unofficial-API
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run development server**:
   ```bash
   python -m uvicorn main:app --reload --port 9000
   ```

4. **Access**:
   - Custom UI Docs: http://localhost:9000
   - Swagger UI:     http://localhost:9000/docs
   - ReDoc:          http://localhost:9000/redoc
   - Health Check:   http://localhost:9000/api/health

---

## 🚀 Vercel Deployment

```bash
# 1. Install Vercel CLI
npm i -g vercel

# 2. Deploy
vercel --prod
```

Or use the one-click button at the top of this README.

---

## ⚠️ Important Notes

### Episode Endpoints
- `/episodes/{n}` — makes **1 extra HTTP request** per call (the episode detail page)
- `/episodes/all` — makes **N extra requests** (one per episode), batched 4 at a time with 0.5 s delays. Expect ~5–15 s for a 16-episode drama.

### Vercel Limits (Free Tier)
| Limit | Value |
|-------|-------|
| Max execution time | 10 s |
| Function size | 15 MB |
| Cold starts | Possible on first request |

> ⚠️ `/episodes/all` may time out on Vercel's free tier for long dramas. Consider deploying your own instance or using individual `/episodes/{n}` calls instead.

### Rate Limiting
- 1 s delay on every endpoint entry
- 0.5 s pause between episode batch groups

---

## 🔍 Error Handling

| Code | Meaning |
|------|---------|
| 400 | Invalid parameters or private resource |
| 404 | Resource not found |
| 500 | Server-side scraping error |

---

## 📝 License

Educational use only. Please respect MyDramaList.com's terms of service.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request
