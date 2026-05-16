# This file is a part of NEO-WZML (github.com/irisXDR/NEO-WZML)

import re
import os
from os import path as ospath

from aiohttp import ClientSession
from lxml.etree import HTML

from bot import LOGGER
from bot.helper.ext_utils.bot_utils import sync_to_async


class ThumbnailFetcher:

    TMDB_BASE_URL = "https://www.themoviedb.org"
    TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"
    VIDEO_EXTENSIONS = {
        '.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv',
        '.webm', '.m4v', '.mpg', '.mpeg', '.ts', '.mts', '.m2ts'
    }

    @staticmethod
    def is_video_file(filename: str) -> bool:
        return ospath.splitext(filename)[1].lower() in ThumbnailFetcher.VIDEO_EXTENSIONS

    @staticmethod
    def parse_filename(filename: str) -> dict:
        name = ospath.splitext(filename)[0]

        year_match = re.search(r'\b(19|20)\d{2}\b', name)
        year = year_match.group() if year_match else None

        is_tv = False
        season = None
        tv_pattern = re.search(r'(.+?)\s*[sS](\d{1,2})\s*[eE](\d{1,3})', name)
        if tv_pattern:
            is_tv = True
            name = tv_pattern.group(1).strip()
            season = int(tv_pattern.group(2))
        else:
            alt_tv_pattern = re.search(r'(.+?)\s*(?:[eE]pisode\s*\d+|[eE]\d+[.\s]*[sS](\d+))', name)
            if alt_tv_pattern:
                is_tv = True
                name = alt_tv_pattern.group(1).strip()
                if alt_tv_pattern.group(2):
                    season = int(alt_tv_pattern.group(2))

        if year:
            name = name.replace(year, ' ').strip()

        name = re.sub(r'\s*[-–]\s*[A-Za-z0-9]+\s*$', '', name)

        patterns_to_remove = [
            r'\[.*?\]',
            r'\([^)]*\)',
            r'\{.*?\}',
            r'\b(?:2160p|1080p|720p|480p|360p|240p|4K|UHD)\b',
            r'\b(?:HDR10\+?|HDR|DV|DoVi|Dolby\s*Vision|SDR)\b',
            r'\b(?:x265|x264|h\.?264|h\.?265|HEVC|AVC|AV1|VP9)\b',
            r'\b(?:BluRay|Blu-Ray|WEBRip|WEB-DL|WEBDL|WEB|DVDRip|BRRip|BDRip|HDRip|HDTV|PDTV|CamRip|BMS|AMZN|NF|DSNP|HMAX|REMUX)\b',
            r'\b(?:DDP5\.?1|DD5\.?1|DDP7\.?1|DD7\.?1|AAC5\.?1|AAC2\.?0|AAC|DTS|DTS-HD|TrueHD|Atmos|EAC3|AC3|FLAC|MA)\b',
            r'\b(?:DSQHD|DS4K|DS2K|DSNHD|IMAX|Extended|Remastered|Unrated|Directors\s*Cut|DC|PROPER|REPACK)\b',
            r'\b(?:10bit|10-bit|8bit|8-bit|Hi10P)\b',
            r'\b(?:Dual[Aa]udio|Multi|Hindi|English|Tamil|Telugu|Malayalam|Kannada|Korean|Japanese|Chinese|Spanish|French|German|Italian|Portuguese|Russian|Indonesian)\b',
            r'\b(?:YIFY|YTS|RARBG|SPARKS|GECKOS|FGT|EVO|ETRG|ETTV|LOL|KILLERS|DIMENSION|FLEET|AVS|CMRG|NTb|CtrlHD|QxR|EDITH|Pahe|PSA|MeGUiL|AMRAP|Chiheisen|Toonworld4all|CR)\b',
            r'\b(?:ESub|ESubs|Subs|Subtitles)\b',
            r'\d+(?:\.\d+)?\s*(?:MB|GB|TB)\b',
        ]

        for pattern in patterns_to_remove:
            name = re.sub(pattern, ' ', name, flags=re.IGNORECASE)

        name = re.sub(r'[._]', ' ', name)

        name = re.sub(r'\s+', ' ', name).strip()
        name = re.sub(r'^[-–\s]+|[-–\s]+$', '', name).strip()

        return {'name': name, 'year': year, 'is_tv': is_tv, 'season': season}

    @staticmethod
    async def search_tmdb(query: str, year: str = None, is_tv: bool = False, season: int = None) -> str or None:
        try:
            from urllib.parse import quote

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9'
            }

            search_types = ['tv', 'movie'] if is_tv else ['movie', 'tv']

            async with ClientSession() as session:
                for search_type in search_types:
                    search_url = f"{ThumbnailFetcher.TMDB_BASE_URL}/search/{search_type}?query={quote(query)}"

                    if year and search_type == 'movie':
                        search_url += f"&year={year}"
                    elif year and search_type == 'tv':
                        search_url += f"&first_air_date_year={year}"

                    LOGGER.debug(f"TMDB search URL: {search_url}")

                    async with session.get(search_url, headers=headers, ssl=False, timeout=10) as resp:
                        if resp.status != 200:
                            continue
                        html_content = await resp.text()

                    html = HTML(html_content)

                    if search_type == 'tv' and season:
                        show_links = html.xpath('//a[contains(@href, "/tv/")]/@href')
                        if show_links:
                            show_path = show_links[0]
                            season_url = f"{ThumbnailFetcher.TMDB_BASE_URL}{show_path}/season/{season}"
                            LOGGER.info(f"TMDB fetching season {season} poster from: {season_url}")
                            
                            async with session.get(season_url, headers=headers, ssl=False, timeout=10) as season_resp:
                                if season_resp.status == 200:
                                    season_html_content = await season_resp.text()
                                    season_html = HTML(season_html_content)

                                    season_posters = season_html.xpath('//div[contains(@class, "poster")]//img/@src')
                                    if not season_posters:
                                        season_posters = season_html.xpath('//img[contains(@src, "/t/p/")]/@src')
                                    
                                    if season_posters:
                                        poster_path = season_posters[0]
                                        poster_match = re.search(r'/t/p/[^/]+/(.+)', poster_path)
                                        if poster_match:
                                            poster_filename = poster_match.group(1)
                                            full_url = f"{ThumbnailFetcher.TMDB_IMAGE_BASE}/{poster_filename}"
                                            LOGGER.info(f"TMDB season {season} poster URL: {full_url}")
                                            return full_url

                    posters = html.xpath('//div[contains(@class, "poster")]//img/@src')
                    if not posters:
                        posters = html.xpath('//a[@data-id]/img/@src')
                    if not posters:
                        posters = html.xpath('//img[contains(@src, "/t/p/")]/@src')

                    if posters:
                        poster_path = posters[0]
                        LOGGER.debug(f"TMDB found poster path: {poster_path}")

                        poster_match = re.search(r'/t/p/[^/]+/(.+)', poster_path)
                        if poster_match:
                            poster_filename = poster_match.group(1)
                            full_url = f"{ThumbnailFetcher.TMDB_IMAGE_BASE}/{poster_filename}"
                            LOGGER.info(f"TMDB poster URL (original quality): {full_url}")
                            return full_url

                        if poster_path.startswith('http'):
                            upgraded = re.sub(r'/t/p/[^/]+/', '/t/p/original/', poster_path)
                            LOGGER.info(f"TMDB poster URL (upgraded): {upgraded}")
                            return upgraded

            return None

        except Exception as e:
            LOGGER.error(f"TMDB search error: {e}")
            return None

    @staticmethod
    async def download_poster(url: str, user_id: int) -> str or None:
        try:
            import tempfile
            from PIL import Image

            fd, temp_path = tempfile.mkstemp(suffix='.jpg', prefix=f'aut_thumb_{user_id}_')
            try:
                os.close(fd)
            except Exception:
                pass

            async with ClientSession() as session:
                async with session.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }, timeout=15) as resp:
                    if resp.status != 200:
                        return None
                    content = await resp.read()

            def save_image():
                from io import BytesIO
                img = Image.open(BytesIO(content))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(temp_path, 'JPEG', quality=95)
                return temp_path

            return await sync_to_async(save_image)

        except Exception as e:
            LOGGER.error(f"Poster download error: {e}")
            return None

    @classmethod
    async def fetch_thumbnail(cls, filename: str, user_id: int) -> str or None:
        if not cls.is_video_file(filename):
            LOGGER.debug(f"Auto-thumbnail: Skipping non-video file: {filename}")
            return None

        parsed = cls.parse_filename(filename)
        if not parsed['name'] or len(parsed['name']) < 3:
            LOGGER.debug(f"Auto-thumbnail: Could not extract valid name from: {filename}")
            return None

        is_tv = parsed.get('is_tv', False)
        season = parsed.get('season')
        if is_tv:
            query = parsed['name']
        else:
            query = f"{parsed['name']} {parsed.get('year') or ''}".strip()

        LOGGER.info(f"Auto-thumbnail: Searching for '{query}' (TV: {is_tv}, Season: {season}, Year: {parsed.get('year')})")

        poster_url = await cls.search_tmdb(query, parsed.get('year'), is_tv=is_tv, season=season)

        if poster_url:
            thumbnail_path = await cls.download_poster(poster_url, user_id)
            if thumbnail_path:
                LOGGER.info(f"Auto-thumbnail: Successfully fetched poster for '{query}'")
                return thumbnail_path

        LOGGER.warning(f"Auto-thumbnail: No poster found for '{query}'")
        return None

    @staticmethod
    async def cleanup_thumbnail(thumb_path: str):
        try:
            if thumb_path and ospath.exists(thumb_path):
                from aiofiles.os import remove
                await remove(thumb_path)
                LOGGER.debug(f"Auto-thumbnail: Cleaned up {thumb_path}")
        except Exception as e:
            LOGGER.error(f"Auto-thumbnail cleanup error: {e}")
