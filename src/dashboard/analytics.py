#!/usr/bin/env python3
"""Real-time analytics dashboard for blog automation system."""

from datetime import datetime, timedelta
from typing import Any, Dict, List

from src.database.models import db_manager
from src.monitoring.metrics import metrics


class AnalyticsDashboard:
    """Provides real-time analytics and monitoring dashboard data."""
    
    def __init__(self):
        self.db = db_manager
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Compile comprehensive dashboard data."""
        return {
            'overview': self._get_overview_stats(),
            'content': self._get_content_stats(),
            'performance': self._get_performance_stats(),
            'quality': self._get_quality_stats(),
            'trends': self._get_trend_data(),
            'alerts': self._get_recent_alerts(),
            'system_health': self._get_system_health(),
            'last_updated': datetime.now().isoformat()
        }
    
    def _get_overview_stats(self) -> Dict[str, int | float]:
        """Calculate high-level overview statistics."""
        posts = self.db.get_blog_posts(limit=1000)
        
        if not posts:
            return {
                'total_posts': 0,
                'published_posts': 0,
                'draft_posts': 0,
                'total_words': 0,
                'avg_quality_score': 0.0,
                'weekly_growth': 0,
                'avg_words_per_post': 0
            }
        
        total_posts = len(posts)
        published_posts = sum(1 for p in posts if p.status == 'published')
        total_words = sum(p.word_count for p in posts)
        avg_quality = sum(p.quality_score for p in posts) / total_posts
        
        # Calculate weekly growth
        week_ago = datetime.now() - timedelta(days=7)
        weekly_growth = sum(
            1 for p in posts 
            if p.created_at and p.created_at >= week_ago
        )
        
        return {
            'total_posts': total_posts,
            'published_posts': published_posts,
            'draft_posts': total_posts - published_posts,
            'total_words': total_words,
            'avg_quality_score': round(avg_quality, 1),
            'weekly_growth': weekly_growth,
            'avg_words_per_post': round(total_words / total_posts)
        }
    
    def _get_content_stats(self) -> Dict[str, Any]:
        """Generate content quality and distribution statistics."""
        posts = self.db.get_blog_posts(limit=100)
        
        quality_ranges = {
            'excellent': 0, 
            'good': 0, 
            'fair': 0, 
            'poor': 0
        }
        
        word_count_ranges = {
            'short': 0, 
            'medium': 0, 
            'long': 0
        }
        
        for post in posts:
            # Quality distribution
            if post.quality_score >= 80:
                quality_ranges['excellent'] += 1
            elif post.quality_score >= 60:
                quality_ranges['good'] += 1
            elif post.quality_score >= 40:
                quality_ranges['fair'] += 1
            else:
                quality_ranges['poor'] += 1
            
            # Word count distribution
            if post.word_count < 500:
                word_count_ranges['short'] += 1
            elif post.word_count < 1000:
                word_count_ranges['medium'] += 1
            else:
                word_count_ranges['long'] += 1
        
        # Get recent posts (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        recent_posts = [
            p for p in posts 
            if p.created_at and p.created_at >= week_ago
        ]
        recent_posts.sort(key=lambda p: p.created_at, reverse=True)
        recent_posts = recent_posts[:10]  # Top 10 most recent
        
        return {
            'quality_distribution': quality_ranges,
            'word_count_distribution': word_count_ranges,
            'recent_posts': [
                {
                    'title': p.title,
                    'quality_score': p.quality_score,
                    'word_count': p.word_count,
                    'created_at': p.created_at.isoformat(),
                    'status': p.status
                } for p in recent_posts
            ]
        }
    
    def _get_performance_stats(self) -> Dict[str, float]:
        """Generate system performance statistics."""
        perf_metrics = metrics.get_metrics_summary(hours=24)
        
        # Extract key metrics
        ai_gen_time = perf_metrics.get(
            'content_generation.duration_ms', {}
        ).get('avg', 0)
        
        article_ext_time = perf_metrics.get(
            'article_extraction.duration_ms', {}
        ).get('avg', 0)
        
        success_count = perf_metrics.get(
            'content_generation.success.count', {}
        ).get('latest', 0)
        
        error_count = perf_metrics.get(
            'content_generation.error.count', {}
        ).get('latest', 0)
        
        # Calculate success rate
        total_operations = success_count + error_count
        success_rate = (
            (success_count / total_operations * 100) 
            if total_operations > 0 else 0.0
        )
        
        return {
            'avg_ai_generation_time_ms': round(ai_gen_time, 1),
            'avg_article_extraction_time_ms': round(article_ext_time, 1),
            'success_rate_percent': round(success_rate, 1),
            'total_operations_24h': total_operations,
            'error_count_24h': error_count
        }
    
    def _get_quality_stats(self) -> Dict[str, Any]:
        """Calculate content quality trends."""
        posts = self.db.get_blog_posts(limit=50)
        
        if not posts:
            return {
                'trend': 'no_data', 
                'average_score': 0, 
                'improvement': 0
            }
        
        # Filter posts with creation dates
        dated_posts = [p for p in posts if p.created_at]
        dated_posts.sort(key=lambda p: p.created_at)
        
        if len(dated_posts) < 2:
            return {
                'trend': 'insufficient_data',
                'average_score': posts[0].quality_score,
                'improvement': 0
            }
        
        # Split into older and newer halves
        split_index = len(dated_posts) // 2
        older = dated_posts[:split_index]
        newer = dated_posts[split_index:]
        
        older_avg = sum(p.quality_score for p in older) / len(older)
        newer_avg = sum(p.quality_score for p in newer) / len(newer)
        improvement = newer_avg - older_avg
        
        trend = 'stable'
        if improvement > 0.5:
            trend = 'improving'
        elif improvement < -0.5:
            trend = 'declining'
        
        return {
            'trend': trend,
            'average_score': round(newer_avg, 1),
            'improvement': round(improvement, 1),
            'sample_size': len(dated_posts)
        }
    
    def _get_trend_data(self) -> Dict[str, List]:
        """Generate trend data for visualization."""
        posts = self.db.get_blog_posts(limit=30)
        dated_posts = [p for p in posts if p.created_at]
        dated_posts.sort(key=lambda p: p.created_at)
        
        # Aggregate daily statistics
        daily_stats = {}
        for post in dated_posts:
            date_str = post.created_at.date().isoformat()
            if date_str not in daily_stats:
                daily_stats[date_str] = {
                    'count': 0, 
                    'quality_sum': 0, 
                    'word_sum': 0
                }
                
            daily_stats[date_str]['count'] += 1
            daily_stats[date_str]['quality_sum'] += post.quality_score
            daily_stats[date_str]['word_sum'] += post.word_count
        
        # Prepare last 14 days data
        dates = sorted(daily_stats.keys())[-14:]
        
        post_counts = [
            daily_stats[date]['count'] 
            for date in dates
        ]
        
        avg_quality = [
            daily_stats[date]['quality_sum'] / daily_stats[date]['count']
            for date in dates
        ]
        
        return {
            'dates': dates,
            'post_counts': post_counts,
            'avg_quality_scores': [round(q, 1) for q in avg_quality]
        }
    
    def _get_recent_alerts(self) -> List[Dict]:
        """Retrieve recent system alerts (placeholder implementation)."""
        # TODO: Integrate with actual alerting system
        return [
            {
                'level': 'info',
                'component': 'content_generator',
                'message': 'High quality content generated',
                'timestamp': datetime.now().isoformat()
            }
        ]
    
    def _get_system_health(self) -> Dict[str, Any]:
        """Retrieve current system health status."""
        from src.monitoring.health_check import health_checker
        
        health_status = health_checker.perform_health_check()
        
        return {
            'status': health_status.status,
            'response_time_ms': health_status.response_time_ms,
            'checks': {
                component: data.get('status', 'unknown')
                for component, data in health_status.checks.items()
            },
            'timestamp': health_status.timestamp
        }


# Global analytics dashboard instance
analytics_dashboard = AnalyticsDashboard()