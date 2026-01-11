#!/usr/bin/env python3
"""
Blogger Post Automation Script
Automates cryptocurrency blog posts using Google Gemini AI and Unsplash API
Publishes directly to Blogger via Blogger API v3
"""

import os
import json
import requests
import time
from datetime import datetime
from google import genai
from google.genai import types
from io import BytesIO
from PIL import Image
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as AuthRequest

# ==================== CONFIGURATION ====================

# API Keys (Set these as environment variables)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
UNSPLASH_ACCESS_KEY = os.environ.get('UNSPLASH_ACCESS_KEY', '')

# Blogger OAuth Configuration
BLOGGER_CLIENT_ID = os.environ.get('BLOGGER_CLIENT_ID', '')
BLOGGER_CLIENT_SECRET = os.environ.get('BLOGGER_CLIENT_SECRET', '')
BLOGGER_REFRESH_TOKEN = os.environ.get('BLOGGER_REFRESH_TOKEN', '')

# Blogger Configuration
BLOG_ID = os.environ.get('BLOG_ID', '')  # Extract from your Blogger dashboard
BLOGGER_API_URL = f'https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts'

# File Paths
TOPICS_FILE = 'topics.txt'
STATUS_FILE = 'status.json'
IMAGE_DIR = 'images'

# Categories for Blogger labels
CATEGORIES = [
    'Beginner Guide',
    'Crypto Investment',
    'News and Updates',
    'Tools & Tutorials',
    'Crypto Airdrops',
    'Blockchain Technology',
    'DeFi',
    'NFTs'
]

# ==================== HELPER FUNCTIONS ====================

def initialize_apis():
    """Initialize Gemini AI client"""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    return client


def load_status():
    """Load current status from status.json"""
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"next_day": 1, "last_processed": ""}


def save_status(status):
    """Save status to status.json"""
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(status, f, indent=2, ensure_ascii=False)


