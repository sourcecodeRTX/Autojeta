#!/usr/bin/env python3
"""
Test script to validate all APIs and configurations before running automation
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gemini_api():
    """Test Gemini AI API connection"""
    print("\n🧪 Testing Gemini AI API...")
    
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY not set")
        return False
    
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents='Say "Hello World" in 5 words',
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=50,
            )
        )
        
        result = response.text.strip()
        print(f"✅ Gemini AI connected: {result[:50]}")
        return True
        
    except Exception as e:
        print(f"❌ Gemini AI error: {e}")
        return False


def test_unsplash_api():
    """Test Unsplash API connection"""
    print("\n🧪 Testing Unsplash API...")
    
    api_key = os.environ.get('UNSPLASH_ACCESS_KEY')
    if not api_key:
        print("⚠️  UNSPLASH_ACCESS_KEY not set (optional, skipping)")
        return True
    
    try:
        import requests
        
        url = "https://api.unsplash.com/search/photos"
        headers = {"Authorization": f"Client-ID {api_key}"}
        params = {"query": "bitcoin", "per_page": 1}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get('results'):
            print(f"✅ Unsplash connected: Found {data['total']} images")
            return True
        else:
            print("⚠️  Unsplash connected but no results")
            return True
            
    except Exception as e:
        print(f"❌ Unsplash error: {e}")
        return False


def test_blogger_api():
    """Test Blogger API connection"""
    print("\n🧪 Testing Blogger API...")
    
    api_key = os.environ.get('BLOGGER_API_KEY')
    blog_id = os.environ.get('BLOG_ID')
    
    if not api_key:
        print("❌ BLOGGER_API_KEY not set")
        return False
    
    if not blog_id:
        print("❌ BLOG_ID not set")
        return False
    
    try:
        import requests
        
        url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}"
        params = {"key": api_key}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        blog_name = data.get('name', 'Unknown')
        blog_url = data.get('url', 'Unknown')
        
        print(f"✅ Blogger connected")
        print(f"   Blog: {blog_name}")
        print(f"   URL: {blog_url}")
        return True
        
    except Exception as e:
        print(f"❌ Blogger error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Status: {e.response.status_code}")
            print(f"   Response: {e.response.text[:200]}")
        return False


def test_files():
    """Test required files exist"""
    print("\n🧪 Testing required files...")
    
    files = {
        'topics.txt': 'Topics file',
        'status.json': 'Status tracker',
        'requirements.txt': 'Dependencies',
        '.gitignore': 'Git ignore',
    }
    
    all_exist = True
    for file, desc in files.items():
        if os.path.exists(file):
            print(f"✅ {desc}: {file}")
        else:
            print(f"❌ Missing: {file}")
            all_exist = False
    
    return all_exist


def test_topics():
    """Test topics.txt format"""
    print("\n🧪 Testing topics.txt format...")
    
    try:
        with open('topics.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        
        blocks = content.strip().split('\n\n')
        valid_topics = 0
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 2 and lines[0].startswith('Day'):
                valid_topics += 1
        
        if valid_topics > 0:
            print(f"✅ Found {valid_topics} valid topics")
            return True
        else:
            print("❌ No valid topics found")
            return False
            
    except Exception as e:
        print(f"❌ Error reading topics: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("🔍 Blog Automation - Configuration Test")
    print("=" * 60)
    
    results = {
        'Files': test_files(),
        'Topics': test_topics(),
        'Gemini AI': test_gemini_api(),
        'Unsplash': test_unsplash_api(),
        'Blogger': test_blogger_api(),
    }
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}  {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! Ready to run automation.")
        print("\nNext step: python automate_blogger.py")
    else:
        print("⚠️  Some tests failed. Fix issues before running.")
        print("\nCheck:")
        print("1. .env file with all API keys")
        print("2. Blogger API enabled in Google Cloud Console")
        print("3. Correct Blog ID from Blogger dashboard")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
