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
        try:
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    print("⚠️ status.json is empty, creating new status")
                    return {"next_day": 1, "last_processed": "", "used_images": []}
                return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"⚠️ Error parsing status.json: {e}")
            print("Creating backup and starting fresh...")
            # Backup corrupted file
            if os.path.exists(STATUS_FILE):
                backup_file = f"{STATUS_FILE}.backup"
                os.rename(STATUS_FILE, backup_file)
                print(f"Corrupted file backed up to: {backup_file}")
            return {"next_day": 1, "last_processed": "", "used_images": []}
        except Exception as e:
            print(f"⚠️ Unexpected error loading status: {e}")
            return {"next_day": 1, "last_processed": "", "used_images": []}
    return {"next_day": 1, "last_processed": "", "used_images": []}


def save_status(status):
    """Save status to status.json with robust error handling"""
    try:
        # Ensure used_images key exists
        if 'used_images' not in status:
            status['used_images'] = []
        
        # Write to temp file first
        temp_file = f"{STATUS_FILE}.tmp"
        with open(temp_file, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(status, f, indent=2, ensure_ascii=False)
            f.write('\n')  # Ensure file ends with newline
        
        # Verify temp file is valid JSON
        with open(temp_file, 'r', encoding='utf-8') as f:
            json.load(f)
        
        # Replace original file
        if os.path.exists(STATUS_FILE):
            os.remove(STATUS_FILE)
        os.rename(temp_file, STATUS_FILE)
        
    except Exception as e:
        print(f"⚠️ Error saving status: {e}")
        # Clean up temp file if it exists
        temp_file = f"{STATUS_FILE}.tmp"
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise


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
18. USE VISUAL ENHANCEMENTS naturally when they add value (don't overuse - 2-4 per article maximum)

Visual Enhancement Syntax (use sparingly and naturally):

A) Info Boxes - Use [TIP], [WARNING], [BEST_PRACTICE], or [KEY_TAKEAWAY] on a line by itself, followed by the content:
   [TIP]
   Always enable two-factor authentication on exchange accounts for enhanced security.

B) Comparison Tables - Use standard markdown tables with | separators:
   | Feature | Bitcoin | Ethereum |
   |---------|---------|----------|
   | Speed | 10 min | 15 sec |

C) Code Examples - Use standard code blocks with triple backticks:
   ```javascript
   const wallet = getWalletBalance(address);
   ```

D) Timeline - Use [TIMELINE] followed by bullet points with Year/Event format:
   [TIMELINE]
   - 2009: Bitcoin Launch - First cryptocurrency created
   - 2015: Ethereum Emerges - Smart contracts introduced

E) Pros & Cons - Use [PROS] and [CONS] sections with bullet points:
   [PROS]
   - Complete control over your funds
   - Lower transaction fees
   
   [CONS]
   - High price volatility
   - Regulatory uncertainty

F) FAQ - Use [FAQ] followed by Q: and A: format:
   [FAQ]
   Q: What is the best cryptocurrency for beginners?
   A: Bitcoin and Ethereum are recommended for beginners due to their stability and extensive resources.
   
   Q: How much money do I need to start?
   A: You can start with as little as $10-$50 on most exchanges.

