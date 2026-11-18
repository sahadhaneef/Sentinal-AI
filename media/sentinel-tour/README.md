# SENTINEL AI product video

The landing-page video is generated from thirteen actual frontend screenshots and local Windows narration. No backend or external voice service is used.

- `scenes.json`: narration, route and scene source.
- `capture.mjs`: capture frontend pages from the local Vite server at port 5190.
- `build.mjs`: create scene HTML, measure WAV timing, generate chapters and captions.
- `narrate.ps1`: Microsoft Zira narration at rate 2.
- `index.html` and `compositions/`: editable HyperFrames project.
- `publish.mjs`: copy rendered MP4, poster, captions and chapter data into the frontend.

Requirements: Node, the project's Playwright Chromium, Windows System.Speech and Segoe UI fonts, GSAP, HyperFrames 0.9.63, project-local FFmpeg/FFprobe. Set `HYPERFRAMES_FFMPEG_PATH` and `HYPERFRAMES_FFPROBE_PATH` to the installed encoders when checking/rendering. Use the installed HyperFrames CLI launcher for check, snapshot, preview and render. The public player never auto-plays and retains a transcript and interactive-demo link if media is unavailable.

See DESIGN.md, SCRIPT.md, STORYBOARD.md, SPEC.md and REVIEW.md for the content and verification boundaries.
