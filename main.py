from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import logging
import asyncio
from scraper import MyDramaListScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tags_metadata = [
    {
        "name": "Search",
        "description": "Search for dramas by title.",
    },
    {
        "name": "Drama",
        "description": "Get full drama details, cast, reviews, and recommendations.",
    },
    {
        "name": "Episodes",
        "description": (
            "Episode data at three levels of detail:\n\n"
            "- **`/episodes`** — list (title + air date)\n"
            "- **`/episodes/{n}`** — single episode: description, cover image, rating, season\n"
            "- **`/episodes/all`** — all episodes enriched concurrently"
        ),
    },
    {
        "name": "People & Lists",
        "description": "Person profiles, seasonal charts, user-created lists, and watchlists.",
    },
    {
        "name": "Utility",
        "description": "Health check and diagnostics.",
    },
]

app = FastAPI(
    title="MyDramaList Unofficial API",
    description="""
## MyDramaList Unofficial Scraper API

An unofficial, serverless REST API that scrapes public data from [MyDramaList.com](https://mydramalist.com).
Built with **FastAPI + BeautifulSoup4 + curl_cffi** for browser-impersonated requests.

---

### 📺 Episodes — 3 levels of detail

| Endpoint | Data returned |
|----------|--------------|
| `/api/id/{slug}/episodes` | Episode list (number, title, air date) |
| `/api/id/{slug}/episodes/{n}` | Single episode: **description, cover image**, rating, season |
| `/api/id/{slug}/episodes/all` | All episodes with full details (concurrent fetching) |

> **Slug format**: `{id}-{drama-name}`, e.g. `58651-run-on`, `746993-my-demon`

---

### ⚠️ Rate limits & timeouts
- Every endpoint has a built-in **1 s delay**.
- `/episodes/all` makes one request per episode in batches of 4 (0.5 s between batches).
  Expect **5–15 s** for a 16-episode drama.
- On Vercel free tier (10 s timeout), prefer `/episodes/{n}` for individual lookups.

---

### 🔴 Error format
```json
{ "code": 404, "error": true, "description": "404 Not Found" }
```
""",
    version="1.1.0",
    openapi_tags=tags_metadata,
    license_info={"name": "Educational use only"},
    contact={"name": "GitHub", "url": "https://github.com/B1PL0B/MyDramaList-Unofficial-API"},
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize scraper
scraper = MyDramaListScraper()

@app.get("/")
async def root():
    """Redirect to static index page"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")

@app.get("/api/search/q/{query}", tags=["Search"],
         summary="Search dramas",
         description="Search MyDramaList by title. Returns up to 20 results including title, slug, year, image, rating, and URL.")
async def search_dramas(query: str):
    """Search for dramas by title query."""
    try:
        logger.info(f"Searching for: {query}")
        await asyncio.sleep(1)  # Rate limiting
        results = await scraper.search_dramas(query)
        return results
    except Exception as e:
        logger.error(f"Error searching dramas: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "error": True, "description": "Internal server error"}
        )

@app.get("/api/id/{slug}", tags=["Drama"],
         summary="Get drama details",
         description="Get full details for a drama by its slug (e.g. `58651-run-on`). Includes title, synopsis, genres, cast overview, rating, year, and more.")
async def get_drama_details(slug: str):
    """Get drama details by slug."""
    try:
        logger.info(f"Getting drama details for: {slug}")
        await asyncio.sleep(1)  # Rate limiting
        details = await scraper.get_drama_details(slug)
        if not details:
            return JSONResponse(
                status_code=404,
                content={"code": 404, "error": True, "description": "404 Not Found"}
            )
        return details
    except Exception as e:
        logger.error(f"Error getting drama details: {str(e)}")
        if "private" in str(e).lower():
            return JSONResponse(
                status_code=400,
                content={"code": 400, "error": True, "description": {"title": "This resource is private."}}
            )
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "error": True, "description": "Internal server error"}
        )

@app.get("/api/id/{slug}/cast", tags=["Drama"],
         summary="Get cast & crew",
         description="Returns cast and crew grouped by role (Main Role, Support Role, Guest Role, Director, Screenwriter, etc.).")
async def get_drama_cast(slug: str):
    """Get cast and crew for a drama."""
    try:
        logger.info(f"Getting cast for: {slug}")
        await asyncio.sleep(1)  # Rate limiting
        cast = await scraper.get_drama_cast(slug)
        if not cast:
            return JSONResponse(
                status_code=404,
                content={"code": 404, "error": True, "description": "404 Not Found"}
            )
        return cast
    except Exception as e:
        logger.error(f"Error getting drama cast: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "error": True, "description": "Internal server error"}
        )

@app.get("/api/id/{slug}/episodes", tags=["Episodes"],
         summary="Get episode list",
         description="Returns the full episode list for a drama: episode number, title, and air date. No per-episode page visits — fast.")
async def get_drama_episodes(slug: str):
    """Get episode list (number, title, air date) for a drama."""
    try:
        logger.info(f"Getting episodes for: {slug}")
        await asyncio.sleep(1)  # Rate limiting
        episodes = await scraper.get_drama_episodes(slug)
        if not episodes:
            return JSONResponse(
                status_code=404,
                content={"code": 404, "error": True, "description": "404 Not Found"}
            )
        return episodes
    except Exception as e:
        logger.error(f"Error getting drama episodes: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "error": True, "description": "Internal server error"}
        )

@app.get("/api/id/{slug}/episodes/all", tags=["Episodes"],
         summary="Get all episodes enriched",
         description="Fetches the episode list then **concurrently visits each episode page** (batches of 4, 0.5 s delay between batches) to retrieve description, cover image, rating, and season for every episode. Expect 5–15 s for a 16-episode drama.")
async def get_drama_episodes_all(slug: str):
    """Get all episodes with full details — description, cover image, rating, season."""
    try:
        logger.info(f"Getting all episode details for: {slug}")
        result = await scraper.get_drama_episodes_all(slug)
        if not result:
            return JSONResponse(
                status_code=404,
                content={"code": 404, "error": True, "description": "404 Not Found"}
            )
        return result
    except Exception as e:
        logger.error(f"Error getting all episode details: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "error": True, "description": "Internal server error"}
        )

@app.get("/api/id/{slug}/episodes/{episode_number}", tags=["Episodes"],
         summary="Get single episode details",
         description="Visits `/{slug}/episode/{n}` on MyDramaList and returns: **title, description, cover image, air date, rating, season**. One extra HTTP request per call.")
async def get_episode_details(slug: str, episode_number: int):
    """Get full details for a single episode by number."""
    try:
        logger.info(f"Getting episode {episode_number} details for: {slug}")
        detail = await scraper.get_episode_details(slug, episode_number)
        if not detail:
            return JSONResponse(
                status_code=404,
                content={"code": 404, "error": True, "description": "404 Not Found"}
            )
        return detail
    except Exception as e:
        logger.error(f"Error getting episode details: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "error": True, "description": "Internal server error"}
        )

@app.get("/api/id/{slug}/reviews", tags=["Drama"],
         summary="Get reviews",
         description="Returns up to 10 user reviews for a drama, including review text, overall score, story/acting/music/rewatch scores, author, and date.")
async def get_drama_reviews(slug: str):
    """Get user reviews for a drama."""
    try:
        logger.info(f"Getting reviews for: {slug}")
        await asyncio.sleep(1)  # Rate limiting
        reviews = await scraper.get_drama_reviews(slug)
        if not reviews:
            return JSONResponse(
                status_code=404,
                content={"code": 404, "error": True, "description": "404 Not Found"}
            )
        return reviews
    except Exception as e:
        logger.error(f"Error getting drama reviews: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "error": True, "description": "Internal server error"}
        )

@app.get("/api/id/{slug}/recs", tags=["Drama"],
         summary="Get recommendations",
         description="Returns drama recommendations for a given drama, including the recommended title, reasons given by users, vote count, and recommender username.")
async def get_drama_recommendations(slug: str):
    """Get drama recommendations with reasons and votes."""
    try:
        logger.info(f"Getting recommendations for: {slug}")
        await asyncio.sleep(1)  # Rate limiting
        recs = await scraper.get_drama_recommendations(slug)
        if not recs:
            return JSONResponse(
                status_code=404,
                content={"code": 404, "error": True, "description": "404 Not Found"}
            )
        return recs
    except Exception as e:
        logger.error(f"Error getting drama recommendations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "error": True, "description": "Internal server error"}
        )

@app.get("/api/people/{people_id}", tags=["People & Lists"],
         summary="Get person details",
         description="Returns biography, birthday, nationality, filmography, and social links for an actor/director/crew member. Use the slug from their MDL profile URL (e.g. `14472-song-kang`).")
async def get_person_details(people_id: str):
    """Get person details by slug (e.g. 14472-song-kang)."""
    try:
        logger.info(f"Getting person details for: {people_id}")
        await asyncio.sleep(1)  # Rate limiting
        person = await scraper.get_person_details(people_id)
        if not person:
            return JSONResponse(
                status_code=404,
                content={"code": 404, "error": True, "description": "404 Not Found"}
            )
        return person
    except Exception as e:
        logger.error(f"Error getting person details: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "error": True, "description": "Internal server error"}
        )

@app.get("/api/seasonal/{year}/{quarter}", tags=["People & Lists"],
         summary="Get seasonal dramas",
         description="Returns the top dramas for a specific year and quarter. Quarter values: `1`=Winter, `2`=Spring, `3`=Summer, `4`=Fall. Example: `/api/seasonal/2023/4`")
async def get_seasonal_dramas(year: int, quarter: int):
    """Get top dramas for a year and quarter (1=Winter, 2=Spring, 3=Summer, 4=Fall)."""
    try:
        if quarter not in [1, 2, 3, 4]:
            raise HTTPException(
                status_code=400,
                detail={"code": 400, "error": True, "description": "Quarter must be 1, 2, 3, or 4"}
            )
        
        logger.info(f"Getting seasonal dramas for: {year} Q{quarter}")
        await asyncio.sleep(1)  # Rate limiting
        dramas = await scraper.get_seasonal_dramas(year, quarter)
        return dramas
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting seasonal dramas: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "error": True, "description": "Internal server error"}
        )

@app.get("/api/list/{list_id}", tags=["People & Lists"],
         summary="Get drama list",
         description="Returns all dramas in a user-created public MDL list. Returns 400 if the list is private. Use the numeric list ID from the MDL list URL.")
async def get_drama_list(list_id: str):
    """Get dramas in a public MDL list by list ID."""
    try:
        logger.info(f"Getting drama list: {list_id}")
        await asyncio.sleep(1)  # Rate limiting
        drama_list = await scraper.get_drama_list(list_id)
        if not drama_list:
            return JSONResponse(
                status_code=404,
                content={"code": 404, "error": True, "description": "404 Not Found"}
            )
        return drama_list
    except Exception as e:
        logger.error(f"Error getting drama list: {str(e)}")
        if "private" in str(e).lower():
            return JSONResponse(
                status_code=400,
                content={"code": 400, "error": True, "description": {"title": "This list is private."}}
            )
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "error": True, "description": "Internal server error"}
        )

@app.get("/api/dramalist/{user_id}", tags=["People & Lists"],
         summary="Get user watchlist",
         description="Returns a user's public drama watchlist. Returns 400 if the watchlist is private. Use the MDL username or user ID.")
async def get_user_drama_list(user_id: str):
    """Get a user's public watchlist by user ID or username."""
    try:
        logger.info(f"Getting user drama list for: {user_id}")
        await asyncio.sleep(1)  # Rate limiting
        user_list = await scraper.get_user_drama_list(user_id)
        if not user_list:
            return JSONResponse(
                status_code=404,
                content={"code": 404, "error": True, "description": "404 Not Found"}
            )
        return user_list
    except Exception as e:
        logger.error(f"Error getting user drama list: {str(e)}")
        if "private" in str(e).lower():
            return JSONResponse(
                status_code=400,
                content={"code": 400, "error": True, "description": {"title": "This list is private."}}
            )
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "error": True, "description": "Internal server error"}
        )

# Health check endpoint
@app.get("/api/health", tags=["Utility"], summary="Health check")
async def health_check():
    """Returns healthy status if the API is running."""
    return {"status": "healthy", "version": "1.1.0", "message": "MyDramaList Unofficial API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
