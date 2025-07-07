#!/usr/bin/env python3
"""Async article fetcher with robust resource management."""

import asyncio
import logging
import random
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import aiohttp
from newspaper import Article
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from config import config, ScrapingConfig

logger = logging.getLogger(__name__)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0'
]


class AsyncSessionManager:
    """Manages aiohttp sessions with proper resource lifecycle handling."""
    
    def __init__(self, scraping_config: ScrapingConfig):
        self.config = scraping_config
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._cleanup_lock = asyncio.Lock()
        self._is_closed = True
        
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create a managed aiohttp session."""
        async with self._cleanup_lock:
            if self._session is None or self._session.closed or self._is_closed:
                await self._create_session()
            return self._session
    
    async def _create_session(self):
        """Initialize new aiohttp session with proper configuration."""
        self._connector = aiohttp.TCPConnector(
            limit=20,
            limit_per_host=5,
            ttl_dns_cache=300,
            use_dns_cache=True,
            enable_cleanup_closed=True,
            keepalive_timeout=30
        )
        
        timeout = aiohttp.ClientTimeout(
            total=self.config.timeout,
            connect=30,
            sock_read=60
        )
        
        self._session = aiohttp.ClientSession(
            connector=self._connector,
            timeout=timeout,
            connector_owner=True,
            headers={'User-Agent': random.choice(USER_AGENTS)}
        )
        self._is_closed = False
        logger.debug("Created new session with connector ownership")
    
    def get_semaphore(self) -> asyncio.Semaphore:
        """Get concurrency limiter semaphore."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(
                self.config.max_sources_per_topic
            )
        return self._semaphore
    
    async def close(self):
        """Safely close session and release resources."""
        async with self._cleanup_lock:
            if self._is_closed:
                return
                
            try:
                if self._session and not self._session.closed:
                    logger.debug("Closing session...")
                    await self._session.close()
                    logger.debug("Session closed successfully")
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")
            finally:
                self._is_closed = True
                self._session = None
                self._connector = None

    def is_session_active(self) -> bool:
        """Check if session is available for use."""
        return (
            not self._is_closed and 
            self._session is not None and 
            not self._session.closed
        )


