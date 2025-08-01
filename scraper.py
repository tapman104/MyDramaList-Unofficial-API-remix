# scraper.py

import logging
import re
from typing import Any, Dict, List, Optional
import httpx
from aiolimiter import AsyncLimiter
from selectolax.parser import HTMLParser, Node
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)

# --- Custom Exception for Scraper ---

class ScraperError(Exception):
    """Custom exception for scraper-specific errors."""
    def __init__(self, message, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

# --- Optimized Scraper Class ---

class OptimizedMyDramaListScraper:
    def __init__(self, client: httpx.AsyncClient, limiter: AsyncLimiter):
        """
        Initializes the scraper with a shared httpx client and an async rate limiter.

        Args:
            client (httpx.AsyncClient): An asynchronous HTTP client.
            limiter (AsyncLimiter): An asynchronous rate limiter.
        """
        self.base_url = "https://mydramalist.com"
        self.client = client
        self.limiter = limiter

    @retry(
        wait=wait_exponential(min=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
        reraise=True  # Reraise the exception if all retries fail
    )
    async def _make_request(self, url: str) -> HTMLParser:
        """
        Makes a rate-limited, retry-enabled async HTTP request and parses the HTML.
        This function will automatically retry on transient errors like 429 or timeouts.
        """
        async with self.limiter:
            try:
                response = await self.client.get(url)
                # Raise an exception for 4xx/5xx status codes, which tenacity will catch
                response.raise_for_status()
                
                # Check for "private" or "not found" pages early
                text_content = response.text.lower()
                if "this list is private" in text_content or \
                   "this user's list is private" in text_content or \
                   "this resource is private" in text_content:
                    raise ScraperError("This resource is private.", status_code=404)
                
                if "404 not found" in text_content or "page not found" in text_content:
                    raise ScraperError("404 Not Found.", status_code=404)

                return HTMLParser(response.content)
            
            except httpx.HTTPStatusError as e:
                logger.warning(f"Request to {url} failed with status {e.response.status_code}. Retrying...")
                # Special handling for rate limiting (429) vs. other errors
                if e.response.status_code == 429:
                    raise ScraperError(f"Rate limited by remote server on {url}", status_code=429) from e
                elif e.response.status_code == 404:
                    raise ScraperError("404 Not Found.", status_code=404) from e
                raise  # Re-raise to trigger tenacity retry
            except httpx.RequestError as e:
                logger.error(f"Request failed for {url}: {str(e)}")
                raise ScraperError(f"Network error accessing {url}: {e}", status_code=502) from e

    # --- Helper function for safe data extraction ---
    
    def _get_text(self, node: Optional[Node], selector: str, default: str = "") -> str:
        """Safely get text from a sub-node."""
        if node:
            element = node.css_first(selector)
            return element.text(strip=True) if element else default
        return default
        
    def _get_attrib(self, node: Optional[Node], selector: str, attribute: str, default: str = "") -> str:
        """Safely get an attribute from a sub-node."""
        if node:
            element = node.css_first(selector)
            return element.attributes.get(attribute, default) if element else default
        return default

    # --- API Method Implementations ---

    async def search_dramas(self, query: str) -> Dict[str, Any]:
        """Search for dramas by query."""
        search_url = f"{self.base_url}/search?q={query}"
        tree = await self._make_request(search_url)
        results = []
        drama_items = tree.css('div.box')

        for item in drama_items[:20]:
            title_node = item.css_first('h6.title > a')
            if not title_node:
                continue

            link = title_node.attributes.get('href', '')
            image_node = item.css_first('img.lazy')

            results.append({
                'title': title_node.text(strip=True),
                'slug': link.split('/')[-1] if link else '',
                'year': self._get_text(item, 'span.text-muted', '').split(', ')[-1],
                'image': image_node.attributes.get('data-src') if image_node else self._get_attrib(item, 'img', 'src'),
                'rating': self._get_text(item, 'span.score'),
                'url': f"{self.base_url}{link}" if link else ''
            })
        return {"results": results, "total": len(results)}

    async def get_drama_details(self, slug: str) -> Dict[str, Any]:
        """Get drama details by slug."""
        drama_url = f"{self.base_url}/{slug}"
        tree = await self._make_request(drama_url)

        synopsis_node = tree.css_first('div.show-synopsis > p')
        rating_text = self._get_text(tree, 'div.hfs > b')
        
        alt_titles_li = next((n for n in tree.css('ul.list.m-b-0 > li.list-item') if "Also Known As:" in n.text()), None)
        genres = [g.text(strip=True) for g in tree.css('li.show-genres a')]
        tags = [t.text(strip=True) for t in tree.css('li.show-tags a')]
        
        # Details are in a list, so we iterate to find them
        details_map = {li.css_first('b').text(strip=True): li.text(strip=True) for li in tree.css('div.box-body > ul.list > li') if li.css_first('b')}
        
        return {
            'title': self._get_text(tree, 'h1.film-title'),
            'slug': slug,
            'synopsis': synopsis_node.text(strip=True) if synopsis_node else "Not available.",
            'rating': rating_text.split('/')[0].strip() if rating_text else "",
            'episodes': details_map.get('Episodes:', '').replace('Episodes:', '').strip() or 'N/A',
            'duration': details_map.get('Duration:', '').replace('Duration:', '').strip() or 'N/A',
            'genres': genres,
            'tags': tags,
            'image': self._get_attrib(tree, 'div.film-cover img', 'src'),
            'alternative_titles': [s.strip() for s in alt_titles_li.text(strip=True).replace("Also Known As:", "").split(',') if s.strip()] if alt_titles_li else [],
            'url': drama_url
        }

    async def get_drama_cast(self, slug: str) -> Dict[str, Any]:
        """Get cast information for a drama."""
        cast_url = f"{self.base_url}/{slug}/cast"
        tree = await self._make_request(cast_url)
        cast_by_role = {}
        content_box = tree.css_first('div.box.clear')
        
        if not content_box:
            return {'cast': {}, 'total': 0}
            
        current_role = "Unknown"
        for element in content_box.children:
            if element.tag == 'h3' and 'header' in element.attributes.get('class', ''):
                current_role = element.text(strip=True)
                cast_by_role[current_role] = []
            elif element.tag == 'ul' and 'list' in element.attributes.get('class', ''):
                if current_role not in cast_by_role:
                    continue # Should not happen if page is structured correctly
                
                for item in element.css('li.list-item'):
                    name_node = item.css_first('a.text-primary')
                    if not name_node: continue
                    
                    profile_url = name_node.attributes.get('href', '')
                    img_node = item.css_first('img')
                    
                    cast_by_role[current_role].append({
                        'name': self._get_text(name_node, 'b'),
                        'character': self._get_text(item, 'div > small'),
                        'image': img_node.attributes.get('data-src') or img_node.attributes.get('src') if img_node else '',
                        'profile_url': f"{self.base_url}{profile_url}" if profile_url else ''
                    })
                    
        total_cast = sum(len(v) for v in cast_by_role.values())
        return {'cast': cast_by_role, 'total': total_cast}

    async def get_drama_episodes(self, slug: str) -> Dict[str, Any]:
        """Get episode details for a drama."""
        episodes_url = f"{self.base_url}/{slug}/episodes"
        tree = await self._make_request(episodes_url)
        episodes = []
        episode_items = tree.css('div.episode')

        for item in episode_items:
            full_title = self._get_text(item, 'h2.title > a')
            episode_num_match = re.search(r'Episode\s+(\d+)', full_title)
            episodes.append({
                'episode_number': episode_num_match.group(1) if episode_num_match else '',
                'title': full_title,
                'air_date': self._get_text(item, 'div.air-date')
            })

        return {'episodes': episodes, 'total': len(episodes)}

    async def get_drama_reviews(self, slug: str) -> Dict[str, Any]:
        """Get reviews for a drama."""
        reviews_url = f"{self.base_url}/{slug}/reviews"
        tree = await self._make_request(reviews_url)
        reviews = []
        
        for item in tree.css('div.review')[:10]:
            reviews.append({
                'author': self._get_text(item, 'a.text-primary'),
                'rating': self._get_text(item, 'span.score'),
                'content': self._get_text(item, 'div.review-body'),
                'date': self._get_text(item, 'small.datetime'),
            })

        return {'reviews': reviews, 'total': len(reviews)}

    async def get_person_details(self, people_id: str) -> Dict[str, Any]:
        """Get person details by ID."""
        person_url = f"{self.base_url}/people/{people_id}"
        tree = await self._make_request(person_url)
        info = {}

        for item in tree.css("div.box.clear div.box-body ul.list li.list-item"):
            text_content = item.text(strip=True)
            if ':' in text_content:
                key, value = text_content.split(':', 1)
                info[key.strip()] = value.strip()
        
        return {
            'name': self._get_text(tree, 'h1.film-title'),
            'id': people_id,
            'image': self._get_attrib(tree, "div.content-side .box-body img.img-responsive", 'src'),
            'info': info,
            'url': person_url
        }

    async def get_seasonal_dramas(self, year: int, quarter: int) -> Dict[str, Any]:
        """Get seasonal dramas."""
        seasons = {1: 'winter', 2: 'spring', 3: 'summer', 4: 'fall'}
        season = seasons.get(quarter, 'winter')
        seasonal_url = f"{self.base_url}/shows/top?year={year}&season={season}"
        tree = await self._make_request(seasonal_url)
        
        dramas = []
        for item in tree.css('div.box')[:20]:
            title_node = item.css_first('h6 > a')
            if not title_node: continue
            
            link = title_node.attributes.get('href', '')
            image_node = item.css_first('img.lazy')
            dramas.append({
                'title': title_node.text(strip=True),
                'slug': link.split('/')[-1] if link else '',
                'image': image_node.attributes.get('data-src') if image_node else '',
                'rating': self._get_text(item, 'span.score'),
                'url': f"{self.base_url}{link}" if link else ''
            })

        return {"dramas": dramas, "total": len(dramas), "year": year, "quarter": quarter, "season": season}

    async def get_drama_list(self, list_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific drama list by ID."""
        list_url = f"{self.base_url}/list/{list_id}"
        tree = await self._make_request(list_url)
        
        dramas = []
        for item in tree.css('ul.list-group li.list-group-item'):
            title_node = item.css_first('h2.title > a')
            if not title_node: continue
            
            link = title_node.attributes.get('href', '')
            img_node = item.css_first('img.lazy')

            dramas.append({
                'title': title_node.text(strip=True),
                'slug': link.split('/')[-1] if link else '',
                'image': img_node.attributes.get('data-src') or img_node.attributes.get('src') if img_node else '',
                'url': f"{self.base_url}{link}" if link else ''
            })

        return {
            'title': self._get_text(tree, 'h1'),
            'description': self._get_text(tree, 'div.box-header .description'),
            'dramas': dramas,
            'total': len(dramas),
            'url': list_url
        }

    async def get_user_drama_list(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user's drama list by user ID."""
        user_list_url = f"{self.base_url}/dramalist/{user_id}"
        tree = await self._make_request(user_list_url)
        
        dramas = []
        for section in tree.css('div.mdl-style-list'):
            status = self._get_text(section, 'h3.mdl-style-list-label', 'Unknown')
            for row in section.css('table > tbody > tr'):
                title_node = row.css_first('a.title')
                if not title_node: continue
                
                link = title_node.attributes.get('href', '')
                dramas.append({
                    'title': title_node.text(strip=True),
                    'slug': link.split('/')[-1] if link else '',
                    'status': status,
                    'rating': self._get_text(row, 'td.mdl-style-col-score .score'),
                    'image': '', # Images are not available in this view
                    'url': f"{self.base_url}{link}" if link else ''
                })
        
        return {
            'username': self._get_text(tree, 'h1.mdl-style-header a', user_id),
            'user_id': user_id,
            'dramas': dramas,
            'total': len(dramas),
            'url': user_list_url
        }