IMPORTANT: Use these enhancements ONLY where they genuinely add value. Not every article needs all of them. Use 2-4 maximum per article.

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
    """Convert Markdown to beautifully styled HTML for Blogger with visual enhancements"""
    import re
    
    html = markdown_content
    
    # ==================== PHASE 1: PROCESS BLOCK ELEMENTS (ENHANCEMENTS) ====================
    # CRITICAL: Process in correct order to avoid conflicts!
    # 1. CODE BLOCKS (first - protect from all other processing with placeholders)
    # 2. INFO BOXES
    # 3. TABLES
    # 4. PROS/CONS (before timeline - both use bullets)
    # 5. FAQ (before timeline)
    # 6. TIMELINE (last - most general bullet pattern)
    
    # ENHANCEMENT #7: Code Examples - PROCESS FIRST with placeholder protection
    code_pattern = r'```(\w*)\n(.*?)```'
    code_blocks = {}
    code_counter = 0
    
    def convert_code(match):
        nonlocal code_counter
        lang = match.group(1) or 'code'
        code = match.group(2).strip()
        
        # Escape HTML
        code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        code_html = '<div style="background: #1e1e1e; padding: 25px; border-radius: 4px; margin: 25px 0; overflow-x: auto; box-shadow: 0 2px 8px rgba(0,0,0,0.2);">'
        code_html += f'<div style="color: #d4d4d4; font-family: \'Consolas\', \'Monaco\', \'Courier New\', monospace; font-size: 14px; line-height: 1.6; white-space: pre;">{code}</div>'
        code_html += '</div>'
        
        # Store code block with unique placeholder (using HTML comment to avoid markdown processing)
        placeholder = f'<!--CODEBLOCK{code_counter}-->'
        code_blocks[placeholder] = code_html
        code_counter += 1
        
        return placeholder
    
    html = re.sub(code_pattern, convert_code, html, flags=re.DOTALL)
    
    # ENHANCEMENT #1: Info Boxes (4 types with theme colors)
    # [TIP] - Gold theme color (#ffcd04)
    html = re.sub(
        r'\[TIP\]\n([^\[]+?)(?=\n\n|\n\[|$)',
        r'<div style="background: linear-gradient(135deg, #fff9e6 0%, #fff4d1 100%); border-left: 5px solid #ffcd04; padding: 20px; margin: 25px 0; border-radius: 4px; box-shadow: 0 2px 6px rgba(255, 205, 4, 0.15);"><div style="display: flex; align-items: flex-start; gap: 15px; flex-wrap: wrap;"><div style="font-size: 28px; flex-shrink: 0;">💡</div><div style="flex: 1; min-width: 200px;"><strong style="color: #253137; font-size: 18px; display: block; margin-bottom: 8px; font-weight: 600;">Pro Tip</strong><p style="margin: 0; color: #656565; line-height: 1.7;">\1</p></div></div></div>',
        html, flags=re.MULTILINE | re.DOTALL
    )
    
    # [WARNING] - Orange/Red
    html = re.sub(
        r'\[WARNING\]\n([^\[]+?)(?=\n\n|\n\[|$)',
        r'<div style="background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); border-left: 5px solid #ff9800; padding: 20px; margin: 25px 0; border-radius: 4px; box-shadow: 0 2px 6px rgba(255, 152, 0, 0.15);"><div style="display: flex; align-items: flex-start; gap: 15px; flex-wrap: wrap;"><div style="font-size: 28px; flex-shrink: 0;">⚠️</div><div style="flex: 1; min-width: 200px;"><strong style="color: #e65100; font-size: 18px; display: block; margin-bottom: 8px; font-weight: 600;">Warning</strong><p style="margin: 0; color: #656565; line-height: 1.7;">\1</p></div></div></div>',
        html, flags=re.MULTILINE | re.DOTALL
    )
    
    # [BEST_PRACTICE] - Green
    html = re.sub(
        r'\[BEST_PRACTICE\]\n([^\[]+?)(?=\n\n|\n\[|$)',
        r'<div style="background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); border-left: 5px solid #4CAF50; padding: 20px; margin: 25px 0; border-radius: 4px; box-shadow: 0 2px 6px rgba(76, 175, 80, 0.15);"><div style="display: flex; align-items: flex-start; gap: 15px; flex-wrap: wrap;"><div style="font-size: 28px; flex-shrink: 0;">✅</div><div style="flex: 1; min-width: 200px;"><strong style="color: #2e7d32; font-size: 18px; display: block; margin-bottom: 8px; font-weight: 600;">Best Practice</strong><p style="margin: 0; color: #656565; line-height: 1.7;">\1</p></div></div></div>',
        html, flags=re.MULTILINE | re.DOTALL
    )
    
    # [KEY_TAKEAWAY] - Navy theme color (#253137)
    html = re.sub(
        r'\[KEY_TAKEAWAY\]\n([^\[]+?)(?=\n\n|\n\[|$)',
        r'<div style="background: linear-gradient(135deg, #e8eaf1 0%, #d4d8e6 100%); border-left: 5px solid #253137; padding: 20px; margin: 25px 0; border-radius: 4px; box-shadow: 0 2px 6px rgba(37, 49, 55, 0.15);"><div style="display: flex; align-items: flex-start; gap: 15px; flex-wrap: wrap;"><div style="font-size: 28px; flex-shrink: 0;">🔑</div><div style="flex: 1; min-width: 200px;"><strong style="color: #253137; font-size: 18px; display: block; margin-bottom: 8px; font-weight: 600;">Key Takeaway</strong><p style="margin: 0; color: #656565; line-height: 1.7;">\1</p></div></div></div>',
        html, flags=re.MULTILINE | re.DOTALL
    )
    
    # ENHANCEMENT #3: Comparison Tables (convert markdown tables)
    # Convert markdown tables to HTML tables with theme styling
    table_pattern = r'(\|.+\|\n\|[-:\s|]+\|\n(?:\|.+\|\n?)+)'
    
    def convert_table(match):
        table_md = match.group(1)
        lines = [line.strip() for line in table_md.split('\n') if line.strip()]
        
        if len(lines) < 2:
            return match.group(0)
        
        # Parse header
        header = [cell.strip() for cell in lines[0].split('|')[1:-1]]
        # Skip separator line (lines[1])
        # Parse data rows
        rows = [[cell.strip() for cell in line.split('|')[1:-1]] for line in lines[2:]]
        
        # Build HTML table with theme colors
        table_html = '<div style="overflow-x: auto; margin: 25px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-radius: 4px;">'
        table_html += '<table style="width: 100%; border-collapse: collapse; background: white; border-radius: 4px; overflow: hidden;">'
        
        # Header with gold gradient
        table_html += '<thead><tr style="background: linear-gradient(135deg, #ffcd04 0%, #ffc107 100%); color: #253137;">'
        for i, cell in enumerate(header):
            border = ' border-right: 1px solid rgba(37,49,55,0.1);' if i < len(header) - 1 else ''
            table_html += f'<th style="padding: 18px; text-align: left; font-weight: 600; font-size: 15px;{border}">{cell}</th>'
        table_html += '</tr></thead>'
        
        # Body rows
        table_html += '<tbody>'
        for idx, row in enumerate(rows):
            bg = ' background: #fafafa;' if idx % 2 == 1 else ''
            table_html += f'<tr style="border-bottom: 1px solid #f2f2f6;{bg}">'
            for i, cell in enumerate(row):
                border = ' border-right: 1px solid #f2f2f6;' if i < len(row) - 1 else ''
                align = ' text-align: center;' if i > 0 else ''
                weight = ' font-weight: 500;' if i == 0 else ''
                color = ' color: #253137;' if i == 0 else ' color: #656565;'
                table_html += f'<td style="padding: 15px;{align}{weight}{color}{border}">{cell}</td>'
            table_html += '</tr>'
        table_html += '</tbody></table></div>'
        
        return table_html
    
    html = re.sub(table_pattern, convert_table, html, flags=re.MULTILINE)
    
    # ENHANCEMENT #9: Pros & Cons Layout - BEFORE Timeline (both use bullets)
    # Match only consecutive bullet lines, stop at blank line or new section
    proscons_pattern = r'\[PROS\]\n((?:- [^\n]+\n?)+?)\n+\[CONS\]\n((?:- [^\n]+\n?)+?)(?=\n\n|\n##|\n\[|$)'
    
    def convert_proscons(match):
        pros = [line.strip()[2:] for line in match.group(1).strip().split('\n') if line.strip().startswith('- ')]
        cons = [line.strip()[2:] for line in match.group(2).strip().split('\n') if line.strip().startswith('- ')]
        
        pc_html = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin: 25px 0;">'
        
        # Pros (Green)
        pc_html += '<div style="background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); border-radius: 4px; padding: 25px; box-shadow: 0 2px 8px rgba(76, 175, 80, 0.15);">'
        pc_html += '<h3 style="color: #2e7d32; font-size: 20px; margin: 0 0 20px 0; display: flex; align-items: center; gap: 10px;"><span style="font-size: 24px;">✅</span> Advantages</h3>'
        pc_html += '<ul style="list-style: none; padding: 0; margin: 0;">'
        for idx, pro in enumerate(pros):
            border = ' border-bottom: 1px solid rgba(46, 125, 50, 0.2);' if idx < len(pros) - 1 else ''
            pc_html += f'<li style="padding: 10px 0;{border} display: flex; align-items: flex-start; gap: 10px;"><span style="color: #4CAF50; font-size: 18px; font-weight: bold;">✓</span><span style="color: #656565; line-height: 1.6;">{pro}</span></li>'
        pc_html += '</ul></div>'
        
        # Cons (Red)
        pc_html += '<div style="background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%); border-radius: 4px; padding: 25px; box-shadow: 0 2px 8px rgba(244, 67, 54, 0.15);">'
        pc_html += '<h3 style="color: #c62828; font-size: 20px; margin: 0 0 20px 0; display: flex; align-items: center; gap: 10px;"><span style="font-size: 24px;">❌</span> Disadvantages</h3>'
        pc_html += '<ul style="list-style: none; padding: 0; margin: 0;">'
        for idx, con in enumerate(cons):
            border = ' border-bottom: 1px solid rgba(198, 40, 40, 0.2);' if idx < len(cons) - 1 else ''
            pc_html += f'<li style="padding: 10px 0;{border} display: flex; align-items: flex-start; gap: 10px;"><span style="color: #f44336; font-size: 18px; font-weight: bold;">✗</span><span style="color: #656565; line-height: 1.6;">{con}</span></li>'
        pc_html += '</ul></div>'
        
        pc_html += '</div>'
        return pc_html
    
    html = re.sub(proscons_pattern, convert_proscons, html, flags=re.MULTILINE | re.DOTALL)
    
    # ENHANCEMENT #12: FAQ Section - BEFORE Timeline  
    # Match all content after [FAQ] until next section heading or enhancement tag
    faq_pattern = r'\[FAQ\]\n((?:(?!\n##|\[PROS\]|\[CONS\]|\[TIMELINE\]).)+)'
    
    def convert_faq(match):
        faq_text = match.group(1).strip()
        # Match Q&A pairs - answers can be multi-line until next Q or end
        qa_pattern = r'Q: (.+?)\nA: (.*?)(?=\n\nQ:|$)'
        qa_pairs = re.findall(qa_pattern, faq_text, re.DOTALL)
        
        colors = ['#ffcd04', '#4CAF50', '#253137']  # Rotate icon colors
        
        faq_html = '<div style="margin: 25px 0;">'
        for idx, (question, answer) in enumerate(qa_pairs):
            color = colors[idx % len(colors)]
            margin = ' margin-bottom: 15px;' if idx < len(qa_pairs) - 1 else ''
            
            faq_html += f'<div style="background: white; border: 2px solid #f2f2f6; border-radius: 4px; padding: 20px;{margin} box-shadow: 0 2px 4px rgba(0,0,0,0.03);">'
            faq_html += '<div style="display: flex; align-items: flex-start; gap: 15px; flex-wrap: wrap;">'
            faq_html += f'<div style="font-size: 24px; color: {color}; flex-shrink: 0;">❓</div>'
            faq_html += '<div style="flex: 1; min-width: 200px;">'
            faq_html += f'<strong style="color: #253137; font-size: 18px; display: block; margin-bottom: 10px; font-weight: 600;">{question.strip()}</strong>'
            faq_html += f'<p style="color: #656565; line-height: 1.7; margin: 0;">{answer.strip()}</p>'
            faq_html += '</div></div></div>'
        
        faq_html += '</div>'
        return faq_html
    
    html = re.sub(faq_pattern, convert_faq, html, flags=re.MULTILINE | re.DOTALL)
    
    # ENHANCEMENT #8: Timeline (visual progress indicator) - LAST, after PROS/CONS and FAQ
    # Match only consecutive lines starting with - , stop at blank line or new section
    timeline_pattern = r'\[TIMELINE\]\n((?:- [^\n]+\n?)+?)(?=\n\n|\n##|\n\[|$)'
    
    def convert_timeline(match):
        items = [line.strip()[2:] for line in match.group(1).strip().split('\n') if line.strip().startswith('- ')]
        
        colors = ['#ffcd04', '#4CAF50', '#253137']  # Theme colors rotation
        bg_colors = ['#fff9e6', '#e8f5e9', '#e8eaf1']
        
        timeline_html = '<div style="position: relative; padding: 30px 0 30px 40px; margin: 25px 0;">'
        timeline_html += '<div style="position: absolute; left: 15px; top: 0; bottom: 0; width: 3px; background: linear-gradient(180deg, #ffcd04 0%, #4CAF50 50%, #253137 100%);"></div>'
        
        for idx, item in enumerate(items):
            color = colors[idx % len(colors)]
            bg_color = bg_colors[idx % len(bg_colors)]
            
            # Parse title and description
            parts = item.split(' - ', 1)
            title = parts[0] if len(parts) > 0 else item
            desc = parts[1] if len(parts) > 1 else ''
            
            margin = ' margin-bottom: 40px;' if idx < len(items) - 1 else ''
            timeline_html += f'<div style="position: relative;{margin}">'
            timeline_html += f'<div style="position: absolute; left: -32px; width: 20px; height: 20px; background: {color}; border: 4px solid white; border-radius: 50%; box-shadow: 0 0 0 3px {bg_color};"></div>'
            timeline_html += f'<div style="background: white; padding: 20px; border-radius: 4px; border: 2px solid {bg_color}; box-shadow: 0 2px 6px rgba(0,0,0,0.05);">'
            timeline_html += f'<strong style="color: {color}; font-size: 18px; display: block; margin-bottom: 5px;">{title}</strong>'
            if desc:
                timeline_html += f'<p style="color: #656565; margin: 0; line-height: 1.6;">{desc}</p>'
            timeline_html += '</div></div>'
        
        timeline_html += '</div>'
        return timeline_html
    
    html = re.sub(timeline_pattern, convert_timeline, html, flags=re.MULTILINE | re.DOTALL)
    
    # ==================== PHASE 2: PROCESS STANDARD MARKDOWN ====================
    
    # Convert headers with attractive styling (from h1 to h6 for complete support)
    # Process from most specific (most #) to least specific (fewest #) to avoid conflicts
    html = re.sub(r'^###### (.+)$', r'<h6 style="color: #34495e; font-size: 16px; font-weight: 600; margin: 20px 0 12px 0; line-height: 1.4;">\1</h6>', html, flags=re.MULTILINE)
    html = re.sub(r'^##### (.+)$', r'<h5 style="color: #2c3e50; font-size: 18px; font-weight: 600; margin: 22px 0 13px 0; line-height: 1.4;">\1</h5>', html, flags=re.MULTILINE)
    html = re.sub(r'^#### (.+)$', r'<h4 style="color: #2c3e50; font-size: 20px; font-weight: 600; margin: 25px 0 14px 0; line-height: 1.4; border-left: 3px solid #9b59b6; padding-left: 12px;">\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3 style="color: #2c3e50; font-size: 22px; font-weight: 600; margin: 28px 0 15px 0; line-height: 1.4; border-left: 4px solid #3498db; padding-left: 15px;">\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2 style="color: #1a1a1a; font-size: 28px; font-weight: 700; margin: 35px 0 20px 0; padding-bottom: 12px; border-bottom: 3px solid #4CAF50; line-height: 1.3;">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1 style="color: #1a1a1a; font-size: 32px; font-weight: 800; margin: 40px 0 25px 0;">\1</h1>', html, flags=re.MULTILINE)
    
    # Convert bold text with special handling for bold labels followed by colons
    # First, handle bold labels followed by colon (like "Blockchain Solution:") - make them stand out more
    html = re.sub(r'\*\*([^*]+?):\*\*', r'<strong style="color: #2196F3; font-weight: 700; display: block; margin-top: 20px; margin-bottom: 8px; font-size: 18px;">\1:</strong>', html)
    html = re.sub(r'__([^_]+?):__', r'<strong style="color: #2196F3; font-weight: 700; display: block; margin-top: 20px; margin-bottom: 8px; font-size: 18px;">\1:</strong>', html)
    
    # Then handle regular bold text
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color: #2196F3; font-weight: 600;">\1</strong>', html)
    html = re.sub(r'__(.+?)__', r'<strong style="color: #2196F3; font-weight: 600;">\1</strong>', html)
    
    # Convert italic
    html = re.sub(r'\*([^\*]+?)\*', r'<em style="color: #555;">\1</em>', html)
    html = re.sub(r'_([^_]+?)_', r'<em style="color: #555;">\1</em>', html)
    
    # Convert links with styling
    html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" style="color: #3498db; text-decoration: none; border-bottom: 2px solid #3498db;">\1</a>', html)
    
    # Convert lists (both bullet and numbered) with better styling
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
            
            # Open bullet list if not open
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
            
            # Open numbered list if not open
            if not in_numbered_list:
                result.append('<ol style="margin: 20px 0; padding-left: 35px; line-height: 1.9;">')
                in_numbered_list = True
            
            # Extract the item content after the number and period
            item = re.sub(r'^\d+\.\s+', '', stripped)
            result.append(f'<li style="margin: 10px 0; color: #444; font-size: 17px;">{item}</li>')
        
        else:
            # Close any open list
            if in_bullet_list:
                result.append('</ul>')
                in_bullet_list = False
            if in_numbered_list:
                result.append('</ol>')
                in_numbered_list = False
            
            result.append(line)
    
    # Close any remaining open lists
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
    
    # ==================== PHASE 3: RESTORE CODE BLOCKS ====================
    # Replace placeholders with actual code block HTML (after all markdown processing)
    for placeholder, code_html in code_blocks.items():
        html_content = html_content.replace(placeholder, code_html)
    
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

