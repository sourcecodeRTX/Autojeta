#!/usr/bin/env python3
"""
Blogger Post Automation Script with AI Image Generation
Automates cryptocurrency blog posts using Google Gemini AI and Hugging Face FLUX.1
Publishes directly to Blogger via Blogger API v3

KEY FEATURES:
- Uses FLUX.1-dev model for photorealistic image generation
- NO text rendered on images (configured via prompt engineering)
- Maintains all existing functionality from original script
- Generates images specifically tailored to blog content
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
from huggingface_hub import InferenceClient

# ==================== CONFIGURATION ====================

# API Keys (Set these as environment variables)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')  # Required for content generation
HF_TOKEN = os.environ.get('HF_TOKEN', '')  # Required for FLUX.1 image generation

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


# ==================== AI IMAGE GENERATION ====================

def generate_image_prompt(client, topic):
    """
    Generate a detailed text-to-image prompt using Gemini AI.
    CRITICAL: Instructs the AI to create photorealistic images WITHOUT any text.
    """
    prompt = f"""You are an expert AI art director specializing in photorealistic cryptocurrency and blockchain imagery.

Generate a detailed text-to-image prompt for a blog post about: {topic}

CRITICAL REQUIREMENTS:
1. **ABSOLUTELY NO TEXT OR WORDS** in the image - no labels, no ticker symbols, no writing of any kind
2. Focus on PURE VISUAL ELEMENTS: physical objects, lighting, textures, composition
3. Theme: Cryptocurrency, Blockchain, Digital Finance, Futuristic Technology
4. Style: Photorealistic, Cinematic, Professional Editorial Photography
5. Quality: 8k resolution, highly detailed, Unreal Engine 5 rendering quality

VISUAL ELEMENTS TO INCLUDE:
- Physical crypto coins (gold, silver, metallic textures)
- Circuit boards, motherboards, digital technology
- Glowing effects, neon lights, holographic displays
- Professional studio lighting with depth of field
- Futuristic backgrounds (digital networks, abstract tech patterns)
- Clean, sleek, modern aesthetic

AVOID:
- ANY text, letters, numbers, ticker symbols (Bitcoin, ETH, etc.)
- Computer screens with visible text
- Charts or graphs with labels
- Newspapers or documents with readable text
- Any form of written content

Example Good Prompts:
- "A close-up macro shot of a golden physical Bitcoin coin resting on a glowing blue motherboard with intricate circuitry, cinematic lighting, depth of field, 8k resolution, highly detailed metal texture, professional product photography"
- "Multiple metallic cryptocurrency coins scattered on a dark reflective surface with neon blue and purple rim lighting, futuristic digital bokeh background, photorealistic, cinematic composition, 8k detail"
- "A sleek golden coin with circuit board patterns floating above a glowing digital network grid, volumetric lighting, photorealistic 3D render, depth of field, cinematic mood, 8k resolution"

Based on the topic "{topic}", generate ONE detailed prompt (50-80 words) that describes the visual scene in vivid detail.

