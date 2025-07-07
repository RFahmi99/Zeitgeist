import asyncio
import asyncpraw
import logging
import os
import time
from dataclasses import dataclass
from typing import List, Optional
from difflib import SequenceMatcher

import feedparser
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Fallback topics for when trend detection fails
FALLBACK_TOPICS = [
    "Artificial Intelligence breakthroughs",
    "Climate change solutions",
    "Technology innovations",
    "Space exploration updates",
    "Healthcare advances",
    "Economic trends",
    "Cybersecurity developments",
    "Renewable energy progress",
    "Social media trends",
    "Digital transformation"
]


@dataclass
class TrendingTopic:
    title: str
    source: str
    category: str
    search_volume: Optional[int] = None
    timestamp: float = None
    confidence_score: float = 0.0


class TrendDetector:
    """Multi-source trending topic detection system"""
    
    def __init__(self):
        self.sources = {
            'google_trends': self._get_google_trends,
            'reddit': self._get_reddit_trends,
            'news_feeds': self._get_news_trends,
            'buzzfeed': self._get_buzzfeed_trends
        }

    async def get_trending_topics(self, limit: int = 10) -> List[TrendingTopic]:
        """Get trending topics from all sources"""
        all_trends = []
        
        for source_name, source_func in self.sources.items():
            try:
                logger.info(f"Fetching trends from {source_name}")
                trends = await self._fetch_source(source_func)
                all_trends.extend(trends)
            except Exception as e:
                logger.error(f"Failed to fetch from {source_name}: {e}")
        
        unique_trends = self._deduplicate_trends(all_trends)
        return sorted(unique_trends, key=lambda x: x.confidence_score, reverse=True)[:limit]
    
    async def _fetch_source(self, source_func):
        """Fetch trends from a source with async support"""
        if asyncio.iscoroutinefunction(source_func):
            return await source_func()
        return source_func()

    def _get_google_trends(self) -> List[TrendingTopic]:
        """Google Trends with RSS and scraping fallback"""
        try:
            return self._parse_google_rss()
        except Exception as e:
            logger.warning(f"Google Trends RSS failed: {e}")
            return self._scrape_google_trends()

    def _parse_google_rss(self) -> List[TrendingTopic]:
        """Parse Google Trends RSS feed"""
        trends = []
        rss_url = "https://trends.google.com/trending/rss?geo=US"
        feed = feedparser.parse(rss_url)
        
        for entry in feed.entries[:5]:
            trends.append(TrendingTopic(
                title=entry.title,
                source="google_trends_rss",
                category="general",
                confidence_score=0.9,
                timestamp=time.time()
            ))
        return trends

    def _scrape_google_trends(self) -> List[TrendingTopic]:
        """Scrape Google Trends as fallback"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(
                "https://trends.google.com/trends/trendingsearches/daily", 
                headers=headers, 
                timeout=10
            )
            if response.status_code == 200:
                # Add parsing logic for trending searches
                return []
        except Exception as e:
            logger.warning(f"Google Trends scraping failed: {e}")
        return []

    async def _get_reddit_trends(self) -> List[TrendingTopic]:
        """Get trending topics from Reddit"""
        try:
            import asyncpraw
            return await self._fetch_reddit_trends()
        except ImportError:
            logger.error("asyncpraw not installed")
            return []
        except Exception as e:
            logger.error(f"Reddit API failed: {e}")
            return []

    async def _fetch_reddit_trends(self) -> List[TrendingTopic]:
        """Fetch trends from Reddit using asyncpraw"""
        reddit = asyncpraw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent='script:your-script-name:v1.0'
        )
        
        try:
            return await self._process_reddit_subs(reddit)
        finally:
            try:
                await reddit.close()
                logger.debug("Reddit connection closed")
            except Exception:
                pass

    async def _process_reddit_subs(self, reddit) -> List[TrendingTopic]:
        """Process Reddit subreddits for trending topics"""
        trends = []
        subreddits = ['technology', 'worldnews', 'science', 'business']
        
        for subreddit_name in subreddits:
            try:
                subreddit = await reddit.subreddit(subreddit_name)
                async for post in subreddit.hot(limit=3):
                    trends.append(TrendingTopic(
                        title=post.title,
                        source=f"reddit_{subreddit_name}",
                        category=subreddit_name,
                        confidence_score=min(post.score / 1000, 1.0),
                        timestamp=time.time()
                    ))
            except Exception as e:
                logger.warning(f"Failed r/{subreddit_name}: {e}")
        return trends

    def _get_news_trends(self) -> List[TrendingTopic]:
        """Get trending topics from news RSS feeds"""
        trends = []
        news_feeds = [
            "https://feeds.reuters.com/Reuters/worldNews",
            "https://rss.cnn.com/rss/edition.rss",
            "https://feeds.bbci.co.uk/news/world/rss.xml"
        ]
        
        for feed_url in news_feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:3]:
                    trends.append(TrendingTopic(
                        title=entry.title,
                        source="news_feed",
                        category="news",
                        confidence_score=0.8,
                        timestamp=time.time()
                    ))
            except Exception as e:
                logger.warning(f"News feed failed: {feed_url} - {e}")
        return trends

    def _get_buzzfeed_trends(self) -> List[TrendingTopic]:
        """Get trending topics from BuzzFeed"""
        try:
            rss_url = "https://www.buzzfeed.com/trending.xml"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(rss_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return self._parse_buzzfeed_feed(response.content)
            logger.warning(f"BuzzFeed status: {response.status_code}")
        except Exception as e:
            logger.warning(f"BuzzFeed failed: {e}")
        return []

    def _parse_buzzfeed_feed(self, content) -> List[TrendingTopic]:
        """Parse BuzzFeed RSS content"""
        trends = []
        feed = feedparser.parse(content)
        for entry in feed.entries[:3]:
            trends.append(TrendingTopic(
                title=entry.title,
                source="buzzfeed",
                category="entertainment",
                confidence_score=0.6,
                timestamp=time.time()
            ))
        return trends

    def _deduplicate_trends(self, trends: List[TrendingTopic]) -> List[TrendingTopic]:
        """Remove duplicate trends based on title similarity"""
        from difflib import SequenceMatcher
        
        unique_trends = []
        for trend in trends:
            if not self._is_duplicate(trend, unique_trends):
                unique_trends.append(trend)
        return unique_trends

    def _is_duplicate(self, trend, unique_trends) -> bool:
        """Check if trend is a duplicate"""
        for unique in unique_trends:
            similarity = SequenceMatcher(
                None, 
                trend.title.lower(), 
                unique.title.lower()
            ).ratio()
            
            if similarity > 0.7:
                if trend.confidence_score > unique.confidence_score:
                    unique_trends.remove(unique)
                    unique_trends.append(trend)
                return True
        return False


# Global trend detector
trend_detector = TrendDetector()


async def get_trending_topics(n=5) -> List[str]:
    """Get trending topics with fallback"""
    try:
        trends = await trend_detector.get_trending_topics(limit=n)
        return [trend.title for trend in trends]
    except Exception as e:
        logger.error(f"Trend detection failed: {e}")
        return FALLBACK_TOPICS[:n]