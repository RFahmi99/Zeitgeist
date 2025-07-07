import os
import re
import json
import logging
import hashlib
import markdown
from datetime import datetime
from typing import List, Dict
from urllib.parse import urlparse
from jinja2 import Template

from src.database.models import db_manager, BlogPost
from src.publisher.notion_publisher import publish_to_notion
from src.generator.quality_scorer import quality_scorer

logger = logging.getLogger(__name__)


def generate_blog_post_url(title: str) -> str:
    """Generate proper blog post URL"""
    # Create slug from title
    slug = title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug).strip('-')
    
    # Limit slug length
    if len(slug) > 60:
        slug = slug[:60].rsplit('-', 1)[0]
    
    # Generate unique post ID
    unique_string = f"{title}{datetime.now().isoformat()}"
    post_id = hashlib.md5(unique_string.encode()).hexdigest()[:8]
    
    # Generate final URL
    blog_domain = os.getenv('BLOG_DOMAIN', 'https://yourblog.com')
    return f"{blog_domain}/posts/{post_id}/{slug}"


def extract_tags_from_content(
    title: str, 
    content: str, 
    source_metadata: List[Dict]
) -> List[str]:
    """Extract intelligent tags from content"""
    tags = set()
    content_lower = content.lower()

    # Category term lists
    tech_terms = ['artificial intelligence', 'ai', 'machine learning', 'ml']
    business_terms = ['startup', 'innovation', 'investment', 'growth']
    science_terms = ['research', 'discovery', 'technology', 'medical']
    all_terms = tech_terms + business_terms + science_terms

    # Extract from title
    for word in re.findall(r'\b[A-Z][a-zA-Z]+\b', title):
        if len(word) > 3:
            tags.add(word.lower())

    # Extract from content
    for term in all_terms:
        if term in content_lower:
            tags.add(term.replace(' ', '_'))

    # Extract from source metadata
    for source_meta in source_metadata:
        if isinstance(source_meta, dict):
            if domain := source_meta.get('domain'):
                clean_domain = domain.replace('.', '_').replace('-', '_')
                tags.add(f"{clean_domain}_source")

    # Auto-categorize
    categories = []
    if any(term in content_lower for term in tech_terms):
        categories.append('technology')
    if any(term in content_lower for term in business_terms):
        categories.append('business')
    if any(term in content_lower for term in science_terms):
        categories.append('science')
    
    tags.update(categories)

    # Clean and format tags
    final_tags = []
    for tag in tags:
        clean_tag = re.sub(r'[^\w\s-]', '', tag).strip()
        if len(clean_tag) >= 3:
            formatted_tag = clean_tag.replace('_', ' ').title()
            final_tags.append(formatted_tag)

    # Return unique tags
    return list(set(final_tags))[:8]


def generate_html_from_markdown(markdown_text: str, title: str) -> str:
    """Convert markdown to HTML with template"""
    html_content = markdown.markdown(markdown_text)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_path = os.path.join(base_dir, "templates", "template.html")

    try:
        with open(template_path) as f:
            return Template(f.read()).render(title=title, content=html_content)
    except FileNotFoundError:
        # Fallback template
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="content">{html_content}</div>
    </div>
</body>
</html>"""


def save_blog_to_html(content: str, title: str) -> None:
    """Save blog post as HTML file"""
    try:
        os.makedirs('blog_posts', exist_ok=True)
        
        # Generate filename
        safe_title = re.sub(r'[^\w\s-]', '', title.strip())
        safe_title = re.sub(r'\s+', '_', safe_title)[:50]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"blog_posts/{timestamp}_{safe_title}.html"
        
        # Generate and save HTML
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(generate_html_from_markdown(content, title))
        
        logger.info(f"Saved HTML: {filename}")
    except Exception as e:
        logger.error(f"HTML save failed: {e}")


def save_blog_to_database_and_files(
    blog_content: str,
    title: str,
    sources_metadata: List[Dict],
    urls: List[str]
) -> int:
    """Save blog post to database and publish to files/Notion"""
    try:
        content_hash = hashlib.sha256(blog_content.encode()).hexdigest()
        tags = extract_tags_from_content(title, blog_content, sources_metadata)
        post_url = generate_blog_post_url(title)
        quality_score = quality_scorer.score_content(blog_content, title)

        # Create blog post object
        post = BlogPost(
            title=title,
            content=blog_content,
            sources="",  # Empty sources field
            urls=json.dumps(urls),
            url=post_url,
            quality_score=quality_score.overall_score,
            word_count=len(blog_content.split()),
            status='published',
            tags=json.dumps(tags),
            seo_score=quality_score.seo_score,
            engagement_score=quality_score.engagement_score,
            published_at=datetime.now(),
            content_hash=content_hash
        )

        # Save to database
        post_id = db_manager.save_blog_post(post)
        logger.info(f"Saved to database ID: {post_id}")

        # Prepare post data for Notion
        post_data = {
            "status": "Published",
            "quality_score": quality_score.overall_score,
            "word_count": len(blog_content.split()),
            "published_at": datetime.now().isoformat(),
            "seo_score": quality_score.seo_score,
            "engagement_score": quality_score.engagement_score,
            "tags": tags,
            "url": post_url,
            "content_hash": content_hash,
        }

        # Save to HTML and publish to Notion
        save_blog_to_html(blog_content, title)
        publish_to_notion(blog_content, title, post_data)
        
        logger.info(f"Published successfully: {post_url}")
        return post_id

    except Exception as e:
        logger.error(f"Blog save failed: {e}")
        raise