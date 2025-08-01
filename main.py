# main.py

import logging
import httpx
from aiolimiter import AsyncLimiter
from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import ORJSONResponse, RedirectResponse

from scraper import OptimizedMyDramaListScraper, ScraperError

# --- Configuration ---

# Configure logging to show timestamps and log levels
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiter: 4 requests per second, respecting MyDramaList servers
# The client will burst up to 4 requests, then refill the token bucket at a rate of 4 per second.
limiter = AsyncLimiter(max_rate=4, time_period=1)

# Initialize a shared asynchronous HTTP client for connection pooling
# Using a timeout to prevent requests from hanging indefinitely
http_client = httpx.AsyncClient(
    headers={
        'User-Agent': 'MyDramaList-API-Scraper/1.1 (github.com/B1PL0B/MyDramaList-Unofficial-API; mailto:your-email@example.com)',
        'Accept-Language': 'en-US,en;q=0.5',
    },
    timeout=15.0, # Increased timeout for Vercel's cold starts
    follow_redirects=True,
)

# Initialize the optimized scraper with shared clients
scraper = OptimizedMyDramaListScraper(client=http_client, limiter=limiter)

# --- FastAPI App Initialization ---

app = FastAPI(
    title="MyDramaList Scraper API (Optimized)",
    description="An optimized, serverless API for scraping MyDramaList.com data using modern async libraries.",
    version="2.0.0",
    default_response_class=ORJSONResponse,  # Use orjson for faster JSON serialization
)

# Add Gzip middleware to compress responses and save bandwidth
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Mount static files (for the documentation page)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Event Handlers for Application Lifecycle ---

@app.on_event("shutdown")
async def shutdown_event():
    """Close the httpx client gracefully on application shutdown."""
    logger.info("Closing HTTP client...")
    await http_client.aclose()
    logger.info("HTTP client closed.")


# --- Centralized Error Handler ---

async def handle_scraper_exception(e: Exception, endpoint_name: str, resource_id: str):
    """
    Handles common exceptions from the scraper and maps them to HTTP exceptions.
    """
    logger.error(f"Error in '{endpoint_name}' for '{resource_id}': {str(e)}")
    if isinstance(e, ScraperError):
        # Specific errors raised from the scraper
        if "private" in e.message.lower() or "not found" in e.message.lower():
            status_code = 404
            description = e.message
        elif e.status_code == 429:
            status_code = 429
            description = "Rate limit exceeded on MyDramaList. Please try again later."
        else:
            status_code = e.status_code or 500
            description = e.message
    else:
        # Generic internal server error for unexpected issues
        status_code = 500
        description = "An internal server error occurred."
    
    raise HTTPException(
        status_code=status_code,
        detail={"code": status_code, "error": True, "description": description}
    )

# --- API Endpoints ---

@app.get("/", include_in_schema=False)
async def root():
    """Redirect to the static index page."""
    return RedirectResponse(url="/static/index.html")


@app.get("/api/search/q/{query}")
async def search_dramas(query: str):
    """Search for dramas by query."""
    try:
        logger.info(f"Searching for: {query}")
        return await scraper.search_dramas(query)
    except Exception as e:
        await handle_scraper_exception(e, "search_dramas", query)


@app.get("/api/id/{slug}")
async def get_drama_details(slug: str):
    """Get drama details by slug."""
    try:
        logger.info(f"Getting drama details for: {slug}")
        details = await scraper.get_drama_details(slug)
        return details
    except Exception as e:
        await handle_scraper_exception(e, "get_drama_details", slug)


@app.get("/api/id/{slug}/cast")
async def get_drama_cast(slug: str):
    """Get cast information for a drama."""
    try:
        logger.info(f"Getting cast for: {slug}")
        return await scraper.get_drama_cast(slug)
    except Exception as e:
        await handle_scraper_exception(e, "get_drama_cast", slug)


@app.get("/api/id/{slug}/episodes")
async def get_drama_episodes(slug: str):
    """Get episode details for a drama."""
    try:
        logger.info(f"Getting episodes for: {slug}")
        return await scraper.get_drama_episodes(slug)
    except Exception as e:
        await handle_scraper_exception(e, "get_drama_episodes", slug)


@app.get("/api/id/{slug}/reviews")
async def get_drama_reviews(slug: str):
    """Get reviews for a drama."""
    try:
        logger.info(f"Getting reviews for: {slug}")
        return await scraper.get_drama_reviews(slug)
    except Exception as e:
        await handle_scraper_exception(e, "get_drama_reviews", slug)


@app.get("/api/people/{people_id}")
async def get_person_details(people_id: str):
    """Get person details by ID."""
    try:
        logger.info(f"Getting person details for: {people_id}")
        return await scraper.get_person_details(people_id)
    except Exception as e:
        await handle_scraper_exception(e, "get_person_details", people_id)


@app.get("/api/seasonal/{year}/{quarter}")
async def get_seasonal_dramas(year: int, quarter: int):
    """Get seasonal dramas."""
    if quarter not in [1, 2, 3, 4]:
        raise HTTPException(
            status_code=400,
            detail={"code": 400, "error": True, "description": "Quarter must be 1, 2, 3, or 4"}
        )
    try:
        logger.info(f"Getting seasonal dramas for: {year} Q{quarter}")
        return await scraper.get_seasonal_dramas(year, quarter)
    except Exception as e:
        await handle_scraper_exception(e, "get_seasonal_dramas", f"{year}-Q{quarter}")


@app.get("/api/list/{list_id}")
async def get_drama_list(list_id: str):
    """Get a specific drama list by ID."""
    try:
        logger.info(f"Getting drama list: {list_id}")
        return await scraper.get_drama_list(list_id)
    except Exception as e:
        await handle_scraper_exception(e, "get_drama_list", list_id)


@app.get("/api/dramalist/{user_id}")
async def get_user_drama_list(user_id: str):
    """Get a user's drama list by user ID."""
    try:
        logger.info(f"Getting user drama list for: {user_id}")
        return await scraper.get_user_drama_list(user_id)
    except Exception as e:
        await handle_scraper_exception(e, "get_user_drama_list", user_id)


@app.get("/api/health")
async def health_check():
    """Health check endpoint to verify API status."""
    return {"status": "healthy", "message": "MyDramaList Scraper API (Optimized) is running"}

if __name__ == "__main__":
    import uvicorn
    # This block is for local development
    uvicorn.run(app, host="0.0.0.0", port=8000)
