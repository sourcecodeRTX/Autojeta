# Crypto Basic Guide - Blog Automation

Automated cryptocurrency blog publishing system for Blogger using Google Gemini AI and Unsplash API.

## 🚀 Features

- **AI-Powered Content Generation**: Uses Google Gemini AI to create high-quality, SEO-optimized blog posts
- **Automatic Image Integration**: Fetches relevant images from Unsplash with proper attribution
- **Direct Blogger Publishing**: Posts directly to your Blogger blog via API v3
- **Progress Tracking**: Maintains automation state across runs
- **31-Day Content Calendar**: Pre-planned topics covering all aspects of cryptocurrency
- **Monthly Market Updates**: Includes monthly crypto market analysis topics
- **Image Optimization**: Automatic compression and sizing for web
- **Error Handling**: Robust error handling and logging

## 📋 Prerequisites

Before you begin, you'll need:

1. **Python 3.8+** installed on your system
2. **A Blogger blog** (create one at [blogger.com](https://www.blogger.com))
3. **API Keys** (all free):
   - Google Gemini API key
   - Unsplash API access key
   - Blogger API key
   - Your Blog ID

## 🔧 Installation

### Step 1: Clone or Download This Repository

```powershell
cd c:\Users\Ns8pc\Music\Blog_Automater
```

### Step 2: Install Python Dependencies

```powershell
pip install -r requirements.txt
```

This installs:
- `google-genai` - Google Gemini AI SDK
- `Pillow` - Image processing
- `requests` - HTTP requests
- `python-dotenv` - Environment variable management

### Step 3: Set Up Environment Variables

1. Copy `.env.example` to `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```

2. Edit `.env` and add your API keys:
   ```
   GEMINI_API_KEY=your_actual_gemini_key
   UNSPLASH_ACCESS_KEY=your_actual_unsplash_key
   BLOGGER_API_KEY=your_actual_blogger_key
   BLOG_ID=your_actual_blog_id
   ```

### Step 4: Get Your API Keys

#### 🤖 Google Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key and paste it in your `.env` file
5. **Free tier**: 60 requests per minute

#### 📸 Unsplash API Access Key

1. Go to [Unsplash Developers](https://unsplash.com/developers)
2. Click "Register as a developer"
3. Create a new application
4. Copy the "Access Key" (not Secret Key)
5. Paste it in your `.env` file
6. **Free tier**: 50 requests per hour

#### 📝 Blogger API Key & Blog ID

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable "Blogger API v3":
   - Go to "APIs & Services" > "Library"
   - Search for "Blogger API v3"
   - Click "Enable"
4. Create API credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "API Key"
   - Copy the API key
5. Get your Blog ID:
   - Go to your [Blogger Dashboard](https://www.blogger.com/)
   - Click on your blog
   - Look at the URL: `blogger.com/blog/posts/YOUR_BLOG_ID`
   - Copy the numeric Blog ID
6. Paste both in your `.env` file

## 🎯 Usage

### Test Your Setup First

Before running automation, test your configuration:

```powershell
python test_setup.py
```

This validates:
- ✅ All API keys are set correctly
- ✅ Blogger API is accessible
- ✅ Gemini AI is working
- ✅ Unsplash is connected (optional)
- ✅ Topics file is valid

### Run the Automation

To publish the next blog post in the queue:

```powershell
python automate_blogger.py
```

The script will:
1. Load the next topic from `topics.txt`
2. Generate content using Gemini AI (800-1200 words)
3. Fetch a relevant image from Unsplash
4. Optimize and compress the image
5. Convert content to HTML
6. Publish to your Blogger blog
7. Update `status.json` with progress

### What Gets Created

- **Blog Post Title**: "Day X: [Topic Name]"
- **Content**: SEO-optimized article with headings, lists, and formatting
- **Featured Image**: Relevant cryptocurrency image with attribution
- **Labels/Tags**: Category + "Cryptocurrency" + "Blockchain"
- **Published**: Immediately live on your blog

### Schedule Automation

#### Option 1: GitHub Actions (Recommended) ⭐

**Fully automated, runs in the cloud, no local setup needed!**

**Schedule:** Daily at 6:00 AM IST (12:30 AM UTC)

1. **Push your code to GitHub:**
   ```powershell
   git init
   git add .
   git commit -m "Initial commit - Crypto blog automation"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```

2. **Set up GitHub Secrets:**
   - Go to your repository on GitHub
   - Click **Settings** → **Secrets and variables** → **Actions**
   - Click **New repository secret** and add:
     - `GEMINI_API_KEY` → Your Gemini API key
     - `UNSPLASH_ACCESS_KEY` → Your Unsplash access key
     - `BLOGGER_API_KEY` → Your Blogger API key
     - `BLOG_ID` → Your Blog ID

3. **Enable GitHub Actions:**
   - Go to **Actions** tab → **General** → **Workflow permissions**
   - Select **"Read and write permissions"** → Save
   - Go to **Actions** tab
   - Enable workflows if prompted
   - The workflow will run daily at 6:00 AM IST automatically

4. **Manual trigger (optional):**
   - Go to **Actions** tab → **Automate Crypto Blog Posts**
   - Click **Run workflow** → **Run workflow**
   - Perfect for testing!

**Benefits:**
- ✅ Runs automatically in the cloud (no PC needed)
- ✅ Free for public repos (2,000 min/month for private)
- ✅ Auto-commits status.json updates
- ✅ Full error logging and retry logic
- ✅ Manual trigger available

#### Option 2: Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., daily at 9 AM)
4. Action: Start a program
5. Program: `python`
6. Arguments: `c:\Users\Ns8pc\Music\Blog_Automater\automate_blogger.py`
7. Start in: `c:\Users\Ns8pc\Music\Blog_Automater`

#### Option 3: Manual Daily Run

Just run the script once per day manually:
```powershell
python automate_blogger.py
```

## 📁 File Structure

```
Blog_Automater/
├── .github/
│   └── workflows/
│       └── automate-blog.yml  # GitHub Actions workflow (6 AM IST)
├── automate_blogger.py    # Main automation script
├── topics.txt             # 31-day content calendar
├── status.json            # Progress tracker
├── requirements.txt       # Python dependencies
├── .env                   # Your API keys (keep secret!)
├── .env.example           # Template for .env
├── .gitignore            # Git ignore rules
├── README.md             # This file
└── images/               # Downloaded images (auto-created)
```

## 📅 Content Calendar

The `topics.txt` file includes 31 days of content covering:

### Week 1: Fundamentals
- Bitcoin basics
- Top cryptocurrencies
- Buying guide
- Blockchain technology
- Wallet security
- DeFi introduction
- NFTs beyond art

### Week 2: Trading & Security
- Trading strategies
- Scam detection
- Ethereum 2.0
- Crypto taxes
- Layer 2 solutions
- Stablecoins
- Mining profitability

### Week 3: Advanced Topics
- Airdrops
- Monthly market analysis (January)
- CBDCs impact
- Cross-chain bridges
- DAO governance
- Security tools

### Week 4: Passive Income & Monthly Updates
- February outlook
- Yield farming
- Altcoin research
- Crypto payments
- Privacy coins

### Week 5: Tokenization & Regulation
- March calendar
- Asset tokenization
- Crypto lending
- Play-to-earn gaming
- Global regulation
- April preview

## 🔍 Monitoring Progress

Check `status.json` to see:
- **next_day**: Which day will be published next
- **last_processed**: Last topic published
- **last_published**: Timestamp of last publication

Example:
```json
{
  "next_day": 5,
  "last_processed": "Crypto Wallets Explained: Hot vs Cold Storage",
  "last_published": "2026-01-10T14:30:00"
}
```

## 🛠️ Troubleshooting

### Error: "GEMINI_API_KEY environment variable not set"
- Make sure you created `.env` file (not `.env.example`)
- Verify your API key is correctly pasted
- Restart terminal after editing `.env`

### Error: "BLOG_ID environment variable not set"
- Get your Blog ID from Blogger dashboard URL
- It's the numeric ID after `/posts/` in the URL

### Error: "Failed to publish to Blogger"
- Check your Blogger API key is correct
- Verify Blogger API v3 is enabled in Google Cloud Console
- Ensure your blog exists and is accessible

### Error: "No images found on Unsplash"
- Check your Unsplash access key
- You may have hit the free tier limit (50/hour)
- The script will continue without images

### Image Not Appearing in Blog Post
- Blogger may take a few seconds to process images
- Check the post in Blogger dashboard
- Image attribution will still be included

## 📊 API Rate Limits & Costs

| Service | Free Tier Limit | Cost |
|---------|-----------------|------|
| Google Gemini AI | 60 requests/min | FREE |
| Unsplash API | 50 requests/hour | FREE |
| Blogger API | Unlimited | FREE |

**Total Monthly Cost**: $0.00

Running once per day is well within all free tier limits.

## 🔒 Security Best Practices

1. **Never commit `.env` file** - It contains your API keys
2. **Use `.gitignore`** - Already configured to exclude `.env`
3. **Keep API keys private** - Don't share screenshots with keys visible
4. **Regenerate compromised keys** - If leaked, regenerate immediately
5. **Use environment variables** - Never hardcode keys in scripts

## 📝 Customization

### Add More Topics

Edit `topics.txt` following this format:
```
Day 32
Topic: Your New Topic Title
Additional Details: Context and requirements for content generation
```

### Change Content Length

Edit the prompt in `generate_blog_content()`:
```python
# Change from (800-1200 words) to your desired length
1. Write an engaging, informative article (1500-2000 words)
```

### Modify Categories

Edit the `CATEGORIES` list in `automate_blogger.py`:
```python
CATEGORIES = [
    'Your Category 1',
    'Your Category 2',
    # Add more categories
]
```

### Adjust Image Size

Edit the `compress_image()` function:
```python
max_size_kb=300  # Change target file size
max_dimension = 1200  # Change max width/height
```

## 🤝 Support

### Need Help?

1. Check the troubleshooting section above
2. Review the `automate_blogger.py` script comments
3. Verify all API keys are correctly set
4. Test each API independently (see test scripts below)

### Test Individual APIs

Create test scripts to verify each API:

**Test Gemini AI**:
```python
from google import genai
import os

client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))
response = client.models.generate_content(
    model='gemini-2.0-flash-exp',
    contents='Write a short paragraph about Bitcoin'
)
print(response.text)
```

**Test Unsplash**:
```python
import requests
import os

headers = {"Authorization": f"Client-ID {os.environ.get('UNSPLASH_ACCESS_KEY')}"}
response = requests.get(
    "https://api.unsplash.com/search/photos",
    headers=headers,
    params={"query": "bitcoin", "per_page": 1}
)
print(response.json())
```

**Test Blogger API**:
```python
import requests
import os

blog_id = os.environ.get('BLOG_ID')
api_key = os.environ.get('BLOGGER_API_KEY')
url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts"
response = requests.get(url, params={"key": api_key, "maxResults": 1})
print(response.json())
```

## 📜 License

This project is provided as-is for educational and personal use. Make sure to comply with:
- Blogger Terms of Service
- Google AI Terms of Service
- Unsplash API Terms (attribution required)

## 🎉 Success!

Once everything is set up, your blog automation will:
- ✅ Generate high-quality crypto content daily
- ✅ Include relevant professional images
- ✅ Publish automatically to Blogger
- ✅ Build your blog with minimal effort
- ✅ Track progress automatically

**Your blog**: [Crypto Basic Guide](https://cryptobasicguide.blogspot.com)

Happy automating! 🚀
