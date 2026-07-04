# TurntUpToddler v5.39.0 Release Notes

### Highlights
- **Dashboard Consolidation:** Replaced the fragmented multi-page Next.js structure (`/editor`, `/radio`) with a single-page interactive dashboard. Users can now seamlessly tab between the Generator Pipeline, Generation History, Radio Broadcast, and Dev Tools without full page reloads.
- **Interactive Review UX:** The `InteractiveReviewModal` has been completely redesigned with a polished Tailwind interface, featuring backdrop blurs, clear tooltips, and loading states to prevent duplicate API submissions. Keyboard shortcuts (like `Ctrl+Enter` to approve) have been added for a power-user friendly workflow.
- **Backend-UI Integration Validations:** Added Playwright E2E suites to rigorously validate the Kids Mode automated BitMidi scraping pipeline, ensuring it correctly suspends operations to await the frontend's Interactive Review payload (`job_id` correctly preserved).

### Upgrade Instructions
- No database migrations required for `history.db`.
- Docker orchestrations will automatically pull the updated Next.js build. Ensure you hard refresh your browser cache to load the new React SPA payload.
