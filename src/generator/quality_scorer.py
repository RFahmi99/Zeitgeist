#!/usr/bin/env python3
"""AI-powered content quality scoring system."""

import logging
import re
import statistics
from dataclasses import dataclass
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class QualityScore:
    """Comprehensive quality assessment of content."""
    overall_score: float
    readability_score: float
    seo_score: float
    engagement_score: float
    technical_score: float
    details: Dict[str, any]
    recommendations: List[str]


class ContentQualityScorer:
    """Performs comprehensive content quality analysis."""
    
    def __init__(self):
        self.min_word_count = 300
        self.max_word_count = 2000
        self.target_word_count = 800
    
    def score_content(self, content: str, title: str = "") -> QualityScore:
        """Perform comprehensive content quality analysis."""
        # Analyze different aspects
        readability_score, readability_details = self.analyze_readability(content)
        seo_score, seo_details = self.analyze_seo_factors(content, title)
        engagement_score, engagement_details = self.analyze_engagement_factors(content)
        technical_score, technical_details = self.analyze_technical_quality(content)
        
        # Calculate overall weighted score
        overall_score = self._calculate_overall_score(
            readability_score,
            seo_score,
            engagement_score,
            technical_score
        )
        
        # Generate recommendations
        recommendations = self.generate_recommendations(
            readability_score,
            seo_score,
            engagement_score,
            technical_score,
            {
                "readability": readability_details,
                "seo": seo_details,
                "engagement": engagement_details,
                "technical": technical_details
            }
        )
        
        return QualityScore(
            overall_score=round(overall_score, 1),
            readability_score=round(readability_score, 1),
            seo_score=round(seo_score, 1),
            engagement_score=round(engagement_score, 1),
            technical_score=round(technical_score, 1),
            details={
                "readability": readability_details,
                "seo": seo_details,
                "engagement": engagement_details,
                "technical": technical_details
            },
            recommendations=recommendations
        )
    
    def _calculate_overall_score(
        self,
        readability: float,
        seo: float,
        engagement: float,
        technical: float
    ) -> float:
        """Calculate weighted overall score."""
        weights = {
            "readability": 0.25,
            "seo": 0.30,
            "engagement": 0.25,
            "technical": 0.20
        }
        return sum([
            readability * weights["readability"],
            seo * weights["seo"],
            engagement * weights["engagement"],
            technical * weights["technical"]
        ])

    def analyze_readability(self, content: str) -> Tuple[float, Dict]:
        """Analyze content readability using multiple metrics."""
        clean_content = self._clean_content(content)
        
        if not clean_content:
            return 0.0, {"error": "No content to analyze"}
            
        words = clean_content.split()
        sentences = self._split_sentences(clean_content)
        
        if not sentences:
            return 0.0, {"error": "No sentences found"}
        
        word_count = len(words)
        sentence_count = len(sentences)
        syllable_count = sum(self._count_syllables(word) for word in words)
        
        # Calculate readability metrics
        avg_sentence_length = word_count / sentence_count
        avg_syllables_per_word = syllable_count / word_count
        
        # Flesch Reading Ease Score
        flesch_score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
        readability_score = max(0, min(100, flesch_score))
        
        return readability_score, {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_sentence_length": round(avg_sentence_length, 2),
            "avg_syllables_per_word": round(avg_syllables_per_word, 2),
            "flesch_score": round(flesch_score, 2),
            "readability_level": self._get_readability_level(flesch_score)
        }
    
    def _clean_content(self, content: str) -> str:
        """Remove markdown formatting for analysis."""
        return re.sub(r'[#*\[\]()]', '', content)
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        return [
            s.strip() for s in re.split(r'[.!?]+', text) 
            if s.strip()
        ]
    
    def analyze_seo_factors(self, content: str, title: str) -> Tuple[float, Dict]:
        """Analyze SEO-related factors."""
        score_components = []
        details = {}
        
        # Title analysis
        title_length = len(title)
        title_score = self._calculate_title_score(title_length)
        score_components.append(title_score)
        details.update({
            "title_length": title_length,
            "title_score": round(title_score, 1)
        })
        
        # Content length analysis
        word_count = len(content.split())
        length_score = self._calculate_length_score(word_count)
        score_components.append(length_score)
        details.update({
            "word_count": word_count,
            "length_score": round(length_score, 1)
        })
        
        # Header structure analysis
        headers = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
        header_score = min(100, len(headers) * 20)  # Reward up to 5 headers
        score_components.append(header_score)
        details.update({
            "header_count": len(headers),
            "header_score": round(header_score, 1)
        })
        
        # Keyword density analysis
        density_score = self._calculate_density_score(content)
        score_components.append(density_score)
        details["density_score"] = round(density_score, 1)
        
        return statistics.mean(score_components), details
    
    def _calculate_title_score(self, length: int) -> float:
        """Calculate SEO score based on title length."""
        if 30 <= length <= 60:
            return 100.0
        return max(0.0, 100.0 - abs(length - 45) * 2)
    
    def _calculate_length_score(self, word_count: int) -> float:
        """Calculate score based on content length."""
        if self.min_word_count <= word_count <= self.max_word_count:
            return 100.0 - abs(word_count - self.target_word_count) / 10
        return max(0.0, 50.0 - abs(word_count - self.target_word_count) / 20)
    
    def _calculate_density_score(self, content: str) -> float:
        """Calculate keyword density score."""
        words = [w for w in content.lower().split() if len(w) > 3]
        if not words:
            return 0.0
            
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        max_frequency = max(word_freq.values())
        keyword_density = (max_frequency / len(words)) * 100
        
        if keyword_density < 3:
            return 100.0
        if keyword_density < 5:
            return 80.0
        return max(0.0, 100.0 - (keyword_density - 5) * 10)
    
    def analyze_engagement_factors(self, content: str) -> Tuple[float, Dict]:
        """Analyze factors that affect reader engagement."""
        score_components = []
        details = {}
        
        # Question analysis
        questions = len(re.findall(r'\?', content))
        question_score = min(100, questions * 15)  # Reward up to ~7 questions
        score_components.append(question_score)
        details["question_count"] = questions
        
        # List usage analysis
        list_items = self._count_list_items(content)
        list_score = min(100, list_items * 10)
        score_components.append(list_score)
        details["list_items"] = list_items
        
        # Call-to-action analysis
        cta_count = self._count_cta_phrases(content)
        cta_score = min(100, cta_count * 25)
        score_components.append(cta_score)
        details["cta_phrases"] = cta_count
        
        return statistics.mean(score_components), details
    
    def _count_list_items(self, content: str) -> int:
        """Count all list items in content."""
        bullet_lists = len(re.findall(r'^\s*[-*+]\s+', content, re.MULTILINE))
        numbered_lists = len(re.findall(r'^\s*\d+\.\s+', content, re.MULTILINE))
        return bullet_lists + numbered_lists
    
    def _count_cta_phrases(self, content: str) -> int:
        """Count call-to-action phrases."""
        patterns = [
            r'\b(learn more|read more|find out|discover|explore)\b',
            r'\b(try|start|begin|get started)\b',
            r'\b(download|subscribe|follow|share)\b'
        ]
        return sum(
            len(re.findall(pattern, content, re.IGNORECASE)) 
            for pattern in patterns
        )
    
    def analyze_technical_quality(self, content: str) -> Tuple[float, Dict]:
        """Analyze technical aspects of content quality."""
        score_components = []
        details = {}
        
        # Markdown formatting analysis
        formatting_score = self._calculate_formatting_score(content)
        score_components.append(min(100, formatting_score))
        
        # Content structure analysis
        structure_score = self._calculate_structure_score(content)
        score_components.append(structure_score)
        details["paragraph_count"] = self._count_meaningful_paragraphs(content)
        
        return statistics.mean(score_components), details
    
    def _calculate_formatting_score(self, content: str) -> int:
        """Calculate score based on markdown usage."""
        elements = [
            (r'#{1,6}\s+', 20),  # Headers
            (r'\*\*[^*]+\*\*', 20),  # Bold text
            (r'\*[^*]+\*', 20),  # Italic text
            (r'`[^`]+`', 20),  # Code blocks
            (r'\[.+\]\(.+\)', 20)  # Links
        ]
        
        score = 0
        for pattern, points in elements:
            if re.search(pattern, content):
                score += points
        return score
    
    def _count_meaningful_paragraphs(self, content: str) -> int:
        """Count paragraphs with meaningful content."""
        paragraphs = content.split('\n\n')
        return len([p for p in paragraphs if len(p.strip()) > 50])
    
    def _calculate_structure_score(self, content: str) -> float:
        """Calculate structure score based on paragraph count."""
        paragraph_count = self._count_meaningful_paragraphs(content)
        if paragraph_count >= 3:
            return 100.0
        if paragraph_count >= 2:
            return 75.0
        return 50.0
    
    def generate_recommendations(
        self,
        readability: float,
        seo: float,
        engagement: float,
        technical: float,
        details: Dict[str, Dict]
    ) -> List[str]:
        """Generate actionable recommendations for improvement."""
        recommendations = []
        
        # Readability recommendations
        if readability < 60:
            recommendations.append(
                "Improve readability by shortening sentences and using simpler words"
            )
        
        # SEO recommendations
        seo_details = details["seo"]
        if seo_details.get("title_length", 0) < 30:
            recommendations.append(
                "Lengthen title to 30-60 characters for better SEO"
            )
        elif seo_details.get("title_length", 0) > 60:
            recommendations.append(
                "Shorten title to under 60 characters for better SEO"
            )
        
        word_count = seo_details.get("word_count", 0)
        if word_count < self.min_word_count:
            recommendations.append(
                f"Increase content length to at least {self.min_word_count} words"
            )
        elif word_count > self.max_word_count:
            recommendations.append(
                f"Consider shortening content to under {self.max_word_count} words"
            )
        
        if seo_details.get("header_count", 0) < 3:
            recommendations.append(
                "Add more headers (H2, H3) to improve content structure"
            )
        
        # Engagement recommendations
        engagement_details = details["engagement"]
        if engagement_details.get("question_count", 0) == 0:
            recommendations.append(
                "Add questions to increase reader engagement"
            )
        
        if engagement_details.get("list_items", 0) < 3:
            recommendations.append(
                "Add bullet points or numbered lists to improve readability"
            )
        
        # Technical recommendations
        if details["technical"].get("paragraph_count", 0) < 3:
            recommendations.append(
                "Break content into more paragraphs for better structure"
            )
        
        return recommendations
    
    def _count_syllables(self, word: str) -> int:
        """Estimate syllable count for a word."""
        word = word.lower()
        vowels = "aeiouy"
        count = 0
        prev_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        
        # Handle silent 'e'
        if word.endswith('e') and count > 1:
            count -= 1
        
        return max(1, count)
    
    def _get_readability_level(self, flesch_score: float) -> str:
        """Get readability level description from Flesch score."""
        if flesch_score >= 90:
            return "Very Easy"
        if flesch_score >= 80:
            return "Easy"
        if flesch_score >= 70:
            return "Fairly Easy"
        if flesch_score >= 60:
            return "Standard"
        if flesch_score >= 50:
            return "Fairly Difficult"
        if flesch_score >= 30:
            return "Difficult"
        return "Very Difficult"


# Global quality scorer instance
quality_scorer = ContentQualityScorer()