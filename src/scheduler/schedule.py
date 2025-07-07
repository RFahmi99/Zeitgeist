#!/usr/bin/env python3

import asyncio
import logging
import time
import traceback
from urllib.parse import urlparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.aggregator.article_fetcher import async_fetcher
from src.aggregator.dedup_engine import dedup_engine
from src.generator.generate_post import ai_generator
from src.publisher.post_to_site import save_blog_to_database_and_files
from src.trends.detect import FALLBACK_TOPICS, trend_detector
from src.trends.search import article_finder

logger = logging.getLogger(__name__)


class BlogScheduler:
    """Scheduler for automated blog generation with resource management"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._shutdown_requested = False
        self.stats = {
            'total_runs': 0,
            'successful_posts': 0,
            'failed_posts': 0,
            'last_run': None,
            'errors': []
        }

    async def blog_generation_task(self):
        """Main blog generation workflow"""
        if self._shutdown_requested:
            logger.info("Skipping blog generation: shutdown requested")
            return

        run_start = time.time()
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.stats['total_runs'] += 1
        self.stats['last_run'] = datetime.now()

        logger.info(f"Starting blog generation: {run_id}")

        try:
            trending_topics = await self._get_trending_topics()
            successful_posts = 0

            for i, trend in enumerate(trending_topics):
                if self._shutdown_requested:
                    logger.info("Stopping topic processing: shutdown requested")
                    break

                topic_title = trend.title if hasattr(trend, 'title') else str(trend)
                logger.info(f"Processing topic {i+1}/{len(trending_topics)}: {topic_title}")

                if not await self._process_topic(topic_title):
                    continue

                successful_posts += 1
                self.stats['successful_posts'] += 1
                logger.info(f"Published blog for: {topic_title}")

                if not self._shutdown_requested:
                    await asyncio.sleep(30)  # Rate limiting

            total_time = time.time() - run_start
            logger.info(f"Task completed: {run_id} - {successful_posts} posts in {total_time:.2f}s")
            await self._cleanup_history()

        except Exception as e:
            logger.critical(f"Critical error: {e}\n{traceback.format_exc()}")

        finally:
            await self._post_run_cleanup()

    async def _get_trending_topics(self) -> List[str]:
        """Get trending topics with fallback"""
        logger.info("Fetching trending topics...")
        topics = await trend_detector.get_trending_topics(limit=5)
        if not topics:
            logger.warning("Using fallback topics")
            return self._get_fallback_topics()
        return topics

    async def _process_topic(self, topic: str) -> bool:
        """Process a single topic through the pipeline"""
        try:
            if not dedup_engine.check_content_before_generation(topic, []):
                logger.info(f"Skipping duplicate: {topic}")
                return False

            article_urls = await article_finder.find_articles(topic, limit=8)
            if not article_urls:
                logger.warning(f"No articles found: {topic}")
                return False

            extracted = await self._extract_articles(article_urls)
            if not extracted['valid_articles']:
                logger.warning(f"No valid content: {topic}")
                return False

            blog_content = await self._generate_content(
                topic, 
                extracted['texts'], 
                extracted['urls']
            )

            if not blog_content or blog_content.startswith("Error:"):
                logger.error(f"Content generation failed: {topic}")
                self.stats['failed_posts'] += 1
                return False

            await self._publish_content(
                blog_content, 
                topic,
                extracted['sources'],
                extracted['urls']
            )
            dedup_engine.add_content(topic, blog_content)
            return True

        except Exception as e:
            logger.error(f"Error processing {topic}: {e}")
            self.stats['errors'].append({
                'topic': topic,
                'error': str(e),
                'timestamp': datetime.now(),
                'traceback': traceback.format_exc()
            })
            self.stats['failed_posts'] += 1
            return False

    async def _extract_articles(self, urls: List[str]) -> Dict:
        """Extract articles with retry logic"""
        for attempt in range(3):
            try:
                results = await async_fetcher.extract_multiple_articles(urls)
                return self._process_extraction_results(results)
            except Exception as e:
                logger.warning(f"Extraction attempt {attempt+1} failed: {e}")
                if attempt < 2:
                    await self._cleanup_sessions()
                    await asyncio.sleep(15 * (attempt + 1))
        
        return {'texts': [], 'urls': [], 'sources': [], 'valid_articles': False}

    def _process_extraction_results(self, results) -> Dict:
        """Process article extraction results"""
        valid_articles = []
        valid_urls = []
        source_metadata = []
        
        for url, title, content in results:
            if not content or len(content.split()) <= 200:
                continue
                
            valid_articles.append(content)
            valid_urls.append(url)
            source_metadata.append(self._create_source_metadata(url, title))
        
        return {
            'texts': valid_articles,
            'urls': valid_urls,
            'sources': source_metadata,
            'valid_articles': bool(valid_articles)
        }

    def _create_source_metadata(self, url: str, title: str) -> Dict:
        """Create metadata for a source"""
        domain = urlparse(url).netloc.replace('www.', '') if url else 'Unknown'
        clean_title = title[:100].strip() if title and not title.startswith('Error:') else f'Article from {domain}'
        
        return {
            'url': url or 'Unknown',
            'title': clean_title,
            'domain': domain,
            'extracted_at': datetime.now().isoformat()
        }

    async def _generate_content(self, title: str, sources: List[str], urls: List[str]) -> Optional[str]:
        """Generate content with retry logic"""
        for attempt in range(3):
            try:
                result = await ai_generator.generate_content(title, sources, urls)
                if result and result.validation_passed:
                    return result.content
            except Exception as e:
                logger.warning(f"Generation attempt {attempt+1} failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(15 * (attempt + 1))
        return None

    async def _publish_content(self, content: str, title: str, sources: List[Dict], urls: List[str]):
        """Publish generated content"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, 
                save_blog_to_database_and_files, 
                content, title, sources, urls
            )
        except Exception as e:
            logger.error(f"Publish failed for '{title}': {e}")
            raise

    async def _cleanup_sessions(self):
        """Cleanup sessions before retry"""
        try:
            logger.info("Cleaning up sessions...")
            await async_fetcher.cleanup()
            await asyncio.sleep(2.0)
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    async def _post_run_cleanup(self):
        """Cleanup after each run"""
        try:
            logger.info("Running post-run cleanup...")
            await async_fetcher.cleanup()
            await asyncio.sleep(1.0)
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    async def _cleanup_history(self):
        """Cleanup old statistics"""
        try:
            if len(self.stats['errors']) > 100:
                self.stats['errors'] = self.stats['errors'][-50:]
        except Exception as e:
            logger.error(f"History cleanup error: {e}")

    def _get_fallback_topics(self) -> List[str]:
        """Get fallback topics"""
        try:
            return FALLBACK_TOPICS[:5]
        except Exception:
            return [
                "Technology trends",
                "Climate solutions", 
                "AI advances",
                "Digital transformation",
                "Future of work"
            ]

    def start_scheduling(self):
        """Start scheduled tasks"""
        self.scheduler.add_job(
            self.blog_generation_task,
            CronTrigger(minute=0, hour='*/6'),
            id='main_blog_generation',
            max_instances=1
        )

        self.scheduler.add_job(
            self._daily_maintenance,
            CronTrigger(hour=2, minute=0),
            id='daily_maintenance'
        )

        self.scheduler.add_job(
            self._weekly_cleanup,
            CronTrigger(day_of_week='sun', hour=3, minute=0),
            id='weekly_cleanup'
        )

        self.scheduler.start()
        logger.info("Scheduler started")

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Initiating shutdown...")
        self._shutdown_requested = True

        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")

        await self._post_run_cleanup()
        logger.info("Shutdown completed")

    async def _daily_maintenance(self):
        """Daily maintenance tasks"""
        logger.info("Running daily maintenance")
        try:
            dedup_engine.cleanup_old_fingerprints(days=30)
            if len(self.stats['errors']) > 100:
                self.stats['errors'] = self.stats['errors'][-50:]
        except Exception as e:
            logger.error(f"Maintenance error: {e}")

    async def _weekly_cleanup(self):
        """Weekly cleanup tasks"""
        logger.info("Running weekly cleanup")
        try:
            dedup_engine.cleanup_old_fingerprints(days=60)
            
            if self.stats['total_runs'] > 5000:
                for key in ['total_runs', 'successful_posts', 'failed_posts']:
                    self.stats[key] = min(self.stats[key], 100)
        except Exception as e:
            logger.error(f"Weekly cleanup error: {e}")

    def get_stats(self) -> Dict:
        """Get current statistics"""
        return {
            'total_runs': self.stats['total_runs'],
            'successful_posts': self.stats['successful_posts'],
            'failed_posts': self.stats['failed_posts'],
            'last_run': self.stats['last_run'].isoformat() if self.stats['last_run'] else None,
            'success_rate': (self.stats['successful_posts'] / max(1, self.stats['total_runs'])) * 100,
            'recent_errors': len(self.stats['errors'])
        }


# Global scheduler instance
blog_scheduler = BlogScheduler()

__all__ = ['blog_scheduler', 'BlogScheduler']