def load_topics():
    """Load topics from topics.txt"""
    if not os.path.exists(TOPICS_FILE):
        raise FileNotFoundError(f"{TOPICS_FILE} not found")
    
    with open(TOPICS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    topics = []
    blocks = content.strip().split('\n\n')
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 2:
            day_line = lines[0].strip()
            topic_line = lines[1].strip()
            
            if day_line.startswith('Day'):
                try:
                    day = int(day_line.split()[1])
                except (IndexError, ValueError):
                    print(f"Warning: Skipping invalid day line: {day_line}")
                    continue
                
                topic = topic_line.replace('Topic: ', '').strip()
                if not topic:
                    print(f"Warning: Empty topic for Day {day}")
                    continue
                
                details = ""
                if len(lines) > 2:
                    for line in lines[2:]:
                        if line.strip().startswith('Additional Details:'):
                            details = line.replace('Additional Details: ', '').strip()
                            break
                
                topics.append({
                    'day': day,
                    'topic': topic,
                    'details': details
                })
    
    if not topics:
        raise ValueError("No valid topics found in topics.txt")
    
    return topics


def get_next_topic():
    """Get the next topic to process"""
    status = load_status()
    topics = load_topics()
    
    next_day = status.get('next_day', 1)
    
    # Find the topic for the next day
    for topic in topics:
        if topic['day'] == next_day:
            return topic
    
    # If we've reached the end, start over from Day 1
    max_day = max(t['day'] for t in topics)
    if next_day > max_day:
        print(f"Reached end of topics (Day {max_day}). Restarting from Day 1.")
        status['next_day'] = 1
        save_status(status)
        return topics[0] if topics else None
    
    return None


# ==================== CONTENT GENERATION ====================

def generate_blog_content(client, topic, details, category):
    """Generate blog post content using Gemini AI"""
    print(f"Generating content for: {topic}")
    
    prompt = f"""You are an expert cryptocurrency and blockchain content writer for the blog "Crypto Basic Guide" (cryptobasicguide.blogspot.com).

Write a comprehensive, detailed, narrative-driven blog post about: {topic}

Additional Context: {details if details else 'Provide comprehensive coverage of the topic'}

Requirements:
1. Write a DETAILED, informative article (1500-2000 words) - make it comprehensive and valuable
2. Use a NARRATIVE, STORYTELLING approach - tell a story, don't just list facts
3. Write like you're having a conversation with a friend - engaging, personal, relatable
4. Use clear headings and subheadings (## for main sections, ### for subsections)
5. Include real-world scenarios, case studies, and relatable examples
6. Start with a compelling hook or story that draws readers in
7. Use analogies and metaphors to explain complex concepts
8. Add personal insights, opinions, and expert perspectives
9. Include step-by-step walkthroughs where appropriate
10. Discuss both benefits and risks honestly
11. Share practical tips from real-world experience
12. Include current trends, market movements, and future predictions
13. Explain technical terms naturally within the narrative
14. Add context about why this matters to readers personally
15. DO NOT USE EMOJIS - write professionally without emoji characters
16. Focus on cryptocurrency and blockchain technology
17. Category: {category}

Structure (aim for 1500-2000 words total):
- Opening Story/Hook (grab attention with a real scenario or surprising fact)
- Introduction (2-3 paragraphs setting the scene and explaining importance)
- Main narrative with 4-6 detailed sections:
  * Each section should flow naturally from the previous one
  * Use transitions and connecting phrases
  * Include examples, scenarios, and real-world applications
  * Mix explanation with storytelling
- Practical guidance section (actionable tips readers can use immediately)
- Common mistakes and how to avoid them (from real experiences)
- Future outlook and trends (where things are heading)
- Conclusion with key takeaways and next steps

Tone:
- Conversational and friendly, but professional
- Educational without being preachy
- Honest about both opportunities and risks
- Confident but not overconfident
- Avoid hype and unrealistic promises

DO NOT INCLUDE:
- Emojis or emoji characters of any kind
- Generic advice - be specific and detailed
- Overly technical jargon without explanation
- Financial advice disclaimers (readers understand this is educational)

Format the content in Markdown with proper headings.

IMPORTANT: Generate the COMPLETE article from start to finish. Do not stop mid-way. Write all sections including the conclusion. The article must be complete and end with a proper conclusion.

Generate the comprehensive, narrative-driven content (1500-2000 words):"""

    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.8,
                    max_output_tokens=8192,  # Increased from 4096 to support longer content
                )
            )
            
            content = response.text.strip()
            
            # Clean up any markdown code blocks
            if content.startswith('```markdown'):
                content = content.replace('```markdown', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()
            
            if not content or len(content) < 100:
                raise ValueError("Generated content too short")
            
            # Check if content appears truncated (incomplete)
            is_truncated = (
                not content.rstrip().endswith(('.', '!', '?', '"', "'"))  # Doesn't end with punctuation
                or len(content) < 1000  # Too short for requested 1500-2000 words
                or content.count('##') < 3  # Missing expected sections
            )
            
            if is_truncated:
                print(f"⚠️ Content appears incomplete ({len(content)} chars), attempting continuation...")
                
                # Try to continue from where it left off
                continuation_prompt = f"""Continue writing the blog post from where you left off. Here's what was written so far:

{content}

---

Continue writing naturally from the point where it was cut off. Complete all remaining sections including:
- Any incomplete sections
- Practical guidance section
- Common mistakes and how to avoid them
- Future outlook and trends
- Conclusion with key takeaways and next steps

Make sure to write a proper conclusion. Format in Markdown. Continue:"""
                
                continuation_response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=continuation_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.8,
                        max_output_tokens=4096,
                    )
                )
                
                continuation = continuation_response.text.strip()
                if continuation.startswith('```markdown'):
                    continuation = continuation.replace('```markdown', '').replace('```', '').strip()
                elif continuation.startswith('```'):
                    continuation = continuation.replace('```', '').strip()
                
                # Combine original and continuation
                content = content + "\n\n" + continuation
                print(f"✅ Content completed ({len(content)} chars total)")
            
            return content
            
        except Exception as e:
            print(f"Error generating content (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Failed to generate content after all retries")
                return None