Return ONLY the prompt string, nothing else:"""

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.8,
                max_output_tokens=150,
            )
        )
        image_prompt = response.text.strip().strip('"').strip("'")
        
        # Additional safety check: ensure no text-related keywords in prompt
        text_keywords = ['text', 'label', 'writing', 'words', 'letters', 'ticker', 'symbol', 'BTC', 'ETH']
        for keyword in text_keywords:
            if keyword.lower() in image_prompt.lower():
                # Remove problematic phrases
                image_prompt = image_prompt.replace(keyword, '')
        
        # Add explicit "no text" instruction to the prompt
        image_prompt = f"{image_prompt.strip()}, absolutely no text or writing visible, clean composition"
        
        print(f"🎨 Generated Image Prompt: '{image_prompt[:80]}...'")
        return image_prompt
        
    except Exception as e:
        print(f"Error generating image prompt: {e}")
        # Safe fallback prompt with no text
        return f"A photorealistic 3D render of cryptocurrency technology concept related to {topic}, golden metallic coins on glowing circuit board, cinematic lighting, 8k resolution, no text visible, clean professional composition"


def generate_image_from_hf(prompt, day):
    """
    Generate photorealistic image using Hugging Face FLUX.1-dev model.
    
    FLUX.1-dev is currently the state-of-the-art model for:
    - Photorealism and detail
    - Prompt adherence
    - Complex technological textures
    - Professional quality outputs
    
    Returns: Dictionary with image data and metadata, or None if failed
    """
    if not HF_TOKEN:
        print("❌ Error: HF_TOKEN environment variable not set")
        print("   Get your token from: https://huggingface.co/settings/tokens")
        return None

    # FLUX.1-dev: Best quality, slower (25-30 steps)
    # Alternative: "black-forest-labs/FLUX.1-schnell" - Faster, good quality (4-8 steps)
    model_id = "black-forest-labs/FLUX.1-dev"
    
    print(f"🎨 Generating AI image with {model_id}...")
    print(f"📝 Prompt: {prompt[:100]}...")
    
    try:
        client = InferenceClient(token=HF_TOKEN)
        
        # Generate the image with optimal FLUX.1 settings
        image = client.text_to_image(
            prompt,
            model=model_id,
            width=1024,      # Landscape aspect ratio
            height=768,      # Standard blog image dimensions
            guidance_scale=3.5,  # Lower guidance for FLUX = more realism
            num_inference_steps=28  # 25-30 is sweet spot for quality/speed
        )
        
        # Save to buffer for processing
        output = BytesIO()
        image.save(output, format='JPEG', quality=95)
        
        print("✅ Image generated successfully!")
        print(f"   Size: {len(output.getvalue()) / 1024:.1f}KB")
        
        # Return structured data compatible with original workflow
        return {
            'data': output.getvalue(),
            'photographer': 'AI Generation (FLUX.1-dev)',
            'photographer_url': 'https://huggingface.co/black-forest-labs/FLUX.1-dev',
            'unsplash_url': 'https://huggingface.co/',
            'image_url': f'flux-generated-day-{day}'
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error generating image: {error_msg}")
        
        # Provide helpful error messages
        if "429" in error_msg or "rate" in error_msg.lower():
            print("⚠️  Rate limit reached on Hugging Face.")
            print("   Solutions:")
            print("   1. Wait a few minutes and try again")
            print("   2. Switch to FLUX.1-schnell (faster, free tier friendly)")
            print("   3. Upgrade Hugging Face subscription for higher limits")
        elif "401" in error_msg or "unauthorized" in error_msg.lower():
            print("⚠️  Authentication failed. Check your HF_TOKEN:")
            print("   - Ensure it's set correctly in environment variables")
            print("   - Verify token is valid at https://huggingface.co/settings/tokens")
        elif "timeout" in error_msg.lower():
            print("⚠️  Request timed out. FLUX.1-dev can be slow on free tier.")
            print("   Consider switching to FLUX.1-schnell for faster generation")
        
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
    
    print(f"📦 Image compressed to {size_kb:.1f}KB (quality: {quality})")
    return output.getvalue()


def save_image_locally(image_data, day):
    """Save image to local directory"""
    os.makedirs(IMAGE_DIR, exist_ok=True)
    
    filename = f"day-{day}.jpg"
    filepath = os.path.join(IMAGE_DIR, filename)
    
    with open(filepath, 'wb') as f:
        f.write(image_data)
    
    print(f"💾 Image saved: {filepath}")
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
    """Main automation workflow with AI image generation"""
    print("=" * 70)
    print("🚀 Crypto Basic Guide - Blog Automation with AI Images (FLUX.1)")
    print("=" * 70)
    print()
    
    # Check environment variables
    missing_vars = []
    
    if not GEMINI_API_KEY:
        missing_vars.append("GEMINI_API_KEY")
    if not HF_TOKEN:
        missing_vars.append("HF_TOKEN")
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
        print("   2. HF_TOKEN - Get from: https://huggingface.co/settings/tokens")
        print("   3. Blogger OAuth (run get_oauth_token.py to generate):")
        print("      - BLOGGER_CLIENT_ID")
        print("      - BLOGGER_CLIENT_SECRET")
        print("      - BLOGGER_REFRESH_TOKEN")
        print("   4. BLOG_ID - Get from Blogger dashboard URL")
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
    
    # Step 3: Generate AI Image with FLUX.1
    print("=" * 70)
    print("STEP 3: Generating AI Image with FLUX.1-dev...")
    print("=" * 70)
    
    # Generate the image description prompt
    image_prompt = generate_image_prompt(client, topic)
    
    # Generate the actual image using Hugging Face
    image_data_dict = generate_image_from_hf(image_prompt, day)
    
    image_url = None
    
    if image_data_dict:
        try:
            # Compress image to under 500KB
            compressed_data = compress_image(image_data_dict['data'])
            
            # Save locally (will be committed to GitHub)
            save_image_locally(compressed_data, day)
            
            # Use GitHub raw URL for the image (publicly accessible)
            attribution = f'<p style="text-align: center; font-size: 13px; color: #888; margin: 10px 0 30px 0;"><em>Generated with AI (<a href="{image_data_dict["photographer_url"]}" target="_blank" style="color: #888; text-decoration: underline;">FLUX.1-dev</a>)</em></p>'
            image_url = f"https://raw.githubusercontent.com/sourcecodeRTX/Autojeta/main/images/day-{day}.jpg#{attribution}"
            
            print("✅ Image processing complete!")
            print(f"   GitHub URL: https://raw.githubusercontent.com/sourcecodeRTX/Autojeta/main/images/day-{day}.jpg")
            
        except Exception as e:
            print(f"⚠️  Warning: Image processing failed: {e}")
    else:
        print("⚠️  Image generation failed, proceeding without image")
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
    status['last_image_model'] = 'FLUX.1-dev'  # Track which model was used
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
        print(f"✅ AI-generated image included")
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
