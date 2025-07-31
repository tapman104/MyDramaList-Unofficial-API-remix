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
        # Find all boxes, but we will filter for only drama/movie results
        drama_items = soup.find_all('div', class_='box')
        
        for item in drama_items[:20]:  # Limit to 20 results
            try:
                # Dramas/movies have a title h6 with a link inside
                title_elem = item.find('h6', class_='title')
                if not title_elem or not title_elem.find('a'):
                    continue
                
                title = title_elem.get_text(strip=True)
                link = title_elem.find('a')['href']
                slug = link.split('/')[-1] if link else ''
                
                # Year is inside a 'text-muted' span
                year_elem = item.find('span', class_='text-muted')
                year_match = re.search(r'(\d{4})', year_elem.get_text(strip=True)) if year_elem else None
                year = year_match.group(1) if year_match else ''
                
                # Image is lazy-loaded, so we use 'data-src'
                img_elem = item.find('img', class_='lazy')
                image = img_elem['data-src'] if img_elem and 'data-src' in img_elem.attrs else (img_elem['src'] if img_elem else '')

                # Rating is in a span with class 'score'
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
                logger.error(f"Error parsing search result item: {str(e)}")
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
            alt_title_list_elem = soup.find('li', class_='list-item', string=re.compile(r'Also Known As:'))
            if alt_title_list_elem:
                alt_titles = [s.strip() for s in alt_title_list_elem.get_text().replace("Also Known As:", "").split(',') if s.strip()]

            # Synopsis
            synopsis_elem = soup.find('div', class_='show-synopsis')
            synopsis = synopsis_elem.find('p').get_text(strip=True) if synopsis_elem and synopsis_elem.find('p') else ''
            
            # Rating
            rating_elem = soup.find('div', class_='hfs')
            rating_text = rating_elem.find('b').get_text(strip=True) if rating_elem and rating_elem.find('b') else ''
            rating = rating_text.split('/')[0].strip()
            
            # Episodes
            episodes = ''
            details_box = soup.find('div', class_='box-body', string=lambda t: t and 'Episodes:' in t)
            if details_box:
                 ep_elem = details_box.find('li', string=re.compile('Episodes:'))
                 if ep_elem:
                     episodes = ep_elem.get_text(strip=True).replace('Episodes:', '').strip()

            # Duration
            duration = ''
            if details_box:
                dur_elem = details_box.find('li', string=re.compile('Duration:'))
                if dur_elem:
                    duration = dur_elem.get_text(strip=True).replace('Duration:', '').strip()

            # Genres
            genres_container = soup.find('li', class_='show-genres')
            genres = [g.get_text(strip=True) for g in genres_container.find_all('a')] if genres_container else []

            # Tags
            tags_container = soup.find('li', class_='show-tags')
            tags = [t.get_text(strip=True) for t in tags_container.find_all('a', href=re.compile(r'/search\?adv=titles&th='))] if tags_container else []

            # Image
            img_elem = soup.find('div', class_='film-cover').find('img')
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

        cast_by_role = {}
        try:
            # The page is structured by headers (h3) for roles
            role_headers = soup.find_all('h3', class_='header')
            for header in role_headers:
                role_name = header.get_text(strip=True)
                cast_list = []
                
                # The cast members are in a 'ul' that directly follows the 'h3' header
                cast_container = header.find_next_sibling('ul', class_='list')
                if not cast_container:
                    continue
                
                cast_items = cast_container.find_all('li', class_='list-item')
                for item in cast_items:
                    try:
                        name_elem = item.find('a', class_='text-primary')
                        if not name_elem:
                            continue
                        
                        name = name_elem.find('b').get_text(strip=True) if name_elem.find('b') else name_elem.get_text(strip=True)
                        profile_url = name_elem['href']

                        # The character role is in a small tag within a div that's a sibling of the name anchor
                        character_role = ''
                        role_div = name_elem.find_next_sibling('div')
                        if role_div and role_div.find('small'):
                            character_role = role_div.find('small').get_text(strip=True)
                        
                        img_elem = item.find('img')
                        image = img_elem.get('src') or img_elem.get('data-src')

                        cast_list.append({
                            'name': name,
                            'character': character_role,
                            'image': image,
                            'profile_url': f"{self.base_url}{profile_url}" if profile_url else ''
                        })
                    except Exception as e:
                        logger.error(f"Error parsing individual cast member: {str(e)}")
                        continue
                
                if cast_list:
                    cast_by_role[role_name] = cast_list

            total_cast = sum(len(v) for v in cast_by_role.values())
            return {'cast': cast_by_role, 'total': total_cast}
        except Exception as e:
            logger.error(f"Error parsing cast page: {str(e)}")
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
                    title_elem = item.find('h2', class_='title').find('a')
                    full_title = title_elem.get_text(strip=True)
                    
                    episode_num_match = re.search(r'Episode\s+(\d+)', full_title)
                    episode_num = episode_num_match.group(1) if episode_num_match else ''
                    
                    air_date_elem = item.find('div', class_='air-date')
                    air_date = air_date_elem.get_text(strip=True) if air_date_elem else ''
                    
                    episodes.append({
                        'episode_number': episode_num,
                        'title': full_title,
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
            
            for item in review_items[:10]:
                try:
                    author_elem = item.find('a', class_='text-primary')
                    author = author_elem.get_text(strip=True) if author_elem else ''
                    
                    rating_elem = item.find('span', class_='score')
                    rating = rating_elem.get_text(strip=True) if rating_elem else ''
                    
                    content_elem = item.find('div', class_='review-body')
                    content = content_elem.get_text(strip=True)
                    
                    date_elem = item.find('small', class_='datetime')
                    date = date_elem.get_text(strip=True) if date_elem else ''
                    
                    reviews.append({
                        'author': author,
                        'rating': rating,
                        'content': content,
                        'date': date
                    })
                except Exception as e:
                    logger.error(f"Error parsing review: {str(e)}")
                    continue

            return {'reviews': reviews, 'total': len(reviews)}
        except Exception as e:
            logger.error(f"Error parsing reviews: {str(e)}")
            return None

    # Other functions remain the same as they were not reported as broken
    async def get_person_details(self, people_id: str) -> Optional[Dict[str, Any]]:
        """Get person details by ID"""
        person_url = f"{self.base_url}/people/{people_id}"
        soup = self._make_request(person_url)
        
        if not soup:
            return None

        try:
            name_elem = soup.find('h1', class_='film-title')
            name = name_elem.get_text(strip=True) if name_elem else ''
            
            info = {}
            info_box = soup.find('div', class_='box-body')
            if info_box:
                info_items = info_box.find_all('li', class_='list-item')
                for item in info_items:
                    text = item.get_text(strip=True)
                    if ':' in text:
                        key, value = text.split(':', 1)
                        info[key.strip()] = value.strip()
            
            img_elem = soup.find('div', class_='col-sm-4').find('img')
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
        seasons = {1: 'winter', 2: 'spring', 3: 'summer', 4: 'fall'}
        season = seasons.get(quarter, 'winter')
        
        seasonal_url = f"{self.base_url}/shows/top?year={year}&season={season}"
        soup = self._make_request(seasonal_url)
        
        if not soup:
            return {"dramas": [], "total": 0, "year": year, "quarter": quarter}

        try:
            dramas = []
            drama_items = soup.find_all('div', class_='box')
            
            for item in drama_items[:20]:
                try:
                    title_elem = item.find('h6')
                    if not title_elem or not title_elem.find('a'):
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    link = title_elem.find('a')['href']
                    slug = link.split('/')[-1] if link else ''
                    
                    img_elem = item.find('img', class_='lazy')
                    image = img_elem.get('data-src') if img_elem else ''
                    
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
            if soup.find(string=re.compile(r'private|Private', re.IGNORECASE)):
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
                    link = title_elem['href']
                    slug = link.split('/')[-1]
                    
                    img_elem = item.find('img')
                    image = img_elem.get('src') or img_elem.get('data-src')
                    
                    dramas.append({
                        'title': drama_title,
                        'slug': slug,
                        'image': image,
                        'url': f"{self.base_url}{link}"
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
            if "private" in str(e).lower():
                raise
            logger.error(f"Error parsing drama list: {str(e)}")
            return None

    async def get_user_drama_list(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user's drama list by user ID"""
        user_list_url = f"{self.base_url}/dramalist/{user_id}"
        soup = self._make_request(user_list_url)
        
        if not soup:
            return None

        try:
            if soup.find(string=re.compile(r'private|Private', re.IGNORECASE)):
                raise Exception("This list is private")
            
            username_elem = soup.find('h1', class_='pull-left')
            username = username_elem.get_text(strip=True).replace("'s Watchlist", "") if username_elem else user_id
            
            dramas = []
            drama_rows = soup.select('table.table-condensed > tbody > tr')
            
            for row in drama_rows[:50]:
                try:
                    title_elem = row.find('a', class_='title')
                    if not title_elem:
                        continue
                        
                    title = title_elem.get_text(strip=True)
                    link = title_elem['href']
                    slug = link.split('/')[-1]
                    
                    status_elem = row.find('span', class_=re.compile(r'status\d+'))
                    status = status_elem.get_text(strip=True) if status_elem else ''

                    rating_elem = row.find('td', class_='score-td')
                    rating = rating_elem.get_text(strip=True) if rating_elem and rating_elem.get_text(strip=True).isdigit() else ''

                    img_elem = row.find('img', class_='lazy')
                    image = img_elem.get('data-src') if img_elem else ''

                    dramas.append({
                        'title': title,
                        'slug': slug,
                        'status': status,
                        'rating': rating,
                        'image': image,
                        'url': f"{self.base_url}{link}"
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
            if "private" in str(e).lower():
                raise
            logger.error(f"Error parsing user drama list: {str(e)}")
            return None
