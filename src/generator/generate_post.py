# src/generator/generate_post.py
"""Content generation module for blog automation system."""

import asyncio
import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from config import config

logger = logging.getLogger(__name__)


@dataclass
class ContentResult:
    """Result of content generation process."""
    content: str
    word_count: int
    quality_score: float
    generation_time: float
    strategy_used: str
    validation_passed: bool


class ContentValidator:
    """Validates generated content against quality standards."""
    
    QUALITY_INDICATORS = [
        "introduction", "conclusion", "analysis", "overview", "summary",
        "furthermore", "however", "therefore", "moreover", "additionally",
        "according to", "research shows", "studies indicate", "reports suggest",
        "experts believe", "data reveals", "findings show", "evidence suggests",
        "technology", "innovation", "development", "advancement", "breakthrough",
        "industry", "market", "business", "economic", "financial", "growth"
    ]
    
    BLACKLISTED_TERMS = [
        "i am an ai", "as an ai", "i cannot", "i'm unable to",
        "sorry, i can't", "content filtered", "inappropriate request",
        "safety filter", "against my programming", "i apologize, but"
    ]
    
    @classmethod
    def validate_content(
        cls, 
        content: str, 
        title: str, 
        min_word_count: int = 500
    ) -> Dict:
        """
        Validate content against quality standards.
        
        Returns:
            Dictionary with validation results
        """
        issues = []
        scores = {}
        content_lower = content.lower()
        
        # Word count validation
        word_count = len(content.split())
        scores['length'] = cls._calculate_length_score(word_count, min_word_count)
        if word_count < min_word_count:
            issues.append(
                f"Content too short: {word_count} words (min: {min_word_count})"
            )
        
        # Safety validation
        scores['safety'] = cls._calculate_safety_score(content_lower)
        if scores['safety'] == 0.0:
            issues.append("Blacklisted terms detected")
        
        # Quality validation
        scores['quality'] = cls._calculate_quality_score(content_lower)
        
        # Structure validation
        scores['structure'] = cls._calculate_structure_score(
            content, 
            word_count, 
            min_word_count
        )
        
        # Overall score
        overall_score = sum(scores.values()) / len(scores)
        
        return {
            'valid': len(issues) == 0 and overall_score > 0.6,
            'score': overall_score,
            'issues': issues,
            'detailed_scores': scores,
            'word_count': word_count
        }

    @classmethod
    def _calculate_length_score(
        cls, 
        word_count: int, 
        min_count: int
    ) -> float:
        """Calculate score based on content length."""
        if word_count < min_count:
            return max(0, word_count / min_count)
        return min(1.0, word_count / (min_count * 1.5))

    @classmethod
    def _calculate_safety_score(cls, content: str) -> float:
        """Calculate safety score based on blacklisted terms."""
        return 0.0 if any(
            term in content for term in cls.BLACKLISTED_TERMS
        ) else 1.0

    @classmethod
    def _calculate_quality_score(cls, content: str) -> float:
        """Calculate quality score based on indicators."""
        indicator_count = sum(
            1 for indicator in cls.QUALITY_INDICATORS 
            if indicator in content
        )
        quality_ratio = indicator_count / len(cls.QUALITY_INDICATORS)
        return min(1.0, quality_ratio * 5)

    @classmethod
    def _calculate_structure_score(
        cls, 
        content: str, 
        word_count: int, 
        min_count: int
    ) -> float:
        """Calculate structure score based on formatting elements."""
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        has_headers = any(line.startswith('#') for line in content.split('\n'))
        
        structure_score = 0.0
        if len(paragraphs) >= 3:
            structure_score += 0.4
        if has_headers:
            structure_score += 0.3
        if word_count > min_count * 1.2:
            structure_score += 0.3
        return structure_score


