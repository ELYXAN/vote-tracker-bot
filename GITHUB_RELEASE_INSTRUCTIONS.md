# GitHub Release Instructions

## Step 1: Add Your GitHub Remote

Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your actual GitHub username and repository name:

```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
```

Or if you prefer SSH:
```bash
git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO_NAME.git
```

## Step 2: Push to GitHub

```bash
# Push main branch
git branch -M main
git push -u origin main

# Push tags (for releases)
git push origin v3.1
```

## Step 3: Create GitHub Release

1. Go to your GitHub repository
2. Click on "Releases" → "Create a new release"
3. Tag: Select `v3.1` from the dropdown (or type `v3.1`)
4. Release title: `Version 3.1 - Performance Optimized`
5. Description: Copy the contents from `RELEASE_NOTES_v3.1.md`
6. Click "Publish release"

## Alternative: Use GitHub CLI

If you have GitHub CLI installed:

```bash
gh release create v3.1 \
  --title "Version 3.1 - Performance Optimized" \
  --notes-file RELEASE_NOTES_v3.1.md
```

## What's Included in This Release

- ✅ Complete codebase with all optimizations
- ✅ New README.md in English
- ✅ Helper scripts (create_rewards.py, get_reward_ids.py)
- ✅ Colorful terminal output
- ✅ Performance improvements (3-4x faster)
- ✅ Silent background sync
- ✅ Improved authentication module

## Files NOT Included (Protected by .gitignore)

- `secrets.json` - Sensitive credentials
- `Vote tracking.json` - Google Service Account credentials
- `votes.db` - Database file
- `venv/` - Virtual environment
- `__pycache__/` - Python cache files

