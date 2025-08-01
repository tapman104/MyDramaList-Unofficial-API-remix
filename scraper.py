# scraper.py (Corrected)

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

# --- Optimized Scraper Class (with corrected logic) ---

class OptimizedMyDramaListScraper:
    def __init__(self, client: httpx.AsyncClient, limiter: AsyncLimiter):
        """
        Initializes the scraper with a shared httpx client and an async rate limiter.
        """
        self.base_url = "https://mydramalist.com"
        self.client = client
        self.limiter = limiter

    @retry(
        wait=wait_exponential(min=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
        reraise=True
    )
    async def _make_request(self, url: str) -> HTMLParser:
        """
        Makes a rate-limited, retry-enabled async HTTP request and parses the HTML.
        """
        async with self.limiter:
            try:
                response = await self.client.get(url)
                response.raise_for_status()
                
                text_content = response.text.lower()
                if "this list is private" in text_content or \
                   "this user's list is private" in text_content or \
                   "this resource is private" in text_content:
                    raise ScraperError("This resource is private or not found.", status_code=404)
                
                if "page not found" in text_content and "404" in text_content:
                    raise ScraperError("404 Not Found.", status_code=404)

                return HTMLParser(response.content)
            
            except httpx.HTTPStatusError as e:
                logger.warning(f"Request to {url} failed with status {e.response.status_code}. Retrying...")
                if e.response.status_code == 429:
                    raise ScraperError(f"Rate limited by remote server on {url}", status_code=429) from e
                elif e.response.status_code == 404:
                    raise ScraperError("404 Not Found.", status_code=404) from e
                raise
            except httpx.RequestError as e:
                logger.error(f"Request failed for {url}: {str(e)}")
                raise ScraperError(f"Network error accessing {url}: {e}", status_code=502) from e

    def _get_text(self, node: Optional[Node], selector: str, default: str = "") -> str:
        element = node.css_first(selector) if node else None
        return element.text(strip=True) if element else default
        
    def _get_attrib(self, node: Optional[Node], selector: str, attribute: str, default: str = "") -> str:
        element = node.css_first(selector) if node else None
        return element.attributes.get(attribute, default) if element else default
    
    # CORRECTED: Helper function to robustly find sidebar details
    def _find_detail_by_key(self, tree: HTMLParser, key: str) -> str:
        """Finds a detail value from the sidebar list based on its key (e.g., 'Episodes:')."""
        for item in tree.css("div.box-body > ul.list > li"):
            b_tag = item.css_first('b')
            if b_tag and key in b_tag.text():
                return item.text(strip=True).replace(key, '').strip()
        return 'N/A'

    # --- API Method Implementations (with corrected logic) ---

    async def search_dramas(self, query: str) -> Dict[str, Any]:
        search_url = f"{self.base_url}/search?q={query}"
        tree = await self._make_request(search_url)
        results = []
        
        for item in tree.css('div.box')[:20]:
            title_node = item.css_first('h6.title > a')
            if not title_node:
                continue

            link = title_node.attributes.get('href', '')
            year_text = self._get_text(item, 'span.text-muted')
            year_match = re.search(r'(\d{4})', year_text)
            
            results.append({
                'title': title_node.text(strip=True),
                'slug': link.split('/')[-1] if link else '',
                'year': year_match.group(1) if year_match else '',
                'image': self._get_attrib(item, 'img.lazy', 'data-src') or self._get_attrib(item, 'img', 'src'),
                'rating': self._get_text(item, 'span.score'),
                'url': f"{self.base_url}{link}" if link else ''
            })
        return {"results": results, "total": len(results)}

    async def get_drama_details(self, slug: str) -> Dict[str, Any]:
        """Get drama details by slug. (Corrected Logic)"""
        drama_url = f"{self.base_url}/{slug}"
        tree = await self._make_request(drama_url)

        synopsis_node = tree.css_first('div.show-synopsis > p, div.show-synopsis')
        rating_text = self._get_text(tree, 'div.hfs > b')
        
        # CORRECTED: Robustly find "Also Known As" without causing an error if it's not present.
        alt_titles_text = self._find_detail_by_key(tree, "Also Known As:")
        
        return {
            'title': self._get_text(tree, 'h1.film-title'),
            'slug': slug,
            'synopsis': synopsis_node.text(strip=True) if synopsis_node else "Not available.",
            'rating': rating_text.split('/')[0].strip() if rating_text else "",
            'episodes': self._find_detail_by_key(tree, "Episodes:"),
            'duration': self._find_detail_by_key(tree, "Duration:"),
            'genres': [g.text(strip=True) for g in tree.css('li.show-genres a')],
            'tags': [t.text(strip=True) for t in tree.css('li.show-tags a')],
            'image': self._get_attrib(tree, 'div.film-cover img', 'src'),
            'alternative_titles': [s.strip() for s in alt_titles_text.split(',') if s.strip()] if alt_titles_text != 'N/A' else [],
            'url': drama_url
        }

    async def get_drama_cast(self, slug: str) -> Dict[str, Any]:
        """Get cast information for a drama. (Corrected Logic)"""
        cast_url = f"{self.base_url}/{slug}/cast"
        tree = await self._make_request(cast_url)
        cast_by_role = {}
        
        # CORRECTED: A more robust way to iterate through roles and their associated actor lists.
        # This finds a role header, then grabs the UL that immediately follows it.
        role_headers = tree.css('div.box.clear h3.header')

        for header in role_headers:
            role_name = header.text(strip=True)
            cast_list_node = header.next
            
            # Ensure the next element is a UL with the class 'list'
            if not (cast_list_node and cast_list_node.tag == 'ul' and 'list' in cast_list_node.class_name):
                continue
            
            cast_list = []
            for item in cast_list_node.css('li.list-item'):
                name_node = item.css_first('a.text-primary > b')
                if not name_node:
                    continue
                
                profile_node = item.css_first('a.text-primary')
                profile_url = profile_node.attributes.get('href', '') if profile_node else ''

                cast_list.append({
                    'name': name_node.text(strip=True),
                    'character': self._get_text(item, 'small.text-muted'),
                    'image': self._get_attrib(item, 'img', 'src') or self._get_attrib(item, 'img', 'data-src'),
                    'profile_url': f"{self.base_url}{profile_url}" if profile_url else ''
                })
            
            if cast_list:
                cast_by_role[role_name] = cast_list
                    
        total_cast = sum(len(v) for v in cast_by_role.values())
        return {'cast': cast_by_role, 'total': total_cast}

    # --- Unchanged Methods (no reported issues, confirmed logic is stable) ---
    async def get_drama_episodes(self, slug: str) -> Dict[str, Any]:
        episodes_url = f"{self.base_url}/{slug}/episodes"
        tree = await self._make_request(episodes_url)
        episodes = []
        
        for item in tree.css('div.episode'):
            full_title = self._get_text(item, 'h2.title > a')
            episode_num_match = re.search(r'Episode\s+(\d+)', full_title)
            episodes.append({
                'episode_number': episode_num_match.group(1) if episode_num_match else '',
                'title': full_title,
                'air_date': self._get_text(item, 'div.air-date')
            })

        return {'episodes': episodes, 'total': len(episodes)}

    async def get_drama_reviews(self, slug: str) -> Dict[str, Any]:
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
        seasons = {1: 'winter', 2: 'spring', 3: 'summer', 4: 'fall'}
        season = seasons.get(quarter, 'winter')
        seasonal_url = f"{self.base_url}/shows/top?year={year}&season={season}"
        tree = await self._make_request(seasonal_url)
        
        dramas = []
        for item in tree.css('div.box')[:20]:
            title_node = item.css_first('h6 > a')
            if not title_node: continue
            
            link = title_node.attributes.get('href', '')
            dramas.append({
                'title': title_node.text(strip=True),
                'slug': link.split('/')[-1] if link else '',
                'image': self._get_attrib(item, 'img.lazy', 'data-src') or self._get_attrib(item, 'img', 'src'),
                'rating': self._get_text(item, 'span.score'),
                'url': f"{self.base_url}{link}" if link else ''
            })

        return {"dramas": dramas, "total": len(dramas), "year": year, "quarter": quarter, "season": season}

    async def get_drama_list(self, list_id: str) -> Optional[Dict[str, Any]]:
        list_url = f"{self.base_url}/list/{list_id}"
        tree = await self._make_request(list_url)
        
        dramas = []
        for item in tree.css('ul.list-group li.list-group-item'):
            title_node = item.css_first('h2.title > a')
            if not title_node: continue
            
            link = title_node.attributes.get('href', '')
            dramas.append({
                'title': title_node.text(strip=True),
                'slug': link.split('/')[-1] if link else '',
                'image': self._get_attrib(item, 'img.lazy', 'data-src') or self._get_attrib(item, 'img', 'src'),
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
                    'image': '',
                    'url': f"{self.base_url}{link}" if link else ''
                })
        
        return {
            'username': self._get_text(tree, 'h1.mdl-style-header a', user_id),
            'user_id': user_id,
            'dramas': dramas,
            'total': len(dramas),
            'url': user_list_url
        }
