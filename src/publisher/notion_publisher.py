import os
import re
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

from notion_client import Client
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


def clean_text_for_multiselect(text: str) -> str:
    """Clean text to be suitable for Notion multi-select options"""
    text = text.replace(',', '')
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'[^\w\s\-_.]', '', text)
    return text


def format_tags_for_notion(tags: List[str]) -> List[Dict[str, str]]:
    """Format tags for Notion multi-select with validation"""
    if not tags:
        return []

    formatted_tags = []
    seen_tags = set()
    
    for tag in tags:
        if not tag or not isinstance(tag, str):
            continue
        
        clean_tag = clean_text_for_multiselect(tag)
        clean_tag = clean_tag[:100] if len(clean_tag) > 100 else clean_tag
        
        if len(clean_tag) < 2:
            continue
            
        tag_lower = clean_tag.lower()
        if tag_lower not in seen_tags:
            seen_tags.add(tag_lower)
            formatted_tags.append({"name": clean_tag})
        
        if len(formatted_tags) >= 10:
            break
    
    logger.info(f"Formatted {len(tags)} tags to {len(formatted_tags)} valid tags")
    return formatted_tags


def validate_url(url: str) -> bool:
    """Validate URL format for Notion URL field"""
    if not url or not isinstance(url, str):
        return False
    
    pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(pattern.match(url))


def get_database_schema(database_id: str) -> Dict:
    """Fetch database schema to validate property types"""
    notion = Client(auth=os.getenv("NOTION_TOKEN"))
    database = notion.databases.retrieve(database_id=database_id)
    return database['properties']


def find_title_property(schema: Dict) -> tuple:
    """Find the title property in database schema"""
    for prop_name, prop_data in schema.items():
        if prop_data.get('type') == 'title':
            return prop_name, 'title'
    
    for prop_name, prop_data in schema.items():
        if prop_data.get('type') == 'rich_text':
            logger.warning(f"Using rich_text property '{prop_name}' as title")
            return prop_name, 'rich_text'
    
    return 'Title', 'title'