class BrowserManager:
    """Manages Selenium browser instances for JS-rendered content."""
    
    def __init__(self, scraping_config: ScrapingConfig):
        self.config = scraping_config
        self.driver = None
        self._is_initialized = False
    
    def get_driver(self):
        """Get initialized Selenium WebDriver instance."""
        if not self._is_initialized or not self.driver:
            self._initialize_driver()
        return self.driver

    def _initialize_driver(self):
        """Create new Chrome browser instance."""
        try:
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument(
                f"--user-agent={random.choice(USER_AGENTS)}"
            )
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(
                service=service, 
                options=options
            )
            self.driver.set_page_load_timeout(self.config.timeout)
            self._is_initialized = True
            logger.info("Browser driver initialized")
        except Exception as e:
            logger.error(f"Browser initialization failed: {str(e)}")
            raise
    
    def cleanup(self):
        """Release browser resources."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser driver cleaned up")
            except Exception as e:
                logger.error(f"Browser cleanup error: {str(e)}")
            finally:
                self.driver = None
                self._is_initialized = False


class AsyncArticleFetcher:
    """Asynchronously fetches and processes web articles."""
    
    def __init__(self, scraping_config: ScrapingConfig):
        self.config = scraping_config
        self.session_manager = AsyncSessionManager(self.config)
        self._active_tasks = set()
        self._is_closed = False
    
    async def extract_single_article(self, url: str) -> Tuple[str, str]:
        """Extract title and content from a single article URL."""
        if self._is_closed:
            return "Error: Fetcher closed", ""
            
        semaphore = self.session_manager.get_semaphore()
        async with semaphore:
            session = await self.session_manager.get_session()
            resolved_url = await self._resolve_google_news_url(url, session)
            
            for attempt in range(self.config.max_retries):
                try:
                    title, content = await self._extract_with_aiohttp(
                        resolved_url, 
                        session
                    )
                    if content and len(content) > 100:
                        return title, content
                    
                    if attempt < self.config.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                except Exception as e:
                    logger.warning(
                        f"Attempt {attempt+1} failed for {url}: {e}"
                    )
                    if attempt < self.config.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
            
            return "Error: Extraction failed", self._generate_fallback_content(url)
    
    async def _resolve_google_news_url(
        self, 
        url: str, 
        session: aiohttp.ClientSession
    ) -> str:
        """Resolve Google News redirect URLs to actual article URLs."""
        if 'news.google.com/rss/articles/' not in url:
            return url
        
        try:
            async with session.get(url, allow_redirects=True) as response:
                if 'news.google.com' not in str(response.url):
                    return str(response.url)
        except Exception as e:
            logger.warning(f"Google News resolution failed: {e}")
        
        return url
    
    async def _extract_with_aiohttp(
        self, 
        url: str, 
        session: aiohttp.ClientSession
    ) -> Tuple[str, str]:
        """Extract article content using newspaper3k library."""
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                return "Error: Non-200 response", ""
                
            html_content = await response.text()
            article = Article(url, language='en')
            article.download(input_html=html_content)
            article.parse()
            
            if article.title and article.text and len(article.text) > 100:
                return article.title, article.text
        
        return "Error: Failed to extract", ""
    
    def _generate_fallback_content(self, url: str) -> str:
        """Generate placeholder content when extraction fails."""
        domain = urlparse(url).netloc
        return f"Content from {domain} could not be extracted. Source: {url}"
    
    async def extract_multiple_articles(
        self, 
        urls: List[str]
    ) -> List[Tuple[str, str, str]]:
        """Concurrently process multiple article URLs."""
        if self._is_closed:
            logger.warning("Fetcher is closed, aborting extraction")
            return []
        
        logger.info(f"Starting extraction of {len(urls)} articles")
        
        tasks = [
            asyncio.create_task(self._extract_with_url(url))
            for url in urls
        ]
        self._active_tasks.update(tasks)
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=300
            )
        except asyncio.TimeoutError:
            logger.error("Article extraction timed out")
            for task in tasks:
                if not task.done():
                    task.cancel()
            results = [Exception("Timeout") for _ in tasks]
        finally:
            self._active_tasks.difference_update(tasks)
        
        return self._process_results(urls, results)
    
    async def _extract_with_url(self, url: str) -> Tuple[str, str]:
        """Wrapper for concurrent extraction tasks."""
        return await self.extract_single_article(url)
    
    def _process_results(self, urls, results) -> List[Tuple[str, str, str]]:
        """Convert extraction results to uniform format."""
        extracted = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Task failed for {urls[i]}: {result}")
                extracted.append((urls[i], "Error: Task failed", ""))
            else:
                extracted.append((urls[i], result[0], result[1]))
        return extracted
    
    async def cleanup(self):
        """Safely release all resources and cancel pending tasks."""
        if self._is_closed:
            return
            
        logger.info("Initiating fetcher cleanup...")
        self._is_closed = True
        
        try:
            if self._active_tasks:
                logger.info(f"Cancelling {len(self._active_tasks)} tasks")
                for task in self._active_tasks:
                    if not task.done():
                        task.cancel()
                
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self._active_tasks, return_exceptions=True),
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("Task cancellation timeout")
                
                self._active_tasks.clear()
            
            await self.session_manager.close()
            await asyncio.sleep(0.2)
            logger.info("Fetcher cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


# Service instances
browser_manager = BrowserManager(config.scraping)
async_fetcher = AsyncArticleFetcher(config.scraping)

BrowserManagerInstance = browser_manager  # optional alias
__all__ = ['BrowserManager', 'browser_manager']

async def emergency_cleanup():
    """Emergency resource cleanup handler for unexpected exits."""
    try:
        logger.warning("Emergency cleanup triggered!")
        await async_fetcher.cleanup()
        logger.info("Emergency cleanup completed")
    except Exception as e:
        logger.error(f"Emergency cleanup failed: {e}")