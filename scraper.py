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
                
                # Image can be in 'data-src' for lazy loading or 'src'
                img_elem = item.find('img', class_='lazy') or item.find('img')
                image = img_elem.get('data-src') or img_elem.get('src', '')

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
            data = {'slug': slug, 'url': drama_url}
            
            # --- Main Info ---
            data['title'] = soup.select_one('h1.film-title').get_text(strip=True) if soup.select_one('h1.film-title') else ''
            data['image'] = soup.select_one('div.film-cover img.img-responsive')['src'] if soup.select_one('div.film-cover img.img-responsive') else ''
            data['synopsis'] = soup.select_one('div.show-synopsis p').get_text(" ", strip=True) if soup.select_one('div.show-synopsis p') else ''
            
            # --- Sidebar Info ---
            sidebar_details = {}
            sidebar_stats = {}
            
            # Find details and stats boxes in the sidebar
            details_header = soup.find('h3', string='Details')
            if details_header:
                details_box = details_header.find_parent('.box')
                for item in details_box.select('.list-item'):
                    key_b = item.find('b')
                    if key_b:
                        key = key_b.get_text(strip=True).replace(':', '').strip()
                        value = item.get_text().replace(key_b.get_text(), '', 1).strip()
                        sidebar_details[key] = value

            stats_header = soup.find('h3', string='Statistics')
            if stats_header:
                stats_box = stats_header.find_parent('.box')
                for item in stats_box.select('.list-item'):
                    key_b = item.find('b')
                    if key_b:
                        key = key_b.get_text(strip=True).replace(':', '').strip()
                        value = item.get_text().replace(key_b.get_text(), '', 1).strip()
                        sidebar_stats[key] = value

            data.update({
                "drama": sidebar_details.get("Drama"),
                "country": sidebar_details.get("Country"),
                "episodes": sidebar_details.get("Episodes"),
                "aired": sidebar_details.get("Aired"),
                "aired_on": sidebar_details.get("Aired On"),
                "original_network": sidebar_details.get("Original Network"),
                "duration": sidebar_details.get("Duration"),
                "content_rating": sidebar_details.get("Content Rating"),
            })

            score_text = sidebar_stats.get("Score", "")
            score_match = re.search(r'([\d.]+)\s*\(scored by\s*([\d,]+)\s*users\)', score_text)
            if score_match:
                data['rating'] = score_match.group(1)
                data['scored_by'] = score_match.group(2)
            else:
                data['rating'] = 'N/A'
                data['scored_by'] = '0'
                
            data['ranked'] = sidebar_stats.get('Ranked')
            data['popularity'] = sidebar_stats.get('Popularity')
            data['watchers'] = sidebar_stats.get('Watchers')
            
            # --- Main Content Details for lists ---
            main_details_list = soup.select_one('div.show-detailsxss > ul.list')
            if main_details_list:
                for item in main_details_list.find_all('li', class_='list-item'):
                    key_b = item.find('b', class_='inline')
                    if key_b:
                        key_text = key_b.get_text(strip=True)
                        if 'Native Title:' in key_text:
                            data['native_title'] = item.get_text().replace(key_text, '').strip()
                        elif 'Also Known As:' in key_text:
                            data['alternative_titles'] = [a.strip() for a in item.get_text().replace(key_text, '').strip().split(',') if a.strip()]
                        elif 'Genres:' in key_text:
                            data['genres'] = [a.get_text(strip=True) for a in item.select('a')]
                        elif 'Tags:' in key_text:
                            data['tags'] = [a.get_text(strip=True) for a in item.select('a')]

            return data

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
            role_headers = soup.select('h3.header.b-b')
            for header in role_headers:
                role_name = header.get_text(strip=True)
                cast_list = []
                
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
                        
                        # Find character name container (a div after the name anchor)
                        character_div = name_elem.find_next_sibling('div')
                        character_role = ''
                        if character_div:
                            char_small = character_div.find('small')
                            if char_small:
                                character_role = char_small.get_text(strip=True)

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

                    rating = 'N/A'
                    rating_elem = item.select_one('.rating-panel b')
                    if rating_elem:
                        rating = rating_elem.get_text(strip=True)
                    
                    episodes.append({
                        'episode_number': episode_num,
                        'title': full_title,
                        'air_date': air_date,
                        'rating': rating,
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
                    review_data = {}
                    author_elem = item.find('a', class_='text-primary')
                    review_data['author'] = author_elem.get_text(strip=True) if author_elem else ''
                    
                    # Ratings box
                    rating_box = item.select_one('.review-body > .box')
                    if rating_box:
                        overall_rating_elem = rating_box.select_one('.rating-overall .score')
                        review_data['rating_overall'] = overall_rating_elem.get_text(strip=True) if overall_rating_elem else ''
                        
                        rating_breakdown = {}
                        for rating_item in rating_box.select('.review-rating > div'):
                            text = rating_item.get_text()
                            score = rating_item.find('span', class_='pull-right').get_text()
                            key = text.replace(score, '').strip().lower().replace('/', '_').replace(' ', '_')
                            rating_breakdown[key] = score
                        review_data['ratings'] = rating_breakdown
                    
                    content_elem = item.find('div', class_='review-body')
                    review_data['content'] = content_elem.find('p').get_text(" ", strip=True)
                    
                    date_elem = item.find('small', class_='datetime')
                    review_data['date'] = date_elem.get_text(strip=True) if date_elem else ''
                    
                    reviews.append(review_data)
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
            data = {'id': people_id, 'url': person_url}
            
            data['name'] = soup.select_one('h1.film-title').get_text(strip=True)
            data['image'] = soup.select_one('div.profile-image img, div.film-cover img')['src']

            # --- Personal Info ---
            personal_info = {}
            info_list = soup.select_one("div.box.clear.hidden-sm-down .box-body > .list")
            if info_list:
                for item in info_list.select("li.list-item"):
                    key_b = item.find("b")
                    if key_b:
                        key = key_b.get_text(strip=True).replace(":", "").lower().replace(" ", "_")
                        value = item.get_text().replace(key_b.get_text(), "").strip()
                        personal_info[key] = value
            data['personal_info'] = personal_info

            # --- Biography ---
            bio_container = soup.select_one('div.col-sm-8.col-lg-12.col-md-12')
            if bio_container:
                bio_lines = [line.strip() for line in bio_container.find_all(string=True, recursive=False) if line.strip()]
                data['biography'] = " ".join(bio_lines)

            # --- Filmography ---
            filmography = {}
            for header in soup.select('h5.header'):
                category = header.get_text(strip=True).lower()  # 'drama', 'movie', etc.
                table = header.find_next_sibling('table', class_='film-list')
                if table:
                    category_entries = []
                    for row in table.select('tbody > tr'):
                        entry = {}
                        entry['year'] = row.select_one('td.year').get_text(strip=True) if row.select_one('td.year') else ''
                        title_elem = row.select_one('td.title > b > a')
                        if title_elem:
                            entry['title'] = title_elem.get_text(strip=True)
                            entry['slug'] = title_elem['href'].split('/')[-1]

                        role_elem = row.select_one('td.role')
                        if role_elem:
                            role_text = role_elem.find(class_='text-muted').get_text(strip=True)
                            entry['role'] = role_text
                            char_text = role_elem.find(class_='name').get_text(strip=True)
                            entry['character_name'] = char_text if char_text != role_text else ''
                        
                        rating_elem = row.select_one('td.text-center > .text-sm')
                        entry['rating'] = rating_elem.get_text(strip=True) if rating_elem else ''
                        category_entries.append(entry)
                    filmography[category] = category_entries
            data['filmography'] = filmography

            return data
        except Exception as e:
            logger.error(f"Error parsing person details for {people_id}: {str(e)}")
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
            if "private" in soup.text.lower() and "list" in soup.text.lower():
                raise Exception("This list is private")
            
            title_elem = soup.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            description_elem = soup.select_one('div.box-header .description')
            description = description_elem.get_text(strip=True) if description_elem else ''
            
            dramas = []
            drama_items = soup.select('ul.list-group li.list-group-item')
            
            for item in drama_items:
                try:
                    title_elem = item.select_one('h2.title > a')
                    if not title_elem:
                        continue
                    
                    drama_title = title_elem.get_text(strip=True)
                    link = title_elem['href']
                    slug = link.split('/')[-1] if link else ''
                    
                    img_elem = item.find('img', class_='lazy')
                    image = img_elem.get('data-src') or img_elem.get('src')
                    
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
            if "This user's list is private." in soup.get_text():
                raise Exception("This list is private")
            
            username_elem = soup.select_one('h1.mdl-style-header a')
            username = username_elem.get_text(strip=True) if username_elem else user_id
            
            dramas = []
            list_sections = soup.find_all('div', class_='mdl-style-list')
            
            for section in list_sections:
                status_header = section.find('h3', class_='mdl-style-list-label')
                status = status_header.get_text(strip=True) if status_header else 'Unknown'

                drama_rows = section.select('table > tbody > tr')

                for row in drama_rows:
                    try:
                        title_elem = row.find('a', class_='title')
                        if not title_elem:
                            continue
                            
                        title = title_elem.get_text(strip=True)
                        link = title_elem['href']
                        slug = link.split('/')[-1] if link else ''

                        rating_elem = row.select_one('td.mdl-style-col-score .score')
                        rating = rating_elem.get_text(strip=True) if rating_elem and rating_elem.get_text(strip=True) not in ["0.0", "N/A"] else ''
                        
                        image = ''

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
            if "private" in str(e).lower():
                raise
            logger.error(f"Error parsing user drama list: {str(e)}")
            return None
