# GreenPulse — Environmental Action Challenge

A runnable Flask + SQLite hackathon prototype for campus communities. Users register, browse eco-missions, submit environmental actions for review with optional photo evidence, and earn points after an administrator approves the submission.

## Quick Start

### On Linux / macOS
```bash
./start.sh
# Or directly with python:
python3 app.py
```
Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

### On Windows
Double-click `start.bat` or run:
```cmd
start.bat
```
Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## Demo Accounts

### Administrator Account
- **Email:** `admin@greenpulse.local`
- **Password:** `GreenPulse2026!`

Log in as the administrator to access the **Admin Panel**:
- Review and approve/reject pending submissions.
- **Add new eco-missions** with custom title, category, points, and emoji.
- Edit or manage existing missions.
- Monitor verified impact metrics and review history.

### Participant / Member Account
- Register a new account via the **Join GreenPulse** button (e.g. `jane@example.com` / `password123`).
- Browse available missions and submit actions with details and optional photo evidence.
- Track verified submissions and points on **My actions**.
- Compete on the **Leaderboard** as actions are verified!

---

## Features

- **Mission Creation & Management:** Administrators can create new challenges anytime (specifying title, category, points, and emojis) and manage active missions.
- **Review & Verification Workflow:** Submissions require administrator review before points are awarded, ensuring genuine impact.
- **Dynamic Community Impact Stats:** Verified kg of waste collected, tree care actions, total actions, and active community members.
- **Live Leaderboard:** Points and rankings update automatically when submissions are approved.
- **Photo Evidence:** File uploads (JPG, PNG, WEBP up to 4 MB) stored securely for admin verification.
- **Responsive UI:** Clean, modern, accessible design for both desktop and mobile screens.