def convert_markdown_to_html(markdown_content):
    """Convert Markdown to beautifully styled HTML for Blogger"""
    import re
    
    html = markdown_content
    
    # Convert headers with attractive styling
    html = re.sub(r'^### (.+)$', r'<h3 style="color: #2c3e50; font-size: 22px; font-weight: 600; margin: 28px 0 15px 0; line-height: 1.4; border-left: 4px solid #3498db; padding-left: 15px;">\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2 style="color: #1a1a1a; font-size: 28px; font-weight: 700; margin: 35px 0 20px 0; padding-bottom: 12px; border-bottom: 3px solid #4CAF50; line-height: 1.3;">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1 style="color: #1a1a1a; font-size: 32px; font-weight: 800; margin: 40px 0 25px 0;">\1</h1>', html, flags=re.MULTILINE)
    
    # Convert bold with accent color
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color: #2196F3; font-weight: 600;">\1</strong>', html)
    html = re.sub(r'__(.+?)__', r'<strong style="color: #2196F3; font-weight: 600;">\1</strong>', html)
    
    # Convert italic
    html = re.sub(r'\*([^\*]+?)\*', r'<em style="color: #555;">\1</em>', html)
    html = re.sub(r'_([^_]+?)_', r'<em style="color: #555;">\1</em>', html)
    
    # Convert links with styling
    html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" style="color: #3498db; text-decoration: none; border-bottom: 2px solid #3498db;">\1</a>', html)
    
    # Convert bullet lists with better styling
    lines = html.split('\n')
    in_list = False
    result = []
    
    for line in lines:
        if line.strip().startswith('- ') or line.strip().startswith('* '):
            if not in_list:
                result.append('<ul style="margin: 20px 0; padding-left: 35px; line-height: 1.9;">')
                in_list = True
            item = line.strip()[2:]
            result.append(f'<li style="margin: 10px 0; color: #444; font-size: 17px; list-style-type: disc;">{item}</li>')
        else:
            if in_list:
                result.append('</ul>')
                in_list = False
            result.append(line)
    
    if in_list:
        result.append('</ul>')
    
    html = '\n'.join(result)
    
    # Convert paragraphs with better spacing and typography
    paragraphs = html.split('\n\n')
    html_paragraphs = []
    
    for para in paragraphs:
        para = para.strip()
        if para and not para.startswith('<'):
            html_paragraphs.append(f'<p style="line-height: 1.9; margin: 18px 0; color: #333; font-size: 17px; text-align: justify;">{para}</p>')
        elif para:
            html_paragraphs.append(para)
    
    html_content = '\n\n'.join(html_paragraphs)
    
    # Wrap in a container div for consistent styling
    return f'<div style="font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; max-width: 100%; padding: 0;">{html_content}</div>'


# ==================== IMAGE HANDLING ====================

def generate_image_search_query(client, topic):
    """Generate specific 2-3 word Unsplash search query using Gemini AI"""
    prompt = f"""Generate a SPECIFIC search query for Unsplash (2-3 words) to find a professional cryptocurrency image.

TOPIC: {topic}

Requirements:
- Generate 2-3 SPECIFIC words (not just 1 generic word like "security" or "technology")
- Focus on visual elements: coins, technology, charts, digital assets, blockchain visuals
- Make the query unique enough to get different image results
- Avoid overly generic single-word queries

Examples of GOOD queries (2-3 specific words):
- "bitcoin gold coin" (NOT just "bitcoin")
- "ethereum blockchain network" (NOT just "ethereum")
- "cryptocurrency trading chart" (NOT just "trading")
- "digital wallet security" (NOT just "security")
- "blockchain data network" (NOT just "blockchain")

Examples of BAD queries (too generic):
- "security" ❌
- "technology" ❌
- "crypto" ❌
- "blockchain" ❌

Return ONLY the search query (2-3 words), nothing else."""

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=20,
            )
        )
        
        query = response.text.strip().strip('"').strip("'").strip().lower()
        # Ensure query is 2-3 words (optimal for specific searches)
        words = query.split()
        if len(words) > 3:
            query = ' '.join(words[:3])
        elif len(words) < 2:
            query = f"{query} cryptocurrency"
        
        print(f"🔍 Generated specific image query: '{query}' (2-3 words)")
        return query
        
    except Exception as e:
        print(f"Error generating image query: {e}")
        # Fallback to topic-based keywords
        topic_lower = topic.lower()
        if 'bitcoin' in topic_lower:
            return "bitcoin cryptocurrency"
        elif 'ethereum' in topic_lower:
            return "ethereum blockchain"
        else:
            return "cryptocurrency blockchain"


