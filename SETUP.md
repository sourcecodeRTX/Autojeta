# 🚀 Quick Setup Guide

## ✅ What's Been Optimized

### Script Improvements:
- ✅ **Retry logic** for Gemini AI, Unsplash, and Blogger API (handles network issues)
- ✅ **Auto-restart** from Day 1 when topics finish
- ✅ **Better error handling** with detailed messages
- ✅ **Validation** for empty topics and invalid data
- ✅ **Fallback queries** for image search
- ✅ **Alt text** for images (SEO)
- ✅ **Post ID tracking** in logs

### Workflow:
- ⏰ **Schedule:** 6:00 AM IST daily (0:30 AM UTC)
- 🔄 **Auto-retry** on failures
- 📝 **Auto-commit** status updates

---

## ⚡ Setup Steps

### 1. Get API Keys (5 minutes)

**Gemini AI:** https://aistudio.google.com/app/apikey
**Unsplash:** https://unsplash.com/developers
**Blogger API:** https://console.cloud.google.com/
**Blog ID:** From Blogger dashboard URL

### 2. GitHub Setup (3 minutes)

```powershell
# Initialize and push
git init
git add .
git commit -m "Crypto blog automation"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### 3. Add GitHub Secrets (2 minutes)

Go to: **Settings** → **Secrets and variables** → **Actions**

Add these 4 secrets:
- `GEMINI_API_KEY`
- `UNSPLASH_ACCESS_KEY`
- `BLOGGER_API_KEY`
- `BLOG_ID`

### 4. Enable Workflow Permissions (1 minute)

Go to: **Settings** → **Actions** → **General** → **Workflow permissions**

Select: **"Read and write permissions"** → **Save**

### 5. Test Run

Go to: **Actions** → **Automate Crypto Blog Posts** → **Run workflow**

---

## 🛡️ Error Scenarios Handled

| Scenario | Solution |
|----------|----------|
| Gemini API timeout | 3 retries with 5s delay |
| Unsplash no results | Fallback to "cryptocurrency blockchain" |
| Blogger API 500 error | 3 retries with 10s delay |
| Network failure | Automatic retry with exponential backoff |
| Topics exhausted | Auto-restart from Day 1 |
| Empty/invalid topic | Skip and log warning |
| Image download fail | Continue without image |
| Short content (<100 chars) | Regenerate with retry |
| Client errors (4xx) | No retry, detailed error log |

---

## 📊 Workflow Status

**Manual trigger:** Actions tab → Run workflow
**View logs:** Click on any workflow run
**Check status:** View status.json in repo

---

## 🎯 What Happens Daily

1. ✅ Workflow triggers at 6:00 AM IST
2. ✅ Loads next topic from topics.txt
3. ✅ Generates 800-1200 word article (Gemini AI)
4. ✅ Fetches relevant image (Unsplash)
5. ✅ Converts Markdown → HTML
6. ✅ Publishes to Blogger with labels
7. ✅ Updates status.json
8. ✅ Commits changes to GitHub
9. ✅ Repeats tomorrow

---

## 💡 Pro Tips

- **Test first:** Use manual trigger before relying on schedule
- **Monitor logs:** Check Actions tab for any errors
- **Rate limits:** All free tiers support daily usage
- **Customize schedule:** Edit `.github/workflows/automate-blog.yml`
- **Add topics:** Just append to topics.txt (any Day number)

---

## 🆘 Troubleshooting

**Workflow not running?**
→ Check Settings → Actions → General → Read/write permissions enabled

**API errors?**
→ Verify all 4 secrets are set correctly (no extra spaces)

**No image in post?**
→ Check Unsplash key, script continues without images

**Post not appearing?**
→ Check Blogger API enabled in Google Cloud Console

---

**Total setup time:** ~10 minutes
**Monthly cost:** $0.00 (all free tier)
**Maintenance:** Zero

✅ You're ready to go!
