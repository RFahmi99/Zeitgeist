#!/usr/bin/env python3
"""Content deduplication and similarity detection system."""

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Dict, List, Set, Tuple

logger = logging.getLogger(__name__)

# Common stop words for text normalization
STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of',
    'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
    'after', 'above', 'below', 'under', 'between', 'among', 'amongst',
    'throughout', 'within', 'without', 'toward', 'towards', 'until', 'unless',
    'since', 'while', 'because', 'although', 'though', 'if', 'whether', 'when',
    'where', 'who', 'whom', 'whose', 'which', 'what', 'how', 'why', 'this',
    'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me',
    'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our',
    'their', 'mine', 'yours', 'hers', 'ours', 'theirs'
}

DATA_DIR = "data"
FINGERPRINT_FILE = os.path.join(DATA_DIR, "content_fingerprints.json")
os.makedirs(DATA_DIR, exist_ok=True)


@dataclass
class ContentFingerprint:
    """Represents content fingerprint for deduplication."""
    content_hash: str
    title_hash: str
    similarity_hash: str
    word_count: int
    timestamp: datetime
    title: str
    url: str = ""


class ContentDeduplicator:
    """Advanced content deduplication system with similarity detection."""
    
    def __init__(self, similarity_threshold: float = 0.8):
        self.similarity_threshold = similarity_threshold
        self.fingerprints: Dict[str, ContentFingerprint] = {}
        self.title_cache: Set[str] = set()
        self.content_cache: Set[str] = set()
        self._load_fingerprints()
    
    def _load_fingerprints(self):
        """Load existing fingerprints from storage file."""
        if not os.path.exists(FINGERPRINT_FILE):
            return
            
        try:
            with open(FINGERPRINT_FILE, 'r') as file:
                data = json.load(file)
                
            for item in data:
                fingerprint = ContentFingerprint(
                    content_hash=item['content_hash'],
                    title_hash=item['title_hash'],
                    similarity_hash=item['similarity_hash'],
                    word_count=item['word_count'],
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    title=item['title'],
                    url=item.get('url', '')
                )
                self._add_to_cache(fingerprint)
            
            logger.info(
                f"Loaded {len(self.fingerprints)} content fingerprints"
            )
        except Exception as error:
            logger.error(f"Error loading fingerprints: {error}")
    
    def _save_fingerprints(self):
        """Persist fingerprints to storage file."""
        try:
            data = [
                {
                    'content_hash': fp.content_hash,
                    'title_hash': fp.title_hash,
                    'similarity_hash': fp.similarity_hash,
                    'word_count': fp.word_count,
                    'timestamp': fp.timestamp.isoformat(),
                    'title': fp.title,
                    'url': fp.url
                }
                for fp in self.fingerprints.values()
            ]
            
            with open(FINGERPRINT_FILE, 'w') as file:
                json.dump(data, file, indent=2)
        except Exception as error:
            logger.error(f"Error saving fingerprints: {error}")
    
    def _add_to_cache(self, fingerprint: ContentFingerprint):
        """Add fingerprint to all caches."""
        self.fingerprints[fingerprint.content_hash] = fingerprint
        self.title_cache.add(fingerprint.title_hash)
        self.content_cache.add(fingerprint.content_hash)
    
    def _remove_from_cache(self, fingerprint: ContentFingerprint):
        """Remove fingerprint from all caches."""
        self.fingerprints.pop(fingerprint.content_hash, None)
        self.title_cache.discard(fingerprint.title_hash)
        self.content_cache.discard(fingerprint.content_hash)
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison by removing noise."""
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)          # Collapse whitespace
        text = re.sub(r'[^\w\s]', '', text)       # Remove punctuation
        words = [
            word for word in text.split() 
            if word not in STOP_WORDS and len(word) > 2
        ]
        return ' '.join(words)
    
    def _create_similarity_hash(self, text: str) -> str:
        """Create hash for similarity detection using word shingles."""
        normalized = self._normalize_text(text)
        words = normalized.split()
        
        # Generate 3-word shingles
        shingles = {
            ' '.join(words[i:i+3])
            for i in range(len(words) - 2)
        }
        
        sorted_shingles = sorted(shingles)
        shingle_text = '|'.join(sorted_shingles)
        return hashlib.md5(shingle_text.encode()).hexdigest()
    
    def _create_content_fingerprint(
        self, 
        title: str, 
        content: str, 
        url: str = ""
    ) -> ContentFingerprint:
        """Create comprehensive content fingerprint."""
        # Clean content for fingerprinting
        clean_content = re.sub(r'[#*\[\]()]', '', content)  # Remove markdown
        clean_content = re.sub(r'http[s]?://\S+', '', clean_content)  # Remove URLs
        
        return ContentFingerprint(
            content_hash=hashlib.sha256(clean_content.encode()).hexdigest(),
            title_hash=hashlib.sha256(title.lower().encode()).hexdigest(),
            similarity_hash=self._create_similarity_hash(clean_content),
            word_count=len(clean_content.split()),
            timestamp=datetime.now(),
            title=title,
            url=url
        )
    
    def is_duplicate_title(self, title: str) -> bool:
        """Check if title exists in the cache."""
        title_hash = hashlib.sha256(title.lower().encode()).hexdigest()
        return title_hash in self.title_cache
    
    def is_duplicate_content(self, content: str) -> bool:
        """Check if exact content exists in the cache."""
        clean_content = re.sub(r'[#*\[\]()]', '', content)
        content_hash = hashlib.sha256(clean_content.encode()).hexdigest()
        return content_hash in self.content_cache
    
    def find_similar_content(
        self, 
        title: str, 
        content: str
    ) -> List[Tuple[ContentFingerprint, float]]:
        """
        Find similar content based on multiple similarity metrics.
        
        Returns:
            List of matching fingerprints with similarity scores
        """
        fingerprint = self._create_content_fingerprint(title, content)
        similar_content = []
        
        for existing_fp in self.fingerprints.values():
            if existing_fp.content_hash == fingerprint.content_hash:
                continue  # Skip exact duplicates
            
            similarity_score = self._calculate_similarity(
                fingerprint, 
                existing_fp, 
                title
            )
            
            if similarity_score >= self.similarity_threshold:
                similar_content.append((existing_fp, similarity_score))
        
        # Sort by descending similarity
        similar_content.sort(key=lambda x: x[1], reverse=True)
        return similar_content
    
    def _calculate_similarity(
        self, 
        new_fp: ContentFingerprint, 
        existing_fp: ContentFingerprint, 
        title: str
    ) -> float:
        """Calculate weighted similarity score between fingerprints."""
        similarity_metrics = []
        
        # 1. Similarity hash comparison
        similarity_metrics.append(
            1.0 if new_fp.similarity_hash == existing_fp.similarity_hash else 0.0
        )
        
        # 2. Title similarity
        title_similarity = SequenceMatcher(
            None, 
            title.lower(), 
            existing_fp.title.lower()
        ).ratio()
        similarity_metrics.append(title_similarity)
        
        # 3. Content length similarity
        word_count_diff = abs(existing_fp.word_count - new_fp.word_count)
        max_word_count = max(existing_fp.word_count, new_fp.word_count)
        length_similarity = (
            1.0 - (word_count_diff / max_word_count) 
            if max_word_count > 0 else 0.0
        )
        similarity_metrics.append(length_similarity)
        
        # Weighted average of metrics
        weights = [0.5, 0.3, 0.2]  # Prioritize content similarity
        return sum(
            metric * weight 
            for metric, weight in zip(similarity_metrics, weights)
        )
    
    def add_content(
        self, 
        title: str, 
        content: str, 
        url: str = ""
    ) -> bool:
        """
        Add content to deduplication database after verification.
        
        Returns:
            True if content was added, False if duplicate/similar exists
        """
        fingerprint = self._create_content_fingerprint(title, content, url)
        
        if fingerprint.content_hash in self.content_cache:
            logger.warning(f"Exact duplicate content: {title}")
            return False
        
        if fingerprint.title_hash in self.title_cache:
            logger.warning(f"Duplicate title: {title}")
            return False
        
        similar = self.find_similar_content(title, content)
        if similar:
            self._log_similar_content(title, similar)
            return False
        
        self._add_to_cache(fingerprint)
        self._save_fingerprints()
        logger.info(f"Added content fingerprint: {title}")
        return True
    
    def _log_similar_content(
        self, 
        title: str, 
        similar: List[Tuple[ContentFingerprint, float]]
    ):
        """Log similar content matches."""
        logger.warning(
            f"Similar content detected for '{title}': {len(similar)} matches"
        )
        for similar_fp, similarity in similar[:3]:  # Top 3 matches
            logger.warning(
                f"  - Similar to '{similar_fp.title}' (score: {similarity:.2f})"
            )
    
    def check_content_before_generation(
        self, 
        title: str, 
        sources: List[str]
    ) -> bool:
        """
        Check if content should be generated based on source similarity.
        
        Returns:
            True if no similar content exists, False otherwise
        """
        combined_sources = ' '.join(sources[:3])  # Use first 3 sources
        pseudo_content = f"{title}\n\n{combined_sources[:1000]}"  # Truncated
        
        similar = self.find_similar_content(title, pseudo_content)
        if similar:
            logger.info(
                f"Skipping generation for '{title}' - similar content exists"
            )
            return False
        return True
    
    def cleanup_old_fingerprints(self, days: int = 90):
        """Remove fingerprints older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        old_fingerprints = [
            fp for fp in self.fingerprints.values() 
            if fp.timestamp < cutoff
        ]
        
        for fp in old_fingerprints:
            self._remove_from_cache(fp)
        
        if old_fingerprints:
            self._save_fingerprints()
            logger.info(f"Cleaned {len(old_fingerprints)} old fingerprints")
    
    def get_stats(self) -> Dict[str, int | float]:
        """Get deduplication system statistics."""
        now = datetime.now()
        recent_count = sum(
            1 for fp in self.fingerprints.values()
            if (now - fp.timestamp).days <= 7
        )
        
        return {
            'total_fingerprints': len(self.fingerprints),
            'recent_fingerprints_7d': recent_count,
            'title_cache_size': len(self.title_cache),
            'content_cache_size': len(self.content_cache),
            'similarity_threshold': self.similarity_threshold
        }


# Global deduplication engine instance
dedup_engine = ContentDeduplicator()