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

def generate_blog_content(client, topic, details, day, category):
    """Generate blog post content using Gemini AI"""
    print(f"Generating content for Day {day}: {topic}")
    
    prompt = f"""You are an expert cryptocurrency and blockchain content writer for the blog "Crypto Basic Guide" (cryptobasicguide.blogspot.com).

Write a comprehensive, detailed, SEO-optimized blog post about: {topic}

Additional Context: {details if details else 'Provide comprehensive coverage of the topic'}

Requirements:
1. Write a DETAILED, informative article (1500-2000 words) - make it comprehensive and valuable
2. Use clear headings and subheadings (## for main sections, ### for subsections)
3. Include multiple practical examples and real-world applications with explanations
4. Write in a beginner-friendly yet professional and engaging tone
5. Add actionable tips, insights, and step-by-step guidance
6. Include current trends, statistics, and future outlook
7. Use bullet points and numbered lists extensively with detailed explanations
8. Explain technical terms when first introduced
9. Add context and background information
10. Include common mistakes to avoid
11. Focus on cryptocurrency and blockchain technology
12. Category: {category}

Structure (aim for 1500-2000 words total):
- Introduction (2-3 paragraphs explaining why this topic matters)
- Main content with 4-6 detailed sections covering different aspects
- Each section should have multiple paragraphs with examples
- Include practical tips and best practices
- Common pitfalls or mistakes to avoid
- Future trends and outlook
- Key takeaways/summary
- Conclusion with call-to-action

Write detailed explanations, not just brief overviews. Each section should be substantial.

Format the content in Markdown with proper headings.

Generate the comprehensive content (1500-2000 words):"""

    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.8,
                    max_output_tokens=2048,
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
    """Generate simple Unsplash search query - using keywords to save API quota"""
    # Use simple, relevant keywords based on topic (saves AI quota)
    topic_lower = topic.lower()
    
    if 'bitcoin' in topic_lower:
        return "bitcoin cryptocurrency"
    elif 'ethereum' in topic_lower:
        return "ethereum blockchain"
    elif 'wallet' in topic_lower:
        return "crypto wallet security"
    elif 'trading' in topic_lower or 'invest' in topic_lower:
        return "cryptocurrency trading"
    elif 'nft' in topic_lower:
        return "nft digital art"
    elif 'defi' in topic_lower:
        return "decentralized finance"
    elif 'blockchain' in topic_lower:
        return "blockchain technology"
    elif 'mining' in topic_lower:
        return "crypto mining"
    elif 'altcoin' in topic_lower:
        return "altcoin cryptocurrency"
    else:
        return "cryptocurrency blockchain"


def get_unsplash_image(topic):
    """Download image from Unsplash"""
    if not UNSPLASH_ACCESS_KEY:
        print("Warning: UNSPLASH_ACCESS_KEY not set, skipping image")
        return None
    
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
                "per_page": 1
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('results') and len(data['results']) > 0:
                photo = data['results'][0]
                image_url = photo['urls']['regular']
                photographer = photo['user']['name']
                photographer_url = photo['user']['links']['html']
                
                print(f"Found image by {photographer}")
                
                # Download image
                img_response = requests.get(image_url, timeout=15)
                img_response.raise_for_status()
                
                return {
                    'data': img_response.content,
                    'photographer': photographer,
                    'photographer_url': photographer_url,
                    'unsplash_url': photo['links']['html']
                }
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
    
    # Add featured image if available with attractive styling
    if image_url:
        # Create visually appealing image section
        image_html = f'''<div class="featured-image" style="text-align: center; margin: 30px 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
    <img src="{image_url}" alt="{title}" style="max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0 5px 20px rgba(0,0,0,0.3);" />
</div>
<div style="height: 20px;"></div>'''
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
    content = generate_blog_content(client, topic, details, day, category)
    
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
    
    # Get image
    print("Step 3: Fetching image from Unsplash...")
    image_data_dict = get_unsplash_image(topic)
    
    image_url = None
    if image_data_dict:
        try:
            # Compress image to under 500KB
            compressed_data = compress_image(image_data_dict['data'])
            
            # Save locally (will be committed to GitHub)
            image_path = save_image_locally(compressed_data, day)
            
            # Use GitHub raw URL for the image (publicly accessible)
            image_url = f"https://raw.githubusercontent.com/sourcecodeRTX/Autojeta/main/images/day-{day}.jpg"
            
            # Add attribution to content
            attribution = f'<p style="text-align: center; font-size: 14px; color: #888; margin-top: 30px;"><em>Photo by <a href="{image_data_dict["photographer_url"]}" target="_blank">{image_data_dict["photographer"]}</a> on <a href="{image_data_dict["unsplash_url"]}" target="_blank">Unsplash</a></em></p>'
            content_html += "\n\n" + attribution
            
            print("✓ Image processed and saved")
            print(f"  GitHub URL: {image_url}")
        except Exception as e:
            print(f"Warning: Image processing failed: {e}")
    else:
        print("⚠ No image available, proceeding without image")
    print()
    
    # Publish to Blogger
    print("Step 4: Publishing to Blogger...")
    title = f"Day {day}: {topic}"
    labels = [category, "Cryptocurrency", "Blockchain"]
    
    success = publish_to_blogger(title, content_html, labels, image_url)
    
    if not success:
        print("Failed to publish to Blogger")
        return False
    
    print()
    
    # Update status
    print("Step 5: Updating status...")
    status = load_status()
    status['next_day'] = day + 1
    status['last_processed'] = topic
    status['last_published'] = datetime.now().isoformat()
    save_status(status)
    print("✓ Status updated")
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
