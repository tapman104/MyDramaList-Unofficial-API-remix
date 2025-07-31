import requests
from bs4 import BeautifulSoup
import logging
import asyncio
from typing import Dict, List, Optional, Any
import re

logger = logging.getLogger(__name__)

class MyDramaListScraper:
    def __init__(self):
        self.base_url = "https://mydramalist.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _make_request(self, url: str) -> Optional[BeautifulSoup]:
        """Make HTTP request and return BeautifulSoup object"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {str(e)}")
            return None

    async def search_dramas(self, query: str) -> Dict[str, Any]:
        """Search for dramas by query"""
        search_url = f"{self.base_url}/search?q={query}"
        soup = self._make_request(search_url)
        
        if not soup:
            return {"results": [], "total": 0}

        results = []
        drama_items = soup.find_all('div', class_='box')
        
        for item in drama_items[:20]:  # Limit to 20 results
            try:
                title_elem = item.find('h6') or item.find('a', class_='title')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                link = title_elem.find('a')['href'] if title_elem.find('a') else ''
                slug = link.split('/')[-1] if link else ''
                
                year_elem = item.find('span', class_='year')
                year = year_elem.get_text(strip=True) if year_elem else ''
                
                img_elem = item.find('img')
                image = img_elem['src'] if img_elem else ''
                
                rating_elem = item.find('span', class_='score')
                rating = rating_elem.get_text(strip=True) if rating_elem else ''
                
                results.append({
                    'title': title,
                    'slug': slug,
                    'year': year,
                    'image': image,
                    'rating': rating,
                    'url': f"{self.base_url}{link}" if link else ''
                })
            except Exception as e:
                logger.error(f"Error parsing search result: {str(e)}")
                continue

        return {"results": results, "total": len(results)}

    async def get_drama_details(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get drama details by slug"""
        drama_url = f"{self.base_url}/{slug}"
        soup = self._make_request(drama_url)
        
        if not soup:
            return None

        try:
            # Basic info
            title_elem = soup.find('h1', class_='film-title')
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            # Alternative titles
            alt_titles = []
            alt_title_elems = soup.find_all('b', string=re.compile(r'Also Known As|Native Title'))
            for elem in alt_title_elems:
                if elem.parent:
                    alt_titles.append(elem.parent.get_text(strip=True))
            
            # Synopsis
            synopsis_elem = soup.find('div', class_='show-synopsis')
            synopsis = synopsis_elem.get_text(strip=True) if synopsis_elem else ''
            
            # Rating
            rating_elem = soup.find('div', class_='hfs')
            rating = rating_elem.get_text(strip=True) if rating_elem else ''
            
            # Episodes
            episodes_elem = soup.find('b', string='Episodes:')
            episodes = episodes_elem.parent.get_text(strip=True).replace('Episodes:', '').strip() if episodes_elem and episodes_elem.parent else ''
            
            # Duration
            duration_elem = soup.find('b', string='Duration:')
            duration = duration_elem.parent.get_text(strip=True).replace('Duration:', '').strip() if duration_elem and duration_elem.parent else ''
            
            # Genres
            genres = []
            genre_elems = soup.find_all('a', href=re.compile(r'/genre/'))
            for genre in genre_elems:
                genres.append(genre.get_text(strip=True))
            
            # Tags
            tags = []
            tag_elems = soup.find_all('a', href=re.compile(r'/tag/'))
            for tag in tag_elems:
                tags.append(tag.get_text(strip=True))
            
            # Image
            img_elem = soup.find('img', class_='img-responsive')
            image = img_elem['src'] if img_elem else ''
            
            return {
                'title': title,
                'slug': slug,
                'synopsis': synopsis,
                'rating': rating,
                'episodes': episodes,
                'duration': duration,
                'genres': genres,
                'tags': tags,
                'image': image,
                'alternative_titles': alt_titles,
                'url': drama_url
            }
        except Exception as e:
            logger.error(f"Error parsing drama details: {str(e)}")
            return None

    async def get_drama_cast(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get cast information for a drama"""
        cast_url = f"{self.base_url}/{slug}/cast"
        soup = self._make_request(cast_url)
        
        if not soup:
            return None

        try:
            cast_members = []
            cast_items = soup.find_all('div', class_='col-sm-4')
            
            for item in cast_items:
                try:
                    name_elem = item.find('a', class_='text-primary')
                    if not name_elem:
                        continue
                    
                    name = name_elem.get_text(strip=True)
                    profile_url = name_elem['href'] if 'href' in name_elem.attrs else ''
                    
                    role_elem = item.find('small')
                    role = role_elem.get_text(strip=True) if role_elem else ''
                    
                    img_elem = item.find('img')
                    image = img_elem['src'] if img_elem else ''
                    
                    cast_members.append({
                        'name': name,
                        'role': role,
                        'image': image,
                        'profile_url': f"{self.base_url}{profile_url}" if profile_url else ''
                    })
                except Exception as e:
                    logger.error(f"Error parsing cast member: {str(e)}")
                    continue

            return {'cast': cast_members, 'total': len(cast_members)}
        except Exception as e:
            logger.error(f"Error parsing cast: {str(e)}")
            return None

    async def get_drama_episodes(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get episode details for a drama"""
        episodes_url = f"{self.base_url}/{slug}/episodes"
        soup = self._make_request(episodes_url)
        
        if not soup:
            return None

        try:
            episodes = []
            episode_items = soup.find_all('div', class_='episode')
            
            for item in episode_items:
                try:
                    episode_num_elem = item.find('span', class_='episode-number')
                    episode_num = episode_num_elem.get_text(strip=True) if episode_num_elem else ''
                    
                    title_elem = item.find('a', class_='episode-title')
                    title = title_elem.get_text(strip=True) if title_elem else ''
                    
                    air_date_elem = item.find('span', class_='air-date')
                    air_date = air_date_elem.get_text(strip=True) if air_date_elem else ''
                    
                    episodes.append({
                        'episode_number': episode_num,
                        'title': title,
                        'air_date': air_date
                    })
                except Exception as e:
                    logger.error(f"Error parsing episode: {str(e)}")
                    continue

            return {'episodes': episodes, 'total': len(episodes)}
        except Exception as e:
            logger.error(f"Error parsing episodes: {str(e)}")
            return None

    async def get_drama_reviews(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get reviews for a drama"""
        reviews_url = f"{self.base_url}/{slug}/reviews"
        soup = self._make_request(reviews_url)
        
        if not soup:
            return None

        try:
            reviews = []
            review_items = soup.find_all('div', class_='review')
            
            for item in review_items[:10]:  # Limit to 10 reviews
                try:
                    author_elem = item.find('a', class_='username')
                    author = author_elem.get_text(strip=True) if author_elem else ''
                    
                    rating_elem = item.find('span', class_='score')
                    rating = rating_elem.get_text(strip=True) if rating_elem else ''
                    
                    content_elem = item.find('div', class_='review-content')
                    content = content_elem.get_text(strip=True) if content_elem else ''
                    
                    date_elem = item.find('span', class_='review-date')
                    date = date_elem.get_text(strip=True) if date_elem else ''
                    
                    reviews.append({
                        'author': author,
                        'rating': rating,
                        'content': content[:500] + '...' if len(content) > 500 else content,
                        'date': date
                    })
                except Exception as e:
                    logger.error(f"Error parsing review: {str(e)}")
                    continue

            return {'reviews': reviews, 'total': len(reviews)}
        except Exception as e:
            logger.error(f"Error parsing reviews: {str(e)}")
            return None

    async def get_person_details(self, people_id: str) -> Optional[Dict[str, Any]]:
        """Get person details by ID"""
        person_url = f"{self.base_url}/people/{people_id}"
        soup = self._make_request(person_url)
        
        if not soup:
            return None

        try:
            name_elem = soup.find('h1', class_='film-title')
            name = name_elem.get_text(strip=True) if name_elem else ''
            
            # Basic info
            info_items = soup.find_all('b')
            info = {}
            for item in info_items:
                if item.parent:
                    text = item.parent.get_text(strip=True)
                    if ':' in text:
                        key, value = text.split(':', 1)
                        info[key.strip()] = value.strip()
            
            # Image
            img_elem = soup.find('img', class_='img-responsive')
            image = img_elem['src'] if img_elem else ''
            
            return {
                'name': name,
                'id': people_id,
                'image': image,
                'info': info,
                'url': person_url
            }
        except Exception as e:
            logger.error(f"Error parsing person details: {str(e)}")
            return None

    async def get_seasonal_dramas(self, year: int, quarter: int) -> Dict[str, Any]:
        """Get seasonal dramas"""
        # Map quarter to season
        seasons = {1: 'winter', 2: 'spring', 3: 'summer', 4: 'fall'}
        season = seasons.get(quarter, 'winter')
        
        seasonal_url = f"{self.base_url}/shows/top?year={year}&season={season}"
        soup = self._make_request(seasonal_url)
        
        if not soup:
            return {"dramas": [], "total": 0, "year": year, "quarter": quarter}

        try:
            dramas = []
            drama_items = soup.find_all('div', class_='box')
            
            for item in drama_items[:20]:  # Limit to 20 results
                try:
                    title_elem = item.find('h6') or item.find('a', class_='title')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    link = title_elem.find('a')['href'] if title_elem.find('a') else ''
                    slug = link.split('/')[-1] if link else ''
                    
                    img_elem = item.find('img')
                    image = img_elem['src'] if img_elem else ''
                    
                    rating_elem = item.find('span', class_='score')
                    rating = rating_elem.get_text(strip=True) if rating_elem else ''
                    
                    dramas.append({
                        'title': title,
                        'slug': slug,
                        'image': image,
                        'rating': rating,
                        'url': f"{self.base_url}{link}" if link else ''
                    })
                except Exception as e:
                    logger.error(f"Error parsing seasonal drama: {str(e)}")
                    continue

            return {
                "dramas": dramas,
                "total": len(dramas),
                "year": year,
                "quarter": quarter,
                "season": season
            }
        except Exception as e:
            logger.error(f"Error parsing seasonal dramas: {str(e)}")
            return {"dramas": [], "total": 0, "year": year, "quarter": quarter}

    async def get_drama_list(self, list_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific drama list by ID"""
        list_url = f"{self.base_url}/list/{list_id}"
        soup = self._make_request(list_url)
        
        if not soup:
            return None

        try:
            # Check if list is private
            if soup.find(string=re.compile(r'private|Private')):
                raise Exception("This list is private")
            
            title_elem = soup.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            description_elem = soup.find('div', class_='list-description')
            description = description_elem.get_text(strip=True) if description_elem else ''
            
            dramas = []
            drama_items = soup.find_all('div', class_='list-item')
            
            for item in drama_items:
                try:
                    title_elem = item.find('a', class_='title')
                    if not title_elem:
                        continue
                    
                    drama_title = title_elem.get_text(strip=True)
                    link = title_elem['href'] if 'href' in title_elem.attrs else ''
                    slug = link.split('/')[-1] if link else ''
                    
                    img_elem = item.find('img')
                    image = img_elem['src'] if img_elem else ''
                    
                    dramas.append({
                        'title': drama_title,
                        'slug': slug,
                        'image': image,
                        'url': f"{self.base_url}{link}" if link else ''
                    })
                except Exception as e:
                    logger.error(f"Error parsing list item: {str(e)}")
                    continue

            return {
                'title': title,
                'description': description,
                'dramas': dramas,
                'total': len(dramas),
                'url': list_url
            }
        except Exception as e:
            logger.error(f"Error parsing drama list: {str(e)}")
            if "private" in str(e).lower():
                raise e
            return None

    async def get_user_drama_list(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user's drama list by user ID"""
        user_list_url = f"{self.base_url}/dramalist/{user_id}"
        soup = self._make_request(user_list_url)
        
        if not soup:
            return None

        try:
            # Check if list is private
            if soup.find(string=re.compile(r'private|Private')):
                raise Exception("This list is private")
            
            username_elem = soup.find('h1') or soup.find('span', class_='username')
            username = username_elem.get_text(strip=True) if username_elem else user_id
            
            dramas = []
            drama_items = soup.find_all('div', class_='list-item')
            
            for item in drama_items[:50]:  # Limit to 50 items
                try:
                    title_elem = item.find('a', class_='title')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    link = title_elem['href'] if 'href' in title_elem.attrs else ''
                    slug = link.split('/')[-1] if link else ''
                    
                    status_elem = item.find('span', class_='status')
                    status = status_elem.get_text(strip=True) if status_elem else ''
                    
                    rating_elem = item.find('span', class_='score')
                    rating = rating_elem.get_text(strip=True) if rating_elem else ''
                    
                    img_elem = item.find('img')
                    image = img_elem['src'] if img_elem else ''
                    
                    dramas.append({
                        'title': title,
                        'slug': slug,
                        'status': status,
                        'rating': rating,
                        'image': image,
                        'url': f"{self.base_url}{link}" if link else ''
                    })
                except Exception as e:
                    logger.error(f"Error parsing user list item: {str(e)}")
                    continue

            return {
                'username': username,
                'user_id': user_id,
                'dramas': dramas,
                'total': len(dramas),
                'url': user_list_url
            }
        except Exception as e:
            logger.error(f"Error parsing user drama list: {str(e)}")
            if "private" in str(e).lower():
                raise e
            return None