class AIGenerator:
    """Generates content using various strategies with quality validation."""
    
    def __init__(self, ai_config):
        self.config = ai_config
        self.validator = ContentValidator()
        self.generation_history = []
        
    async def generate_content(
        self, 
        title: str, 
        sources: List[str], 
        urls: List[str] = None
    ) -> ContentResult:
        """
        Generate content using multiple strategies until success.
        
        Returns:
            ContentResult with generated content and metadata
        """
        strategies = [
            ("structured", self._generate_structured),
            ("detailed", self._generate_detailed),
            ("standard", self._generate_standard),
            ("minimal", self._generate_minimal)
        ]
        
        start_time = asyncio.get_event_loop().time()
        
        for strategy_name, strategy_func in strategies:
            try:
                logger.info(
                    f"Attempting {strategy_name} generation: {title}"
                )
                
                content = await strategy_func(title, sources, urls)
                
                # Skip empty or error responses
                if not content or content.startswith("Error:"):
                    continue
                
                # Validate content
                validation = self.validator.validate_content(
                    content, 
                    title, 
                    self.config.min_content_length
                )
                
                if self._is_validation_successful(validation):
                    return self._create_result(
                        strategy_name, 
                        content, 
                        validation, 
                        start_time
                    )
                else:
                    logger.warning(
                        f"{strategy_name} validation failed: "
                        f"{validation['issues']}"
                    )
                    
            except Exception as error:
                logger.error(f"{strategy_name} generation failed: {error}")
        
        # All strategies failed
        raise Exception("All content generation strategies failed")

    def _is_validation_successful(self, validation: Dict) -> bool:
        """Check if validation meets minimum requirements."""
        return (
            validation['valid'] and 
            validation['word_count'] >= self.config.min_content_length
        )

    def _create_result(
        self, 
        strategy: str, 
        content: str, 
        validation: Dict, 
        start_time: float
    ) -> ContentResult:
        """Create ContentResult object from generation results."""
        generation_time = asyncio.get_event_loop().time() - start_time
        result = ContentResult(
            content=content,
            word_count=validation['word_count'],
            quality_score=validation['score'],
            generation_time=generation_time,
            strategy_used=strategy,
            validation_passed=True
        )
        
        self.generation_history.append(result)
        logger.info(
            f"Generated content using {strategy}: "
            f"{result.word_count} words, quality: {result.quality_score:.2f}"
        )
        return result

    async def _generate_structured(
        self, 
        title: str, 
        sources: List[str], 
        urls: List[str] = None
    ) -> str:
        """Generate content using structured strategy."""
        prompt = f"""You are an expert academic writer creating an original blog post about "{title}". Thoroughly rephrase and expand the source material using original language while maintaining factual accuracy. Include proper source attribution for all borrowed concepts.

**CRITICAL REQUIREMENTS:**
- ✍️ **Original Rephrasing:** Rewrite ALL content in fresh language (0% direct quotes)
- 📏 **Length:** 1200-1500 words (strict minimum 1000)
- 📚 **Citations:** Attribute every borrowed concept (APA format)
- 🧠 **Depth:** Add 3+ original insights beyond source material
- 🖋️ **Tone:** Engaging academic style with journalistic flair
- 📖 **Formatting:** Full Markdown (## H2, ### H3, bullet lists, bold key terms)

**STRUCTURE:**
## Comprehensive Introduction: Understanding {title}  
[200+ words: Current significance + historical context + thesis statement + article roadmap]

### Core Principle 1: [Key Aspect Name]  
[150+ words: Detailed explanation + 1 analogy/metaphor + 1 statistical example]

### Core Principle 2: [Important Detail Name]  
[150+ words: Cause-effect analysis + contrasting viewpoints + case study]

### Practical Implementation: Real-World Applications  
[150+ words:  
• Industry-specific use cases  
• Step-by-step implementation framework  
• "Pro Tip:" actionable advice]

### Emerging Trends and Future Evolution  
[150+ words:  
- Current innovations (2023-2024)  
- Predicted developments (2025-2030)  
- "Original Insight:" unique projection]

## Conclusion: Key Takeaways and Forward Perspective  
[150+ words: Synthesized findings + "Consider This:" critical question + resources for further learning]

## References  
[APA-formatted citations:  
1. Author(s). (Year). *Title*. Publication. DOI/URL  
2. ...  
*Include ALL referenced concepts*]

**SOURCE MATERIAL:**  
{self._create_summary(sources[:3])}

**WRITING PROTOCOL:**  
1. ANALYZE SOURCES: Extract core concepts only  
2. REPHRASE: Use 3-layer rewriting:  
   a) Synonym substitution  
   b) Sentence restructuring  
   c) Perspective shift (e.g., academic → practitioner)  
3. EXPAND: Add missing dimensions:  
   - Current industry applications  
   - Cross-disciplinary connections  
   - Future research gaps  
4. CITE: Attribute EVERY borrowed concept in references  
5. ENHANCE: Include:  
   - 3+ original data visualizations described in text  
   - 2 "Expert Insight:" commentary boxes  
   - 1 debate point with counterarguments  

Begin writing:"""

        return await self._execute_ai_generation(prompt, timeout=900)
    
    async def _generate_detailed(
        self, 
        title: str, 
        sources: List[str], 
        urls: List[str] = None
    ) -> str:
        """Generate content using detailed strategy."""
        prompt = f"""Create an original, rephrased blog article about "{title}" using the provided source material. Rewrite all content in your own words while preserving key information. Include proper source citations.

**REQUIREMENTS:**
- 📝 800-1200 words (strict minimum)
- 🔍 Deep analysis with unique insights
- ✍️ 100% original phrasing (no direct quotes)
- 📊 Include 3+ specific examples/case studies
- 📚 Academic/professional tone
- 📖 Markdown formatting with H2/H3 headers
- 🖇️ Clear source citations in references

**STRUCTURE:**
## Comprehensive Overview  
[Contextual introduction with thesis statement explaining the topic's significance]

## Critical Analysis of Key Concepts  
[Break into 3-4 subheaded sections using H3:  
### Subtheme 1  
### Subtheme 2  
### Subtheme 3]

## Evidence and Case Studies  
[Concrete examples including:  
- At least 1 statistical data point  
- 1 real-world application  
- 1 historical precedent]

## Implications and Future Impact  
[Discussion of:  
- Short-term consequences  
- Long-term ramifications  
- Industry-specific effects]

## Conclusion  
[Synthesized takeaways + thought-provoking closing]

## References  
[Citations formatted as:  
1. Source Title | Author (Year) [URL if available]  
2. [Additional sources...]  
*Include ALL borrowed concepts*]

**SOURCE MATERIAL:**  
{self._create_summary(sources[:2])}

**PROCESS:**  
1. Thoroughly analyze source material  
2. Extract core ideas ONLY (no verbatim text)  
3. Develop original structure and phrasing  
4. Add new insights beyond source content  
5. Verify word count before finalizing  

Begin writing:"""

        return await self._execute_ai_generation(prompt, timeout=600)
    
    async def _generate_standard(
        self, 
        title: str, 
        sources: List[str], 
        urls: List[str] = None
    ) -> str:
        """Generate content using standard strategy."""
        prompt = f"""Create an original blog post about "{title}" by thoroughly rephrasing and synthesizing the provided source material. Ensure 100% original wording while maintaining factual accuracy and academic integrity through proper citations.

**REQUIREMENTS:**
- ✍️ **Original Rephrasing:** Rewrite all concepts in fresh language (no direct quotes)
- 📏 **Length:** Strict 600-800 words
- 📚 **Citations:** Attribute ALL borrowed ideas (see format below)
- 🧠 **Structure:** Clear logical flow with Markdown headers
- 💡 **Value-Add:** Incorporate 1-2 original insights beyond sources
- 🔗 **Engagement:** Include rhetorical questions + actionable takeaways

**STRUCTURE:**
## Introduction: {title}  
[Context hook + clear purpose statement + roadmap]

### Core Concept Explanation  
[H3 subheaders for key principles:  
• Principle 1 with simple analogy  
• Principle 2 with cause-effect relationship  
• Principle 3 with contrast to alternatives]

### Evidence and Applications  
[3 concrete examples:  
1. Case study with location/time specifics  
2. Statistical evidence with context  
3. Real-world implementation scenario]

### Practical Implications  
[Analysis of:  
- Current impacts (use industry examples)  
- Future considerations  
- Limitations/challenges]

## Conclusion  
[Synthesized key takeaways + forward-looking statement]

## References  
[Numbered citations in APA format:  
1. Author(s). (Year). *Title*. Source. URL  
2. ...]

**SOURCE MATERIAL:**  
{self._create_summary(sources[:2])}

**CRITICAL INSTRUCTIONS:**  
1. Scan source material for core ideas ONLY  
2. Rewrite each concept with synonym substitution + structural changes  
3. Add "Original Insight:" callout boxes for value additions  
4. Verify citations match ALL borrowed concepts  
5. Include 2 reader-engagement elements:  
   - "Consider this:" thought-provoking question  
   - "Try this:" practical action step  

Begin writing:"""

        return await self._execute_ai_generation(prompt, timeout=450)
    
    async def _generate_minimal(
        self, 
        title: str, 
        sources: List[str], 
        urls: List[str] = None
    ) -> str:
        """Generate content using minimal strategy."""
        prompt = f"""Create an original blog post about "{title}" by thoroughly rephrasing the source material. Ensure 100% unique wording while maintaining factual accuracy and including proper source attribution.

**REQUIREMENTS:**
- ✍️ **Original Rephrasing:** Rewrite all content in fresh language (no direct quotes)
- 📏 **Length:** Strict 400-600 words
- 📚 **Citations:** Attribute ALL borrowed concepts (see format below)
- 🧠 **Structure:** Clear 3-part flow with Markdown headers
- 🖋️ **Style:** Professional yet accessible tone
- 🔑 **Focus:** Prioritize key insights over minor details

**STRUCTURE:**
### Introduction: The Essentials of {title}  
[Engaging opening + purpose statement + core significance]

### Key Insights Explained  
[Concise analysis of 2-3 critical aspects:  
• Main concept 1 with practical example  
• Main concept 2 with cause-effect relationship  
• Key implication or current application]

### Conclusion and Practical Takeaways  
[Synthesis of core message + 1 actionable insight]

### References  
[Source attribution in simplified format:  
- Source Title | Author (Year)  
- [URL if available]  
*Include ALL referenced concepts*]

**SOURCE MATERIAL:**  
{self._prepare_minimal_source(sources)}

**CRITICAL INSTRUCTIONS:**  
1. Scan source for key information ONLY  
2. Rewrite each concept using:  
   - Synonym replacement  
   - Sentence restructuring  
   - Perspective shift (e.g., third-person to first-person)  
3. Add 1 original insight not in source material  
4. Verify citations match ALL borrowed content  
5. Include 1 engagement element: "Consider this:" question  

Begin writing:"""

        return await self._execute_ai_generation(prompt, timeout=300)
    
    def _create_summary(self, sources: List[str]) -> str:
        """Create combined source summary with truncation."""
        combined = "\n\n---SOURCE BREAK---\n\n".join(sources)
        max_chars = 8000
        if len(combined) > max_chars:
            return combined[:max_chars] + "\n[Content truncated...]"
        return combined

    def _prepare_minimal_source(self, sources: List[str]) -> str:
        """Prepare source material for minimal strategy."""
        if not sources:
            return ""
        source = sources[0]
        return source[:2000] + "..." if len(source) > 2000 else source

    async def _execute_ai_generation(
        self, 
        prompt: str, 
        timeout: int = 600
    ) -> str:
        """Execute AI generation using subprocess."""
        try:
            process = await asyncio.create_subprocess_exec(
                'ollama', 'run', self.config.model_name,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=prompt.encode()),
                timeout=timeout
            )
            
            if process.returncode != 0:
                raise Exception(f"Ollama failed: {stderr.decode().strip()}")
                
            result = stdout.decode().strip()
            if not result:
                raise Exception("Empty AI response")
                
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Generation timed out after {timeout}s")
            raise
        except Exception as error:
            logger.error(f"Generation failed: {error}")
            raise


# Global AI generator instance
ai_generator = AIGenerator(config.ai)


async def generate_blog_post(
    title: str, 
    sources: List[str], 
    urls: List[str] = None
) -> str:
    """Generate blog post content."""
    try:
        result = await ai_generator.generate_content(title, sources, urls)
        return result.content
    except Exception as error:
        logger.error(f"Blog post generation failed: {error}")
        return f"Error: Content generation failed - {str(error)}"