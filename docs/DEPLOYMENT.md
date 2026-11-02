# Deployment guide

## Option 1 — GitHub Pages (recommended)

1. Create a GitHub repository and upload the **release files**, excluding raw/processed CSVs ignored by `.gitignore`.
2. GitHub Pages supports a folder named `/docs` on a branch, or a GitHub Actions deployment. This release keeps documentation in `docs/` and dashboard in `site/`; **do not select `/docs` as the Pages source**, since it contains Markdown, not the dashboard entrypoint.
3. For the simplest branch-based Pages setup, copy `site/index.html` to a dedicated `gh-pages` branch root (or configure a Pages Actions workflow that publishes `site/`).
4. In repository Settings → Pages, select the corresponding deployment source and publish. Confirm the live URL and test controls.
5. On future releases, regenerate the dashboard, QA it, replace `site/index.html`, then redeploy.

**This package does not automatically configure Pages or push to GitHub.** The published HTML is approximately 15 MB; check initial loading and interaction performance on real devices.

## Option 2 — Docker (optional)

`Dockerfile` defines a lightweight Nginx image containing only `site/index.html`. It is a reproducible way to serve the static page, **not** a Python data-processing environment.

```powershell
docker build -t vancouver-road-safety .
docker run --rm -p 8080:80 vancouver-road-safety
```

Open `http://localhost:8080`. Docker Desktop must be installed and running. Stop with Ctrl+C. External Leaflet CDN access is still required by the browser.

## Option 3 — Local Python HTTP server

```powershell
python -m http.server 8000 --directory site
```

Open `http://localhost:8000`.

## Security and rights

- Do not commit raw source exports or large derived CSVs until licensing and privacy are checked.
- Add publisher attribution and verified source links before public promotion.
- The site is static; no backend database or live data update is configured.
- Avoid calling the page fully offline: road geometries are embedded but JS/CSS are loaded from external CDNs.
