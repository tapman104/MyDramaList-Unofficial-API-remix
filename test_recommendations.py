import asyncio
import json
from scraper import MyDramaListScraper

async def test_recs():
    scraper = MyDramaListScraper()
    # Using Vincenzo (61371-vincenzo) as it has many recommendations for pagination testing
    slug = "61371-vincenzo"
    print(f"Testing recommendations for: {slug}")
    
    results = await scraper.get_drama_recommendations(slug)
    
    if results:
        print(f"Total recommendations found: {results['total']}")
        print(f"Pages fetched: {results.get('pages_fetched', 'N/A')}")
        
        if results['recommendations']:
            first = results['recommendations'][0]
            print("\nFirst Recommendation Sample:")
            print(f"Title: {first['title']} ({first['year']})")
            print(f"Slug: {first['slug']}")
            print(f"Votes: {first['votes']}")
            print(f"Recommended by: {first['recommended_by']}")
            print(f"Reasons count: {len(first['reasons'])}")
            if first['reasons']:
                print(f"First Reason: {first['reasons'][0]}")
    else:
        print("No results returned or error occurred.")

if __name__ == "__main__":
    asyncio.run(test_recs())