def split_content_into_blocks(content: str, max_chars: int = 2000) -> List[Dict]:
    """Split long content into multiple paragraph blocks"""
    if len(content) <= max_chars:
        return [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": content}}]
            }
        }]
    
    blocks = []
    remaining = content
    
    while remaining:
        if len(remaining) <= max_chars:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": remaining}}]
                }
            })
            break
        
        chunk = remaining[:max_chars]
        
        paragraph_split = chunk.rfind('\n\n')
        if paragraph_split > max_chars * 0.5:
            split_point = paragraph_split + 2
        else:
            sentence_split = max(
                chunk.rfind('. '),
                chunk.rfind('! '),
                chunk.rfind('? ')
            )
            if sentence_split > max_chars * 0.5:
                split_point = sentence_split + 2
            else:
                word_split = chunk.rfind(' ')
                split_point = word_split + 1 if word_split > max_chars * 0.5 else max_chars
        
        chunk_content = remaining[:split_point].strip()
        if chunk_content:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": chunk_content}}]
                }
            })
        
        remaining = remaining[split_point:].strip()
    
    return blocks


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def publish_to_notion(content: str, title: str, post_data: Dict) -> Dict:
    """Publish content to Notion database"""
    try:
        notion = Client(auth=os.getenv("NOTION_TOKEN"))
        parent_id = os.getenv("NOTION_DATABASE_ID")

        schema = get_database_schema(parent_id)
        title_prop, title_type = find_title_property(schema)
        logger.info(f"Using '{title_prop}' ({title_type}) for title")

        raw_tags = post_data.get("tags", [])
        formatted_tags = format_tags_for_notion(raw_tags)
        logger.info(f"Formatted {len(raw_tags)} tags to {len(formatted_tags)}")

        properties = {}
        
        # Title property handling
        if title_type == 'title':
            properties[title_prop] = {
                "title": [{
                    "type": "text",
                    "text": {"content": title}
                }]
            }
        else:
            properties[title_prop] = {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": title}
                }]
            }

        # Optional properties
        optional_props = {
            "Status": ("status", "select", "Draft"),
            "Quality Score": ("quality_score", "number", 0),
            "Word Count": ("word_count", "number", 0),
            "SEO Score": ("seo_score", "number", 0),
            "Engagement Score": ("engagement_score", "number", 0),
            "Content Hash": ("content_hash", "rich_text", ""),
        }
        
        for prop, (key, prop_type, default) in optional_props.items():
            if prop in schema:
                value = post_data.get(key, default)
                if value:
                    if prop_type == "select":
                        properties[prop] = {prop_type: {"name": value}}
                    elif prop_type == "rich_text":
                        properties[prop] = {
                            "rich_text": [
                                {
                                    "type": "text", 
                                    "text": {"content": str(value)}
                                }
                            ]
                        }
                    else:
                        properties[prop] = {prop_type: value}

        # URL property
        if "URL" in schema and (url := post_data.get("url")):
            if validate_url(url):
                properties["URL"] = {"url": url}
                logger.info(f"Added URL: {url}")
            else:
                logger.warning(f"Invalid URL skipped: {url}")

        # Tags property
        if "Tags" in schema and formatted_tags:
            properties["Tags"] = {"multi_select": formatted_tags}
            logger.info(f"Added tags: {[t['name'] for t in formatted_tags]}")

        # Published At property
        if "Published At" in schema and (pub_date := post_data.get("published_at")):
            if isinstance(pub_date, str):
                properties["Published At"] = {"date": {"start": pub_date}}
                logger.info(f"Added Published At: {pub_date}")

        content_blocks = split_content_into_blocks(content)
        logger.info(f"Created {len(content_blocks)} content blocks")

        response = notion.pages.create(
            parent={"type": "database_id", "database_id": parent_id},
            properties=properties,
            children=content_blocks
        )

        page_id = response["id"]
        page_url = response["url"]
        logger.info(f"Published successfully! Page: {page_url}")
        
        return {
            "success": True,
            "page_id": page_id,
            "page_url": page_url,
            "properties_set": list(properties.keys())
        }

    except Exception as e:
        logger.error(f"Publishing failed: {str(e)}")
        logger.error("Properties attempted:")
        for key, value in properties.items():
            logger.error(f"  {key}: {value}")
        raise


def test_notion_connection() -> bool:
    """Test Notion connection and database schema"""
    try:
        notion = Client(auth=os.getenv("NOTION_TOKEN"))
        database_id = os.getenv("NOTION_DATABASE_ID")
        
        logger.info("Testing Notion connection...")
        schema = get_database_schema(database_id)
        
        logger.info("Database properties:")
        for prop, data in schema.items():
            logger.info(f"  {prop}: {data.get('type', 'unknown')}")
        
        required_props = ["URL", "Tags", "Content Hash"]
        for prop in required_props:
            status = "✅" if prop in schema else "✗"
            logger.info(f"{status} {prop}")
        
        return True
        
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False


def publish_test_post() -> bool:
    """Publish test post to verify publishing functionality"""
    test_content = """
# Test Blog Post - Notion Publishing

This is a test blog post to verify Notion publishing functionality.

## Features Verified
- Page creation with proper API calls
- URL field population
- Tags multi-select
- Content Hash generation
- Content blocks creation
- All properties correctly set
"""

    test_data = {
        "status": "Published",
        "quality_score": 95.0,
        "word_count": 200,
        "published_at": datetime.now().isoformat(),
        "seo_score": 85.0,
        "engagement_score": 90.0,
        "tags": ["Test", "Notion", "Blog", "Publishing"],
        "url": "https://yourblog.com/posts/test-notion-publishing",
        "content_hash": "test123456789abcdef",
    }

    try:
        result = publish_to_notion(
            test_content,
            "Test: Notion Publishing Verification",
            test_data
        )
        logger.info(f"Test post published: {result['page_url']}")
        return True
    except Exception as e:
        logger.error(f"Test post failed: {e}")
        return False