def get_unsplash_image(topic, used_images=None):
    """Download image from Unsplash with deduplication and random selection
    
    Args:
        topic: The blog topic for image search
        used_images: List of previously used image URLs to avoid duplicates
    
    Returns:
        Dict with image data and URL for tracking, or None
    """
    if not UNSPLASH_ACCESS_KEY:
        print("Warning: UNSPLASH_ACCESS_KEY not set, skipping image")
        return None
    
    if used_images is None:
        used_images = []
    
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            # Initialize Gemini client for query generation
            client = initialize_apis()
            search_query = generate_image_search_query(client, topic)
            
            url = "https://api.unsplash.com/search/photos"
            headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
            params = {
                "query": search_query,
                "orientation": "landscape",
                "per_page": 10  # Get 10 results to randomly choose from
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('results') and len(data['results']) > 0:
                print(f"🔍 Total results from search: {len(data['results'])}")
                
                # Filter out already used images
                available_photos = [
                    photo for photo in data['results']
                    if photo['urls']['regular'] not in used_images
                ]
                
                print(f"🔍 Already used: {len(data['results']) - len(available_photos)}")
                print(f"🔍 Available photos: {len(available_photos)}")
                
                if available_photos:
                    # Randomly select from available options
                    import random
                    photo = random.choice(available_photos)
                    
                    image_url = photo['urls']['regular']  # This will be tracked
                    photographer = photo['user']['name']
                    photographer_url = photo['user']['links']['html']
                    
                    print(f"✅ Selected image by {photographer} (from {len(available_photos)} available)")
                    
                    # Download image
                    img_response = requests.get(image_url, timeout=15)
                    img_response.raise_for_status()
                    
                    return {
                        'data': img_response.content,
                        'photographer': photographer,
                        'photographer_url': photographer_url,
                        'unsplash_url': photo['links']['html'],
                        'image_url': image_url  # Add URL for tracking
                    }
                else:
                    print(f"⚠️ All {len(data['results'])} images from '{search_query}' have been used before")
                    if attempt < max_retries - 1:
                        # Fallback: try broader search with first word only
                        fallback_query = search_query.split()[0] + " cryptocurrency"
                        print(f"🔄 Trying fallback search: '{fallback_query}'")
                        params["query"] = fallback_query
                        
                        response = requests.get(url, headers=headers, params=params, timeout=15)
                        response.raise_for_status()
                        data = response.json()
                        continue
                    return None
            else:
                print(f"No images found for query: {search_query}")
                if attempt < max_retries - 1:
                    # Try with fallback query
                    search_query = "cryptocurrency blockchain"
                    continue
                return None
                
        except Exception as e:
            print(f"Error fetching Unsplash image (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                return None


def compress_image(image_data, max_size_kb=480):
    """Compress image to under 500KB with high quality"""
    img = Image.open(BytesIO(image_data))
    
    # Convert to RGB if necessary
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background
    
    # Resize if too large
    max_dimension = 1200
    if img.width > max_dimension or img.height > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    
    # Compress
    output = BytesIO()
    quality = 85
    
    while quality > 20:
        output.seek(0)
        output.truncate()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        size_kb = len(output.getvalue()) / 1024
        
        if size_kb <= max_size_kb:
            break
        
        quality -= 5
    
    print(f"Image compressed to {size_kb:.1f}KB (quality: {quality})")
    return output.getvalue()


def save_image_locally(image_data, day):
    """Save image to local directory"""
    os.makedirs(IMAGE_DIR, exist_ok=True)
    
    filename = f"day-{day}.jpg"
    filepath = os.path.join(IMAGE_DIR, filename)
    
    with open(filepath, 'wb') as f:
        f.write(image_data)
    
    print(f"Image saved: {filepath}")
    return filepath


# ==================== BLOGGER API ====================

def get_oauth_access_token():
    """Get OAuth access token from refresh token"""
    credentials = Credentials(
        None,
        refresh_token=BLOGGER_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=BLOGGER_CLIENT_ID,
        client_secret=BLOGGER_CLIENT_SECRET
    )
    
    # Refresh the token
    credentials.refresh(AuthRequest())
    return credentials.token


def publish_to_blogger(title, content_html, labels, image_url=None):
    """Publish post to Blogger via API v3 with OAuth"""
    if not BLOGGER_CLIENT_ID or not BLOGGER_CLIENT_SECRET or not BLOGGER_REFRESH_TOKEN or not BLOG_ID:
        print("Error: Blogger OAuth credentials or BLOG_ID not set")
        return False
    
    # Prepare post data
    post_data = {
        "kind": "blogger#post",
        "title": title,
        "content": content_html,
        "labels": labels
    }
    
    # Add featured image if available
    if image_url:
        # Extract attribution if embedded in URL
        actual_url = image_url
        attribution_html = ""
        if "#" in image_url:
            actual_url, attribution_html = image_url.split("#", 1)
        
        # Simple, clean image presentation with attribution right below
        image_html = f'''<div class="featured-image" style="text-align: center; margin: 30px 0 20px 0;">
    <img src="{actual_url}" alt="{title}" style="max-width: 100%; height: auto; display: block; margin: 0 auto;" />
</div>
{attribution_html}'''
        post_data["content"] = image_html + "\n\n" + content_html
    
    max_retries = 3
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            # Get fresh access token
            access_token = get_oauth_access_token()
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            print(f"Publishing to Blogger: {title} (attempt {attempt + 1}/{max_retries})")
            response = requests.post(
                BLOGGER_API_URL,
                json=post_data,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            post_url = result.get('url', '')
            post_id = result.get('id', '')
            print(f"✓ Post published successfully!")
            print(f"  URL: {post_url}")
            print(f"  Post ID: {post_id}")
            
            return True
            
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            print(f"Status Code: {e.response.status_code}")
            print(f"Response: {e.response.text}")
            
            # Don't retry on client errors (4xx)
            if 400 <= e.response.status_code < 500:
                print("Client error - not retrying")
                return False
            
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                return False
                
        except Exception as e:
            print(f"Error publishing to Blogger: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                return False
    
    return False


# ==================== MAIN WORKFLOW ====================

def main():
    """Main automation workflow"""
    print("=" * 60)
    print("Crypto Basic Guide - Blog Automation")
    print("=" * 60)
    print()
    
    # Check environment variables
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY environment variable not set")
        print("Get your API key from: https://aistudio.google.com/app/apikey")
        return False
    
    if not BLOGGER_CLIENT_ID or not BLOGGER_CLIENT_SECRET or not BLOGGER_REFRESH_TOKEN:
        print("Error: Blogger OAuth credentials not set")
        print("Required: BLOGGER_CLIENT_ID, BLOGGER_CLIENT_SECRET, BLOGGER_REFRESH_TOKEN")
        print("Run get_oauth_token.py to generate these credentials")
        return False
    
    if not BLOG_ID:
        print("Error: BLOG_ID environment variable not set")
        print("Get your Blog ID from Blogger dashboard URL")
        return False
    
    # Initialize
    print("Initializing Gemini AI...")
    client = initialize_apis()
    
    # Get next topic
    print("Loading next topic...")
    topic_data = get_next_topic()
    
    if not topic_data:
        print("No more topics to process!")
        return False
    
    day = topic_data['day']
    topic = topic_data['topic']
    details = topic_data['details']
    
    # Select category
    category = CATEGORIES[day % len(CATEGORIES)]
    
    print(f"\nProcessing Day {day}")
    print(f"Topic: {topic}")
    print(f"Category: {category}")
    print()
    
    # Generate content
    print("Step 1: Generating blog content...")
    content = generate_blog_content(client, topic, details, category)
    
    if not content:
        print("Failed to generate content")
        return False
    
    print(f"✓ Content generated ({len(content)} characters)")
    print()
    
    # Convert to HTML
    print("Step 2: Converting Markdown to HTML...")
    content_html = convert_markdown_to_html(content)
    print("✓ Content converted to HTML")
    print()
    
    # Get image with deduplication
    print("Step 3: Fetching image from Unsplash with deduplication...")
    
    # Load used images from status
    used_images = []
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                status = json.load(f)
                used_images = status.get('used_images', [])
                print(f"📋 Loaded {len(used_images)} previously used images")
        except Exception as e:
            print(f"⚠️ Could not load used images: {e}")
    
    # Pass used_images to avoid duplicates
    image_data_dict = get_unsplash_image(topic, used_images)
    
    image_url = None
    new_image_url = None  # For tracking
    if image_data_dict:
        try:
            # Compress image to under 500KB
            compressed_data = compress_image(image_data_dict['data'])
            
            # Save locally (will be committed to GitHub)
            image_path = save_image_locally(compressed_data, day)
            
            # Extract the image URL for tracking
            new_image_url = image_data_dict.get('image_url')
            
            # Use GitHub raw URL for the image (publicly accessible)
            # Include attribution that will be placed right after the image
            attribution = f'<p style="text-align: center; font-size: 13px; color: #888; margin: 10px 0 30px 0;"><em>Photo by <a href="{image_data_dict["photographer_url"]}" target="_blank" style="color: #888; text-decoration: underline;">{image_data_dict["photographer"]}</a> on <a href="{image_data_dict["unsplash_url"]}" target="_blank" style="color: #888; text-decoration: underline;">Unsplash</a></em></p>'
            image_url = f"https://raw.githubusercontent.com/sourcecodeRTX/Autojeta/main/images/day-{day}.jpg#{attribution}"
            
            print("✓ Image processed and saved")
            print(f"  GitHub URL: {image_url}")
            if new_image_url:
                print(f"  Tracking URL: {new_image_url[:60]}...")
        except Exception as e:
            print(f"Warning: Image processing failed: {e}")
    else:
        print("⚠ No image available, proceeding without image")
    print()
    
    # Publish to Blogger
    print("Step 4: Publishing to Blogger...")
    title = topic  # Use only the topic as title, without day prefix
    labels = [category, "Cryptocurrency", "Blockchain"]
    
    success = publish_to_blogger(title, content_html, labels, image_url)
    
    if not success:
        print("Failed to publish to Blogger")
        return False
    
    print()
    
    # Update status with used images tracking
    print("Step 5: Updating status with image tracking...")
    status = load_status()
    
    # Get existing used_images or initialize empty list
    used_images = status.get('used_images', [])
    
    # Add new image URL if available
    if new_image_url and new_image_url not in used_images:
        used_images.append(new_image_url)
        print(f"📝 Added new image to tracking (total tracked: {len(used_images)})")
    
    # Update status
    status['next_day'] = day + 1
    status['last_processed'] = topic
    status['last_published'] = datetime.now().isoformat()
    status['used_images'] = used_images  # Save tracked images
    save_status(status)
    print("✓ Status updated with image tracking")
    print()
    
    print("=" * 60)
    print("✓ Automation completed successfully!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nAutomation interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

