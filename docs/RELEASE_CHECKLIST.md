# Release checklist — v1.0 / dashboard v12.4

## Included in package

- [x] Seven Python scripts (six core + optional standalone prototype)
- [x] Dashboard v12.4 static HTML snapshot (`site/index.html`)
- [x] Updated Python dependencies including Shapely
- [x] Updated Windows launch/rebuild scripts
- [x] README, architecture, methodology, data quality, runbook, deployment, dashboard guide, changelog
- [x] Dockerfile for optional static hosting
- [x] `.gitignore` excluding raw and generated CSVs

## Must verify before public announcement

- [ ] Full clean rebuild from the four original source CSVs
- [ ] Compare rebuilt HTML metrics and QA outputs against the accepted local release
- [ ] Confirm new `v12_4_geocoding_quality.json` filename and other output naming
- [ ] Test all dashboard controls in Chrome and Edge, including year restrictions and highlights
- [ ] Test site load time and mobile/narrow-screen behavior
- [ ] Confirm City of Vancouver / ICBC attribution, source links and redistribution rights
- [ ] Add dashboard screenshots and pipeline infographic to `assets/`
- [ ] Validate GitHub Pages deployment and public URL
- [ ] Review academic group attribution and individual-extension descriptions

No unchecked item should be described as completed.
