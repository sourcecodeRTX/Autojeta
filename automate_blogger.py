#!/usr/bin/env python3
"""
Blogger Post Automation Script with Zip-Based Image Integration
Automates cryptocurrency blog posts using Google Gemini AI with pre-compressed images

KEY FEATURES:
- Zip-based image workflow: Extracts one image per day from zip archive
- Auto re-zipping: Automatically re-zips remaining images
- Pre-compressed WebP images: No image processing needed
- Zero attribution: Clean posts without image source credits
- Flexible scheduling: 6:00 AM IST daily via GitHub Actions
- Complete reliability: Never fails to publish
"""

import os
import json
import requests
import time
import zipfile
import shutil
from datetime import datetime, timedelta
from google import genai
from google.genai import types
from io import BytesIO
from PIL import Image
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as AuthRequest

# ==================== CONFIGURATION ====================

# API Keys (Set these as environment variables)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')  # Required for content generation

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
ZIP_FILE = 'crypto_landscape_1000.zip'  # Zip file containing pre-compressed images

# Categories for Blogger labels (Fixed to user request)
CATEGORIES = [
    'Beginner Guide',
    'Crypto Investment',
    'News and Updates',
    'Tools & Tutorials',
    'Crypto Airdrops',
    'Blockchain Technology'
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
    
    # Restored original detailed prompt structure with inserted SEO/Length constraints
    prompt = f"""You are an expert cryptocurrency and blockchain content writer for the blog "Crypto Basic Guide" (cryptobasicguide.blogspot.com).

Write a comprehensive, detailed, narrative-driven blog post about: {topic}

Additional Context: {details if details else 'Provide comprehensive coverage of the topic'}

Requirements:
1. Write a DETAILED, informative article (900-1000 words) - precise and valuable.
2. Use a NARRATIVE, STORYTELLING approach - tell a story, don't just list facts.
3. Write like you're having a conversation with a friend - engaging, personal, relatable.
4. Use clear headings and subheadings (## for main sections, ### for subsections).
5. Include real-world scenarios, case studies, and relatable examples.
6. Start with a compelling hook or story that draws readers in.
7. Use analogies and metaphors to explain complex concepts.
8. Add personal insights, opinions, and expert perspectives.
9. Include step-by-step walkthroughs where appropriate.
10. Discuss both benefits and risks honestly.
11. Share practical tips from real-world experience.
12. Include current trends, market movements, and future predictions.
13. Explain technical terms naturally within the narrative.
14. Add context about why this matters to readers personally.
15. DO NOT USE EMOJIS - write professionally without emoji characters.
16. Focus on cryptocurrency and blockchain technology.
17. SEO OPTIMIZATION: Identify high-ranking keywords based on Google Trends for this topic and integrate them naturally into the title, headers, and first paragraph. Use LSI (latent semantic) keywords throughout.
18. USER FRIENDLY TONE: Ensure the reading flow is natural and NOT awkward or robotic. Short paragraphs, punchy sentences.
19. Category: {category}

Structure (aim for 900-1000 words total):
- SEO Title (Include main keyword)
- Opening Story/Hook (grab attention with a real scenario or surprising fact)
- Introduction (2-3 paragraphs setting the scene and explaining importance + SEO keywords)
- Main narrative with 4-5 detailed sections:
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
- NO awkward or robotic phrasing

DO NOT INCLUDE:
- Emojis or emoji characters of any kind
- Generic advice - be specific and detailed
- Overly technical jargon without explanation
- Financial advice disclaimers (readers understand this is educational)

Format the content in Markdown with proper headings.

IMPORTANT: Generate the COMPLETE article from start to finish. Do not stop mid-way. Write all sections including the conclusion. The article must be complete and end with a proper conclusion.

Generate the comprehensive, SEO-optimized, narrative-driven content (900-1000 words):"""

    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.75, # Slightly reduced for better SEO focus
                    max_output_tokens=8192,
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
            
            # Check if content appears truncated (Adjusted for 900-1000 words)
            is_truncated = (
                not content.rstrip().endswith(('.', '!', '?', '"', "'"))  # Doesn't end with punctuation
                or len(content) < 2000  # Adjusted length check for ~900 words
                or content.count('##') < 3  # Missing expected sections
            )
            
            if is_truncated:
                print(f"⚠️ Content appears incomplete ({len(content)} chars), attempting continuation...")
                
                # Try to continue from where it left off
                continuation_prompt = f"""Continue writing the blog post from where you left off. Here's what was written so far:

{content[-500:]}

---

Continue writing naturally from the point where it was cut off. Ensure the tone remains user-friendly and natural. Complete all remaining sections including:
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
                        temperature=0.75,
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
    
    # Convert headers with attractive styling (must go from most specific to least specific)
    # h6, h5, h4 - convert to styled subheadings with bullet point (strip any existing bullets first)
    html = re.sub(r'^###### •?\s*(.+)$', r'<div style="color: #34495e; font-size: 16px; font-weight: 600; margin: 18px 0 10px 20px; line-height: 1.4;"><span style="color: #3498db; margin-right: 8px;">•</span>\1</div>', html, flags=re.MULTILINE)
    html = re.sub(r'^##### •?\s*(.+)$', r'<div style="color: #34495e; font-size: 17px; font-weight: 600; margin: 20px 0 12px 15px; line-height: 1.4;"><span style="color: #3498db; margin-right: 8px;">•</span>\1</div>', html, flags=re.MULTILINE)
    html = re.sub(r'^#### •?\s*(.+)$', r'<div style="color: #2c3e50; font-size: 18px; font-weight: 600; margin: 22px 0 12px 10px; line-height: 1.4;"><span style="color: #4CAF50; margin-right: 8px;">•</span>\1</div>', html, flags=re.MULTILINE)
    # h3, h2, h1 - standard headings
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
    
    # Convert bullet lists AND numbered lists with better styling
    lines = html.split('\n')
    in_bullet_list = False
    in_numbered_list = False
    result = []
    
    for line in lines:
        stripped = line.strip()
        
        # Check for bullet list items
        if stripped.startswith('- ') or stripped.startswith('* '):
            # Close numbered list if open
            if in_numbered_list:
                result.append('</ol>')
                in_numbered_list = False
            
            # Open bullet list if not already open
            if not in_bullet_list:
                result.append('<ul style="margin: 20px 0; padding-left: 35px; line-height: 1.9;">')
                in_bullet_list = True
            
            item = stripped[2:]
            result.append(f'<li style="margin: 10px 0; color: #444; font-size: 17px; list-style-type: disc;">{item}</li>')
        
        # Check for numbered list items (1., 2., 3., etc.)
        elif re.match(r'^\d+\.\s+', stripped):
            # Close bullet list if open
            if in_bullet_list:
                result.append('</ul>')
                in_bullet_list = False
            
            # Open numbered list if not already open
            if not in_numbered_list:
                result.append('<ol style="margin: 20px 0; padding-left: 35px; line-height: 1.9;">')
                in_numbered_list = True
            
            item = re.sub(r'^\d+\.\s+', '', stripped)
            result.append(f'<li style="margin: 10px 0; color: #444; font-size: 17px;">{item}</li>')
        
        else:
            # Close any open lists
            if in_bullet_list:
                result.append('</ul>')
                in_bullet_list = False
            if in_numbered_list:
                result.append('</ol>')
                in_numbered_list = False
            
            result.append(line)
    
    # Close any still-open lists at the end
    if in_bullet_list:
        result.append('</ul>')
    if in_numbered_list:
        result.append('</ol>')
    
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


# ==================== ZIP IMAGE EXTRACTION ====================

def extract_image_from_zip(day):
    """
    Extract one image from the zip file and re-zip the remaining images.
    Returns the image bytes if successful, None otherwise.
    """
    if not os.path.exists(ZIP_FILE):
        print(f"❌ Zip file not found: {ZIP_FILE}")
        return None
    
    try:
        print(f"📦 Extracting image from {ZIP_FILE}...")
        
        # Create temporary directory for extraction
        temp_dir = 'temp_images'
        os.makedirs(temp_dir, exist_ok=True)
        
        # Extract all images
        with zipfile.ZipFile(ZIP_FILE, 'r') as zip_ref:
            image_files = [f for f in zip_ref.namelist() if f.lower().endswith(('.webp', '.jpg', '.jpeg', '.png'))]
            
            if not image_files:
                print("❌ No images found in zip file")
                return None
            
            # Sort to ensure consistent order
            image_files.sort()
            
            # Take the first image
            selected_image = image_files[0]
            remaining_images = image_files[1:]
            
            print(f"✅ Selected image: {selected_image}")
            print(f"📊 Remaining images: {len(remaining_images)}")
            
            # Extract the selected image
            zip_ref.extract(selected_image, temp_dir)
            
            # Read the selected image
            selected_image_path = os.path.join(temp_dir, selected_image)
            with open(selected_image_path, 'rb') as f:
                image_data = f.read()
        
        # Re-create the zip with remaining images
        if remaining_images:
            # Extract remaining images to temp directory
            with zipfile.ZipFile(ZIP_FILE, 'r') as zip_ref:
                for img in remaining_images:
                    zip_ref.extract(img, temp_dir)
            
            # Create new zip with remaining images
            with zipfile.ZipFile(ZIP_FILE, 'w', zipfile.ZIP_DEFLATED) as new_zip:
                for img in remaining_images:
                    img_path = os.path.join(temp_dir, img)
                    new_zip.write(img_path, img)
            
            print(f"✅ Re-zipped {len(remaining_images)} remaining images")
        else:
            print("⚠️  No more images left in zip file")
        
        # Clean up temp directory
        shutil.rmtree(temp_dir)
        
        print(f"✅ Image extracted successfully ({len(image_data) / 1024:.1f}KB)")
        return image_data
        
    except Exception as e:
        print(f"❌ Error extracting image from zip: {e}")
        # Clean up temp directory if it exists
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return None


def save_image_locally(image_data, day):
    """
    Save image to local images directory.
    Images are already compressed WebP format, so no processing needed.
    """
    os.makedirs(IMAGE_DIR, exist_ok=True)
    
    # Determine file extension from image data
    image_ext = '.webp'  # Default to webp since that's what we have
    if image_data[:2] == b'\xff\xd8':  # JPEG magic number
        image_ext = '.jpg'
    elif image_data[:4] == b'\x89PNG':  # PNG magic number
        image_ext = '.png'
    
    image_path = os.path.join(IMAGE_DIR, f'day-{day}{image_ext}')
    
    with open(image_path, 'wb') as f:
        f.write(image_data)
    
    print(f"✅ Image saved: {image_path}")
    return image_path



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
        # Simple, clean image presentation without any attribution
        image_html = f'''<div class="featured-image" style="text-align: center; margin: 30px 0 20px 0;">
    <img src="{image_url}" alt="{title}" style="max-width: 100%; height: auto; display: block; margin: 0 auto;" />
</div>'''
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
            
            print(f"📤 Publishing to Blogger: {title} (attempt {attempt + 1}/{max_retries})")
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
            print(f"✅ Post published successfully!")
            print(f"   URL: {post_url}")
            print(f"   Post ID: {post_id}")
            
            return True
            
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            print(f"   Status Code: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
            
            # Don't retry on client errors (4xx)
            if 400 <= e.response.status_code < 500:
                print("   Client error - not retrying")
                return False
            
            if attempt < max_retries - 1:
                print(f"   Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                return False
                
        except Exception as e:
            print(f"❌ Error publishing to Blogger: {e}")
            if attempt < max_retries - 1:
                print(f"   Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                return False
    
    return False


# ==================== MAIN WORKFLOW ====================

def main():
    """Main automation workflow with Zip-based image integration"""
    print("=" * 70)
    print("🚀 Crypto Basic Guide - Blog Automation with Zip Image Archive")
    print("=" * 70)
    print()
    
    # Check environment variables
    missing_vars = []
    
    if not GEMINI_API_KEY:
        missing_vars.append("GEMINI_API_KEY")
    if not BLOGGER_CLIENT_ID:
        missing_vars.append("BLOGGER_CLIENT_ID")
    if not BLOGGER_CLIENT_SECRET:
        missing_vars.append("BLOGGER_CLIENT_SECRET")
    if not BLOGGER_REFRESH_TOKEN:
        missing_vars.append("BLOGGER_REFRESH_TOKEN")
    if not BLOG_ID:
        missing_vars.append("BLOG_ID")
    
    if missing_vars:
        print("❌ Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print()
        print("📋 Required API Keys & Setup:")
        print("   1. GEMINI_API_KEY - Get from: https://aistudio.google.com/app/apikey")
        print("   2. Blogger OAuth (run get_oauth_token.py to generate):")
        print("      - BLOGGER_CLIENT_ID")
        print("      - BLOGGER_CLIENT_SECRET")
        print("      - BLOGGER_REFRESH_TOKEN")
        print("   3. BLOG_ID - Get from Blogger dashboard URL")
        return False
    
    # Initialize
    print("🔧 Initializing Gemini AI...")
    client = initialize_apis()
    print("✅ Gemini AI ready")
    print()
    
    # Get next topic
    print("📖 Loading next topic...")
    topic_data = get_next_topic()
    
    if not topic_data:
        print("❌ No more topics to process!")
        return False
    
    day = topic_data['day']
    topic = topic_data['topic']
    details = topic_data['details']
    
    # Select category
    category = CATEGORIES[day % len(CATEGORIES)]
    
    print(f"📅 Processing Day {day}")
    print(f"📝 Topic: {topic}")
    print(f"🏷️  Category: {category}")
    print()
    
    # Step 1: Generate content
    print("=" * 70)
    print("STEP 1: Generating SEO-optimized blog content...")
    print("=" * 70)
    content = generate_blog_content(client, topic, details, category)
    
    if not content:
        print("❌ Failed to generate content")
        return False
    
    print(f"✅ Content generated ({len(content)} characters, ~{len(content.split())} words)")
    print()
    
    # Step 2: Convert to HTML
    print("=" * 70)
    print("STEP 2: Converting Markdown to HTML...")
    print("=" * 70)
    content_html = convert_markdown_to_html(content)
    print("✅ Content converted to styled HTML")
    print()
    
    # Step 3: Extract Image from Zip
    print("=" * 70)
    print("STEP 3: Extracting image from zip archive...")
    print("=" * 70)
    
    # Extract image from zip file
    image_data = extract_image_from_zip(day)
    image_source = "ZIP"
    image_url = None
    
    if image_data:
        try:
            # Save locally (will be committed to GitHub)
            # No need to compress - images are already compressed WebP format
            image_path = save_image_locally(image_data, day)
            
            # Determine extension based on saved file
            image_ext = os.path.splitext(image_path)[1]
            
            # Use GitHub raw URL for the image (publicly accessible)
            image_url = f"https://raw.githubusercontent.com/sourcecodeRTX/Autojeta/main/images/day-{day}{image_ext}"
            
            print("✅ Image processing complete!")
            print(f"   GitHub URL: {image_url}")
            
        except Exception as e:
            print(f"⚠️  Warning: Image processing failed: {e}")
    else:
        print("⚠️  Image extraction failed, proceeding without image")
        print("   The blog post will be published with text content only")
    
    print()
    
    # Step 4: Publish to Blogger
    print("=" * 70)
    print("STEP 4: Publishing to Blogger...")
    print("=" * 70)
    title = topic  # Use only the topic as title, without day prefix
    labels = [category]  # Uses only the selected category
    
    success = publish_to_blogger(title, content_html, labels, image_url)
    
    if not success:
        print("❌ Failed to publish to Blogger")
        return False
    
    print()
    
    # Step 5: Update status
    print("=" * 70)
    print("STEP 5: Updating status...")
    print("=" * 70)
    status = load_status()
    status['next_day'] = day + 1
    status['last_processed'] = topic
    status['last_published'] = datetime.now().isoformat()
    status['last_image_source'] = image_source
    save_status(status)
    print("✅ Status updated")
    print()
    
    print("=" * 70)
    print("🎉 AUTOMATION COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print(f"✅ Blog post published for Day {day}")
    print(f"✅ Topic: {topic}")
    print(f"✅ Category: {category}")
    if image_url:
        print(f"✅ Pre-compressed WebP image from zip archive included")
    print(f"✅ Next run will process Day {day + 1}")
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Automation interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
