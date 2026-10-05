# NBA Head-to-Head Calendar

Lightweight Python script plus GitHub Actions pipeline that fetches the NBA schedule from ESPN, keeps only games where **both** teams are in a fixed contender list, writes `nba_head_to_head.ics`, and publishes it on GitHub Pages for iOS Calendar.

Target teams (both home and away must be on this list):

- Oklahoma City Thunder
- San Antonio Spurs
- New York Knicks
- Philadelphia 76ers
- Boston Celtics
- Miami Heat
- Denver Nuggets
- Minnesota Timberwolves
- Toronto Raptors

## Local run

```bash
cd nba-h2h-calendar
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python generate_calendar.py
```

This writes `nba_head_to_head.ics` in the repo root. A full-season fetch hits ESPN once per day from October through May and can take several minutes.

## Initialize git, push to GitHub, enable Pages

From the project directory (git is already initialized if you cloned or used this repo):

```bash
cd nba-h2h-calendar
git add generate_calendar.py requirements.txt README.md .gitignore .github/workflows/update_calendar.yml
git commit -m "Add NBA head-to-head calendar generator and GitHub Pages workflow"
gh repo create nba-h2h-calendar --public --source=. --remote=origin --push
```

If `gh` is not logged in, run `gh auth login` first. To push without `gh`:

```bash
git remote add origin git@github.com:<YOUR_GITHUB_USERNAME>/nba-h2h-calendar.git
git branch -M main
git push -u origin main
```

Enable GitHub Pages:

1. Open the repository on GitHub → **Settings** → **Pages**.
2. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
3. Set the branch to **`gh-pages`** and the folder to **`/ (root)`**, then save.

The `gh-pages` branch is created by the workflow. If it is not listed yet:

1. Open **Actions** → **Update NBA Calendar** → **Run workflow**.
2. After it succeeds, return to **Settings** → **Pages** and select `gh-pages`.

Scheduled runs use cron `0 6 * * *` (06:00 UTC daily). New repositories often need one successful manual `workflow_dispatch` before the schedule starts.

## iOS Calendar (`webcal://`) link

After Pages is live, subscribe with:

```text
webcal://<YOUR_GITHUB_USERNAME>.github.io/nba-h2h-calendar/nba_head_to_head.ics
```

HTTPS equivalent (Safari / Calendar on iPhone):

```text
https://<YOUR_GITHUB_USERNAME>.github.io/nba-h2h-calendar/nba_head_to_head.ics
```

On iPhone: open the `webcal://` URL, or in **Calendar** → **Calendars** → **Add Calendar** → **Add Subscription Calendar** and paste the HTTPS URL.
