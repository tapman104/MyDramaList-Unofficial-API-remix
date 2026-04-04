from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import logging
import asyncio
from scraper import MyDramaListScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MyDramaList Scraper API",
    description="A serverless API for scraping MyDramaList.com data",
    version="1.0.0"
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

@app.get("/api/search/q/{query}")
async def search_dramas(query: str):
    """Search for dramas by query"""
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

@app.get("/api/id/{slug}")
async def get_drama_details(slug: str):
    """Get drama details by slug"""
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

@app.get("/api/id/{slug}/cast")
async def get_drama_cast(slug: str):
    """Get cast information for a drama"""
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

@app.get("/api/id/{slug}/episodes")
async def get_drama_episodes(slug: str):
    """Get episode details for a drama"""
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

@app.get("/api/id/{slug}/reviews")
async def get_drama_reviews(slug: str):
    """Get reviews for a drama"""
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

@app.get("/api/id/{slug}/recs")
async def get_drama_recommendations(slug: str):
    """Get drama recommendations for a drama"""
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

@app.get("/api/people/{people_id}")
async def get_person_details(people_id: str):
    """Get person details by ID"""
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

@app.get("/api/seasonal/{year}/{quarter}")
async def get_seasonal_dramas(year: int, quarter: int):
    """Get seasonal dramas"""
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

@app.get("/api/list/{list_id}")
async def get_drama_list(list_id: str):
    """Get a specific drama list by ID"""
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

@app.get("/api/dramalist/{user_id}")
async def get_user_drama_list(user_id: str):
    """Get a user's drama list by user ID"""
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
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "MyDramaList Scraper API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
