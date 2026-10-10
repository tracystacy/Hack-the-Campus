# GreenPulse — Environmental Action Challenge

A runnable Flask + SQLite hackathon prototype. Users register, browse missions, submit environmental actions for review, and earn points only after an administrator approves a submission.

## Fastest Windows start
1. Extract this ZIP to a folder such as `Downloads\GreenPulse`.
2. Double-click `start.bat`.
3. Wait for dependencies to install and Flask to start.
4. Open http://127.0.0.1:5000 in your browser.

If double-clicking does not work, open Command Prompt in this folder and run `start.bat`.

## Demo administrator (local demo only)
- Email: `admin@greenpulse.local`
- Password: `GreenPulse2026!`

Log in using the account icon / Log in link, then open **Admin review**. Register a separate normal account to submit a test action. Approve it in the admin page; then check the dashboard and leaderboard.

## Main features
- Responsive landing page and mission cards
- User registration/login with password hashing
- SQLite persistence
- Environmental action submissions with optional JPG/PNG/WEBP evidence
- Admin approval/rejection queue
- Points and leaderboard based only on approved submissions
- Dashboard totals calculated from approved submissions

## Important demo notes
- The app creates `greenpulse.db` automatically on first run.
- All impact totals start at zero; use test submissions to demonstrate updates. Do not describe demo data as real-world impact.
- The default admin credentials are for a local demo only. Change them and configure a strong secret before any public deployment.
- Photo upload is limited to 4 MB and common image extensions. This is a hackathon prototype, not a production security review.
- To stop the server, focus the terminal window and press `Ctrl+C`.
