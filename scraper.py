from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup
import logging
import asyncio
from typing import Dict, List, Optional, Any
import re
from urllib.parse import quote

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


    async def _make_request(self, url: str) -> Optional[BeautifulSoup]:
        """Make HTTP request and return BeautifulSoup object"""
        try:
            async with AsyncSession(impersonate="chrome110") as session:
                response = await session.get(url, timeout=10)
                response.raise_for_status()
                return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logger.error(f"Request failed for {url}: {str(e)}")
            return None

    async def search_dramas(self, query: str) -> Dict[str, Any]:
        """Search for dramas by query"""
        search_url = f"{self.base_url}/search?q={quote(query)}"
        soup = await self._make_request(search_url)
        
        if not soup:
            return {"results": [], "total": 0}

        results = []
        drama_items = soup.find_all('div', class_='box')
        
        for item in drama_items[:20]:
            try:
                title_elem = item.find('h6', class_='title')
                if not title_elem or not title_elem.find('a'):
                    continue
                
                title = title_elem.get_text(strip=True)
                link_elem = title_elem.find('a')
                link = link_elem['href'] if link_elem else ''
                slug = link.split('/')[-1] if link else ''
                
                year_elem = item.find('span', class_='text-muted')
                year_match = re.search(r'(\d{4})', year_elem.get_text(strip=True)) if year_elem else None
                year = year_match.group(1) if year_match else ''
                
                img_elem = item.find('img', class_='lazy')
                image = img_elem['data-src'] if img_elem and 'data-src' in img_elem.attrs else (item.find('img')['src'] if item.find('img') else '')

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
        soup = await self._make_request(drama_url)
        
        if not soup:
            return None

        try:
            details = {'slug': slug, 'url': drama_url}

            # --- Main Title and Image ---
            title_elem = soup.select_one('h1.film-title')
            details['title'] = title_elem.get_text(strip=True) if title_elem else 'N/A'
            
            img_elem = soup.select_one('div.film-cover img')
            details['image'] = img_elem.get('src') or img_elem.get('data-src') or '' if img_elem else ''

            # --- Synopsis ---
            synopsis_elem = soup.select_one('div.show-synopsis > p')
            details['synopsis'] = synopsis_elem.get_text(" ", strip=True).replace(' Edit Translation', '') if synopsis_elem else ''

            # --- Sidebar Details & Statistics ---
            sidebar_details = soup.select("div.content-side .box")
            for box in sidebar_details:
                header_elem = box.select_one('.box-header h3')
                if not header_elem:
                    continue
                header = header_elem.get_text(strip=True)
                
                if header == 'Details':
                    for item in box.select('li.list-item'):
                        item_text = item.get_text(" ", strip=True)
                        if 'Drama:' in item_text:
                            details['type'] = item_text.replace('Drama:', '').strip()
                        elif 'Country:' in item_text:
                            details['country'] = item_text.replace('Country:', '').strip()
                        elif 'Episodes:' in item_text:
                            details['episodes'] = item_text.replace('Episodes:', '').strip()
                        elif 'Aired:' in item_text:
                            details['aired'] = item_text.replace('Aired:', '').strip()
                        elif 'Aired On:' in item_text:
                            details['aired_on'] = item_text.replace('Aired On:', '').strip()
                        elif 'Original Network:' in item_text:
                            network_elem = item.find('a')
                            details['original_network'] = network_elem.get_text(strip=True) if network_elem else item_text.replace('Original Network:', '').strip()
                        elif 'Duration:' in item_text:
                            details['duration'] = item_text.replace('Duration:', '').strip()
                        elif 'Content Rating:' in item_text:
                            details['content_rating'] = item_text.replace('Content Rating:', '').strip()
                
                elif header == 'Statistics':
                    for item in box.select('li.list-item'):
                        item_text = item.get_text(" ", strip=True)
                        if 'Score:' in item_text:
                            details['score_details'] = item_text.replace('Score:', '').strip()
                        elif 'Ranked:' in item_text:
                            details['ranked'] = item_text.replace('Ranked:', '').strip()
                        elif 'Popularity:' in item_text:
                            details['popularity'] = item_text.replace('Popularity:', '').strip()
                        elif 'Watchers:' in item_text:
                            details['watchers'] = item_text.replace('Watchers:', '').strip()
            
            # --- Main Details (Native Title, Genres, Tags) ---
            main_details_list = soup.select_one('div.show-detailsxss > ul.list')
            if main_details_list:
                for item in main_details_list.select('li.list-item'):
                    key_elem = item.find('b', class_='inline')
                    if not key_elem: continue
                    key = key_elem.get_text(strip=True)
                    
                    if 'Native Title:' in key:
                        details['native_title'] = item.get_text().replace(key, '', 1).strip()
                    elif 'Also Known As:' in key:
                        details['also_known_as'] = [s.strip() for s in item.get_text().replace(key, '', 1).split(',') if s.strip()]
                    elif 'Genres:' in key:
                        details['genres'] = [a.get_text(strip=True) for a in item.select('a')]
                    elif 'Tags:' in key:
                        tags = [a.get_text(strip=True) for a in item.select('a')]
                        details['tags'] = [t for t in tags if t != '(Vote tags)']

            # --- Overall Rating ---
            rating_elem = soup.select_one('.hfs b')
            details['rating'] = rating_elem.get_text(strip=True) if rating_elem else 'N/A'

            return details

        except Exception as e:
            logger.error(f"Error parsing drama details for '{slug}': {str(e)}")
            return None

    async def get_drama_cast(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get cast information for a drama"""
        cast_url = f"{self.base_url}/{slug}/cast"
        soup = await self._make_request(cast_url)
        
        if not soup:
            return None

        cast_by_role = {}
        try:
            # The page is structured by headers (h3) for roles
            role_headers = soup.find_all('h3', class_='header')
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
                        profile_url = name_elem.get('href', '')

                        character_role = ''
                        role_div = name_elem.find_next_sibling('div')
                        if role_div and role_div.find('small'):
                            character_role = role_div.find('small').get_text(strip=True)
                        
                        img_elem = item.find('img')
                        image = (img_elem.get('src') or img_elem.get('data-src') or '') if img_elem else ''

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
        soup = await self._make_request(episodes_url)
        
        if not soup:
            return None

        try:
            episodes = []
            episode_items = soup.find_all('div', class_='episode')
            
            for item in episode_items:
                try:
                    title_elem = item.select_one('h2.title > a')
                    full_title = title_elem.get_text(strip=True) if title_elem else ''
                    
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
        soup = await self._make_request(reviews_url)
        
        if not soup:
            return None

        try:
            reviews = []
            review_items = soup.find_all('div', class_='review')
            
            for item in review_items[:10]:
                try:
                    author_elem = item.find('a', class_='text-primary')
                    author = author_elem.get_text(strip=True) if author_elem else ''
                    
                    rating_elem = item.select_one('.rating-overall .score')
                    rating = rating_elem.get_text(strip=True) if rating_elem else ''
                    
                    content_elem = item.find('div', class_='review-body')
                    content_p = content_elem.find_all('p') if content_elem else []
                    content = "\n".join([p.get_text(" ", strip=True) for p in content_p])
                    
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

    async def get_person_details(self, people_id: str) -> Optional[Dict[str, Any]]:
        """Get person details by ID"""
        person_url = f"{self.base_url}/people/{people_id}"
        soup = await self._make_request(person_url)
        
        if not soup:
            return None

        try:
            data = {'id': people_id, 'url': person_url}

            name_elem = soup.select_one('h1.film-title')
            data['name'] = name_elem.get_text(strip=True) if name_elem else 'N/A'

            img_elem = soup.select_one('.profile-image img, .box-body img.img-responsive')
            data['image'] = img_elem['src'] if img_elem else ''

            # --- Personal Info from sidebar ---
            info = {}
            details_box = soup.select_one('div.box.clear.hidden-sm-down')
            if details_box:
                info_list = details_box.select('ul.list > li.list-item')
                for item in info_list:
                    key_elem = item.find('b')
                    if key_elem:
                        key = key_elem.get_text(strip=True).replace(':', '').strip().lower().replace(' ', '_')
                        value = item.get_text().replace(key_elem.get_text(), '', 1).strip()
                        info[key] = value
            data['personal_info'] = info
            
            # --- Biography ---
            bio_container = soup.select_one('div.col-sm-8.col-lg-12.col-md-12')
            if bio_container:
                # Get all text nodes directly under the div, excluding those in script tags or children tags
                bio_texts = [text.strip() for text in bio_container.find_all(string=True, recursive=False) if text.strip()]
                data['biography'] = " ".join(bio_texts)
            
            # --- Filmography ---
            filmography = {}
            film_headers = soup.select('div.box-body > h5.header')
            for header in film_headers:
                category = header.get_text(strip=True)
                table = header.find_next_sibling('table', class_='film-list')
                if table:
                    entries = []
                    for row in table.select('tbody > tr'):
                        entry = {}
                        entry['year'] = row.select_one('td.year').get_text(strip=True) if row.select_one('td.year') else 'N/A'
                        
                        title_link = row.select_one('td.title a')
                        entry['title'] = title_link.get_text(strip=True) if title_link else 'N/A'
                        
                        role_div = row.select_one('td.role > div.name')
                        role_text_div = row.select_one('td.role > div.text-muted')
                        entry['character_name'] = role_div.get_text(strip=True) if role_div else ''
                        entry['role'] = role_text_div.get_text(strip=True) if role_text_div else ''

                        rating_div = row.select_one('td.text-center > div.text-sm')
                        entry['rating'] = rating_div.get_text(strip=True) if rating_div else 'N/A'
                        
                        entries.append(entry)
                    filmography[category] = entries
            data['filmography'] = filmography

            return data
        except Exception as e:
            logger.error(f"Error parsing person details for '{people_id}': {str(e)}")
            return None

    async def get_seasonal_dramas(self, year: int, quarter: int) -> Dict[str, Any]:
        """Get seasonal dramas"""
        seasons = {1: 'winter', 2: 'spring', 3: 'summer', 4: 'fall'}
        season = seasons.get(quarter, 'winter')
        
        seasonal_url = f"{self.base_url}/shows/top?year={year}&season={season}"
        soup = await self._make_request(seasonal_url)
        
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
                    link_elem = title_elem.find('a')
                    link = link_elem['href'] if link_elem else ''
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
        soup = await self._make_request(list_url)
        
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
                    image = (img_elem.get('data-src') or img_elem.get('src') or '') if img_elem else ''
                    
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
        soup = await self._make_request(user_list_url)
        
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
                        
                        img_elem = row.find('img')
                        image = (img_elem.get('data-src') or img_elem.get('src') or '') if img_elem else ''

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

    async def get_drama_recommendations(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get recommendations for a specific drama with optimized parsing and pagination"""
        all_recommendations = []
        page = 1
        base_rec_url = f"{self.base_url}/{slug}/recs"
        
        while True:
            rec_url = f"{base_rec_url}?page={page}" if page > 1 else base_rec_url
            soup = await self._make_request(rec_url)
            if not soup:
                break
            
            # Updated selector for recommendation items
            rec_items = soup.select("div.box-body.b-t")
            if not rec_items:
                # Fallback check if no items found with b-t class
                rec_items = soup.select("div.box:has(b a)")
                if not rec_items:
                    break
                
            page_recs_found = 0
            for item in rec_items:
                try:
                    # --- TITLE + YEAR ---
                    # Updated selector to 'b a'
                    title_elem = item.select_one("b a")
                    if not title_elem:
                        continue
                    
                    title_full = title_elem.get_text(strip=True)
                    # Match "Title (Year)"
                    title_match = re.match(r"(.+?)\s*\((\d{4})\)", title_full)
                    title = title_match.group(1).strip() if title_match else title_full
                    year = title_match.group(2) if title_match else ""

                    link = title_elem["href"] if title_elem else ""
                    slug_rec = link.split("/")[-1] if link else ""

                    # --- IMAGE ---
                    img_elem = item.select_one("img")
                    image = img_elem.get("data-src") or img_elem.get("src") if img_elem else ""

                    # --- RATING ---
                    rating_elem = item.select_one(".score")
                    rating = rating_elem.get_text(strip=True) if rating_elem else ""

                    # --- REASON ---
                    # Updated selector to 'div.recs-body'
                    reason_container = item.select_one("div.recs-body")
                    reason_lines = []
                    if reason_container:
                        raw_text = reason_container.get_text("\n", strip=True)
                        lines = [p.strip() for p in raw_text.split("\n") if p.strip()]
                        
                        # Handle requested reason parsing: split by newline and strip.
                        # If the list seems to start with dashes, it's likely the old style bulleted list.
                        # But user specified: "if not bulleted" - we'll handle both.
                        is_bulleted = any(line.startswith("-") for line in lines)
                        if is_bulleted:
                            reason_lines = [line.lstrip("-").strip() for line in lines if line.startswith("-")]
                            if not reason_lines: # Fallback if dash detection failed but some text exists
                                reason_lines = lines
                        else:
                            reason_lines = lines

                    # --- RECOMMENDED BY ---
                    # Updated selector to 'span.recs-author a'
                    author_elem = item.select_one("span.recs-author a")
                    recommended_by = author_elem.get_text(strip=True) if author_elem else ""

                    # --- VOTES ---
                    # Updated selector to '.like-cnt'
                    votes_elem = item.select_one(".like-cnt")
                    votes = votes_elem.get_text(strip=True) if votes_elem else "0"

                    all_recommendations.append({
                        "title": title,
                        "year": year,
                        "slug": slug_rec,
                        "url": f"{self.base_url}{link}" if link else "",
                        "image": image,
                        "rating": rating,
                        "reasons": reason_lines,
                        "recommended_by": recommended_by,
                        "votes": votes
                    })
                    page_recs_found += 1
                except Exception as e:
                    logger.error(f"Error parsing recommendation: {str(e)}")
                    continue
            
            if page_recs_found == 0:
                break
                
            # Check for next page in pagination
            # Usually: <li class="page-item next"><a class="page-link" href="...">Next</a></li>
            # Or sometimes just a link with 'next' in rel
            next_link = soup.select_one("li.page-item.next:not(.disabled) a.page-link") or soup.select_one("a.page-link[rel='next']")
            if not next_link or page >= 5: # Limit pagination to 5 pages to avoid rate limits/timeouts
                break
                
            page += 1
            await asyncio.sleep(0.5) # Anti-ban delay

        return {
            "recommendations": all_recommendations,
            "total": len(all_recommendations),
            "url": base_rec_url,
            "pages_fetched": page
        }
