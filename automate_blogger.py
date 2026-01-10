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

# ==================== CONFIGURATION ====================

# API Keys (Set these as environment variables)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
UNSPLASH_ACCESS_KEY = os.environ.get('UNSPLASH_ACCESS_KEY', '')
BLOGGER_API_KEY = os.environ.get('BLOGGER_API_KEY', '')

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

Write a comprehensive, SEO-optimized blog post about: {topic}

Additional Context: {details if details else 'Provide comprehensive coverage of the topic'}

Requirements:
1. Write an engaging, informative article (800-1200 words)
2. Use clear headings and subheadings (## and ###)
3. Include practical examples and real-world applications
4. Write in a beginner-friendly yet professional tone
5. Add actionable tips and insights
6. Include current trends and future outlook
7. Use bullet points and numbered lists where appropriate
8. Focus on cryptocurrency and blockchain technology
9. Category: {category}

Structure:
- Introduction (hook the reader)
- Main content with clear sections
- Key takeaways/summary
- Conclusion with call-to-action

Format the content in Markdown with proper headings.

Generate the content:"""

    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash-exp',
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
    """Convert Markdown to HTML for Blogger"""
    import re
    
    html = markdown_content
    
    # Convert headers
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    
    # Convert bold
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'__(.+?)__', r'<strong>\1</strong>', html)
    
    # Convert italic
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    html = re.sub(r'_(.+?)_', r'<em>\1</em>', html)
    
    # Convert links
    html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)
    
    # Convert bullet lists
    lines = html.split('\n')
    in_list = False
    result = []
    
    for line in lines:
        if line.strip().startswith('- ') or line.strip().startswith('* '):
            if not in_list:
                result.append('<ul>')
                in_list = True
            item = line.strip()[2:]
            result.append(f'<li>{item}</li>')
        else:
            if in_list:
                result.append('</ul>')
                in_list = False
            result.append(line)
    
    if in_list:
        result.append('</ul>')
    
    html = '\n'.join(result)
    
    # Convert paragraphs
    paragraphs = html.split('\n\n')
    html_paragraphs = []
    
    for para in paragraphs:
        para = para.strip()
        if para and not para.startswith('<'):
            html_paragraphs.append(f'<p>{para}</p>')
        else:
            html_paragraphs.append(para)
    
    return '\n\n'.join(html_paragraphs)


# ==================== IMAGE HANDLING ====================

def generate_image_search_query(client, topic):
    """Generate optimized Unsplash search query using Gemini"""
    prompt = f"""Generate a specific, visual search query for Unsplash to find high-quality cryptocurrency-related images.

Topic: {topic}

Requirements:
- Focus on cryptocurrency, blockchain, digital assets, fintech
- Use visual keywords (coins, charts, technology, network, digital)
- Keep it concise (2-4 words)
- Avoid abstract concepts

Return ONLY the search query, nothing else."""

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=50,
            )
        )
        
        query = response.text.strip().strip('"').strip("'")
        print(f"Generated image query: {query}")
        return query
        
    except Exception as e:
        print(f"Error generating image query: {e}")
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


def compress_image(image_data, max_size_kb=300):
    """Compress image to target size"""
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

def publish_to_blogger(title, content_html, labels, image_url=None):
    """Publish post to Blogger via API v3"""
    if not BLOGGER_API_KEY or not BLOG_ID:
        print("Error: BLOGGER_API_KEY or BLOG_ID not set")
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
        # Blogger will use the first image in content as featured image
        image_html = f'<div class="separator" style="clear: both; text-align: center;"><img border="0" src="{image_url}" alt="{title}" style="max-width: 100%; height: auto;" /></div>'
        post_data["content"] = image_html + "\n\n" + content_html
    
    params = {
        "key": BLOGGER_API_KEY
    }
    
    max_retries = 3
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            print(f"Publishing to Blogger: {title} (attempt {attempt + 1}/{max_retries})")
            response = requests.post(
                BLOGGER_API_URL,
                json=post_data,
                params=params,
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
    
    if not BLOGGER_API_KEY:
        print("Error: BLOGGER_API_KEY environment variable not set")
        print("Get your API key from: Google Cloud Console")
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
            # Compress image
            compressed_data = compress_image(image_data_dict['data'])
            
            # Save locally
            image_path = save_image_locally(compressed_data, day)
            
            # For Blogger, we need to upload to a hosting service or use Unsplash CDN directly
            # Using Unsplash CDN URL (recommended)
            image_url = f"https://source.unsplash.com/1200x630/?{generate_image_search_query(client, topic).replace(' ', ',')}"
            
            # Add attribution to content
            attribution = f'<p><small>Photo by <a href="{image_data_dict["photographer_url"]}">{image_data_dict["photographer"]}</a> on <a href="{image_data_dict["unsplash_url"]}">Unsplash</a></small></p>'
            content_html += "\n\n" + attribution
            
            print("✓ Image processed and saved")
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
