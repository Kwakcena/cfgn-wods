# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CrossFit Gangnam Unju WOD tracker - displays daily workout data crawled from Instagram. Built with React + Vite + Tailwind CSS, deployed on Vercel.

## Commands

### Frontend (wod-tracker/)

```bash
cd wod-tracker
npm run dev          # Start dev server (localhost:5173)
npm run dev -- --host  # Expose on network for mobile testing
npm run build        # TypeScript check + Vite build
npm run lint         # ESLint
npm run preview      # Preview production build
```

### Crawler (wod-tracker/scripts/)

```bash
cd wod-tracker
source scripts/venv/bin/activate  # or .venv/bin/activate
pip install -r scripts/requirements.txt

# Primary crawler (web scraper with Playwright)
python scripts/crawl_web.py --stop-on-existing

# Fallback crawler (instaloader)
python scripts/crawl_instagram.py --stop-on-existing
```

## Architecture

```
cfgn/
├── vercel.json              # Vercel deployment config
├── .github/workflows/
│   └── crawl-wod.yml        # Daily WOD crawl (KST 21:00-01:45)
└── wod-tracker/
    ├── src/
    │   ├── components/      # React components
    │   │   ├── Dashboard.tsx  # Main layout with search
    │   │   ├── WodList.tsx    # Virtualized list (@tanstack/react-virtual)
    │   │   └── WodCard.tsx    # Individual workout card
    │   └── data/
    │       └── wods.json    # WOD data {"YYYY-MM-DD": "workout content"}
    └── scripts/
        ├── crawl_web.py     # Primary: Playwright-based scraper
        └── crawl_instagram.py # Fallback: instaloader-based
```

## Data Flow

1. GitHub Actions runs crawler daily (crawl-wod.yml)
2. crawl_web.py fetches new WODs from Instagram, updates wods.json
3. On failure, falls back to crawl_instagram.py
4. Changes committed automatically, triggers Vercel deploy
5. Frontend reads wods.json statically at build time

## Key Implementation Details

- WodList uses @tanstack/react-virtual for performance with large lists
- Search is debounced (300ms) in Dashboard.tsx
- WOD dates are KST (Korean Standard Time) - crawler posts today for tomorrow's WOD
- Crawler requires INSTAGRAM_SESSION, INSTAGRAM_USER, INSTAGRAM_PASS secrets
