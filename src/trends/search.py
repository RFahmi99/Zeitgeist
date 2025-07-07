import asyncio
import asyncpraw
import logging
import os
from dataclasses import dataclass
from typing import List
from urllib.parse import quote

import feedparser
import requests

logger = logging.getLogger(__name__)


@dataclass
class ArticleSource:
    url: str
    title: str
    source: str
    published_date: str = None
    confidence_score: float = 0.0


class ArticleFinder:
    """Multi-source article finder with proper session management"""
    
    def __init__(self):
        self.search_methods = [
            self._search_google_news,
            self._search_newsapi,
            self._search_reddit_articles,
            self._search_rss_feeds
        ]

    async def find_articles(self, topic: str, limit: int = 10) -> List[str]:
        """Find articles on a given topic from multiple sources"""
        all_articles = []
        
        for method in self.search_methods:
            try:
                articles = await self._fetch_articles(method, topic)
                all_articles.extend(articles)
                await asyncio.sleep(1)  # Rate limiting
            except Exception as e:
                logger.warning(f"Search method failed: {e}")
        
        unique_articles = self._deduplicate_articles(all_articles)
        return [article.url for article in unique_articles[:limit]]

    async def _fetch_articles(self, method, topic: str) -> List[ArticleSource]:
        """Fetch articles from a search method with async support"""
        if asyncio.iscoroutinefunction(method):
            return await method(topic)
        return method(topic)

    def _search_google_news(self, topic: str) -> List[ArticleSource]:
        """Google News search"""
        try:
            rss_url = f"https://news.google.com/rss/search?q={quote(topic)}"
            feed = feedparser.parse(rss_url)
            return [
                ArticleSource(
                    url=entry.link,
                    title=entry.title,
                    source="google_news",
                    published_date=entry.get('published', ''),
                    confidence_score=0.9
                )
                for entry in feed.entries[:5]
            ]
        except Exception as e:
            logger.error(f"Google News failed: {e}")
            return []

    def _search_newsapi(self, topic: str) -> List[ArticleSource]:
        """NewsAPI.org search"""
        api_key = os.getenv('NEWSAPI_KEY')
        if not api_key:
            logger.info("Skipping NewsAPI: key not found")
            return []
        
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': topic,
                'sortBy': 'publishedAt',
                'pageSize': 5,
                'language': 'en',
                'apiKey': api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            return [
                ArticleSource(
                    url=article['url'],
                    title=article['title'],
                    source="newsapi",
                    published_date=article.get('publishedAt', ''),
                    confidence_score=0.7
                )
                for article in data.get('articles', [])
            ]
        except Exception as e:
            logger.error(f"NewsAPI failed: {e}")
            return []

    async def _search_reddit_articles(self, topic: str) -> List[ArticleSource]:
        """Search for articles shared on Reddit"""
        try:
            import asyncpraw
            return await self._fetch_reddit_articles(topic)
        except ImportError:
            logger.warning("Skipping Reddit: asyncpraw not installed")
            return []
        except Exception as e:
            logger.error(f"Reddit search failed: {e}")
            return []

    async def _fetch_reddit_articles(self, topic: str) -> List[ArticleSource]:
        """Fetch articles from Reddit using asyncpraw"""
        client_id = os.getenv('REDDIT_CLIENT_ID')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        if not client_id or not client_secret:
            logger.info("Skipping Reddit: credentials missing")
            return []

        reddit = asyncpraw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent='script:your-script-name:v1.0'
        )
        
        try:
            return await self._process_reddit_subs(reddit, topic)
        finally:
            try:
                await reddit.close()
                logger.debug("Reddit connection closed")
            except Exception:
                pass

    async def _process_reddit_subs(self, reddit, topic: str) -> List[ArticleSource]:
        """Process Reddit subreddits for articles"""
        articles = []
        subreddits = ['news', 'worldnews', 'technology', 'science', 'business']
        
        for subreddit_name in subreddits:
            try:
                subreddit = await reddit.subreddit(subreddit_name)
                async for post in subreddit.search(topic, limit=2, sort='relevance'):
                    if self._is_valid_reddit_post(post):
                        articles.append(
                            ArticleSource(
                                url=post.url,
                                title=post.title,
                                source=f"reddit_{subreddit_name}",
                                confidence_score=min(post.score / 1000, 0.6)
                            )
                        )
            except Exception as e:
                logger.warning(f"Failed r/{subreddit_name}: {e}")
        
        return articles

    def _is_valid_reddit_post(self, post) -> bool:
        """Check if a Reddit post links to an external article"""
        return post.url and not post.url.startswith('https://www.reddit.com')

    def _search_rss_feeds(self, topic: str) -> List[ArticleSource]:
        """Search through various RSS feeds"""
        articles = []
        rss_feeds = [
            ("https://feeds.reuters.com/Reuters/worldNews", "reuters"),
            ("https://rss.cnn.com/rss/edition.rss", "cnn"),
            ("https://feeds.bbci.co.uk/news/world/rss.xml", "bbc"),
            ("https://feeds.npr.org/1001/rss.xml", "npr"),
            ("https://feeds.washingtonpost.com/rss/world", "washingtonpost"),
            ("http://feeds.foxnews.com/foxnews/latest", "foxnews")
        ]
        
        for feed_url, source_name in rss_feeds:
            try:
                articles.extend(self._process_rss_feed(feed_url, source_name, topic))
            except Exception as e:
                logger.warning(f"RSS feed failed: {feed_url} - {e}")
        
        return articles

    def _process_rss_feed(self, feed_url: str, source_name: str, topic: str) -> List[ArticleSource]:
        """Process a single RSS feed for relevant articles"""
        articles = []
        feed = feedparser.parse(feed_url)
        topic_keywords = topic.lower().split()
        
        for entry in feed.entries[:10]:
            if self._is_relevant_entry(entry, topic_keywords):
                articles.append(ArticleSource(
                    url=entry.link,
                    title=entry.title,
                    source=f"rss_{source_name}",
                    published_date=entry.get('published', ''),
                    confidence_score=0.7
                ))
            if len(articles) >= 2:
                break
        
        return articles

    def _is_relevant_entry(self, entry, keywords: List[str]) -> bool:
        """Check if an RSS entry is relevant to the topic"""
        title_lower = entry.title.lower()
        summary_lower = getattr(entry, 'summary', '').lower()
        return any(keyword in title_lower or keyword in summary_lower for keyword in keywords)

    def _deduplicate_articles(self, articles: List[ArticleSource]) -> List[ArticleSource]:
        """Remove duplicate articles"""
        seen = set()
        unique = []
        for article in articles:
            if article.url not in seen:
                seen.add(article.url)
                unique.append(article)
        return sorted(unique, key=lambda x: x.confidence_score, reverse=True)


# Global article finder instance
article_finder = ArticleFinder()