# GestureHome — IoT presentation (Reveal.js)

QAHE-branded slides for the 5-minute GestureHome / home-security IoT talk.

**Live:** https://goodluckoguzie.github.io/GestureHome/

Same Reveal.js style as the [PhD Viva deck](https://goodluckoguzie.github.io/Viva/).

## Open locally

```bash
cd talk
python3 -m http.server 8765
```

Then open **http://127.0.0.1:8765/**

## Present

| Key | Action |
|-----|--------|
| → / space | Next slide |
| ← | Back |
| ↓ | Stack slide (under Architecture) / keyboard backup (under Live Demo) |
| **S** | Speaker notes |
| F | Fullscreen |

## Deploy

Pushes to `main` that change `talk/` trigger GitHub Pages via `.github/workflows/deploy-talk.yml`.

Site URL: **https://goodluckoguzie.github.io/GestureHome/**
