# DirectJobPing

DirectJobPing is a personal, direct-source job tracker. You add official company career pages or ATS job boards, the app checks them politely on a schedule, stores newly detected roles in SQLite, and sends one email alert for each new job that matches your filters.

The key timestamp is `first_seen_at`: the first time your own checker saw the job on the public company career site. DirectJobPing does not need the employer's internal posting timestamp.

## Why Direct Source Tracking

LinkedIn, GitHub internship lists, and job aggregators can lag behind official company boards. DirectJobPing watches the public source itself, so a role can be detected as soon as your scheduled worker fetches the company's careers page or ATS board.

This project does not scrape LinkedIn, does not use paid proxies, does not use paid APIs, and does not try to bypass CAPTCHAs or login walls.

## Tech Stack

- Python 3.11+
- FastAPI
- SQLite by default
- SQLAlchemy ORM
- APScheduler
- httpx, BeautifulSoup
- SMTP email
- Jinja2 templates for a simple UI
- Optional Playwright fallback for JavaScript-rendered pages

## Features

- Add companies with official career URLs
- Auto-detect Greenhouse, Lever, Ashby, Google Careers, or generic static source types
- Normalize jobs into one schema
- Dedupe by external ID, URL, or stable fingerprint
- Preserve `first_seen_at` across repeated checks
- Track `last_seen_at`, active/inactive state, matched keywords, raw data, and content hash
- Send one email alert per matched new job
- Record check runs and adapter/email failures
- Run manual checks from the UI or API
- Run scheduled checks for enabled companies

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` before enabling email alerts:

```text
DATABASE_URL=sqlite:///./direct_job_ping.db
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=your_email@gmail.com
ALERT_TO_EMAIL=your_email@gmail.com
DEFAULT_CHECK_INTERVAL_MINUTES=120
ALERT_ON_ALL_JOBS=false
ALLOW_GENERIC_ALERTS=false
APP_ENV=development
```

For Gmail, use an app password rather than your normal account password.

## Run Locally

```bash
uvicorn app.main:app --reload
```

Open:

- Dashboard: http://127.0.0.1:8000/
- Companies: http://127.0.0.1:8000/ui/companies
- Jobs: http://127.0.0.1:8000/ui/jobs
- Settings: http://127.0.0.1:8000/ui/settings
- API docs: http://127.0.0.1:8000/docs

The app creates SQLite tables on startup and seeds editable disabled examples for 100+ big tech, AI, infra, SaaS, fintech, trading, gaming, hardware, and consumer tech companies.

## Add Companies

Use the Companies page to add:

- Company name
- Career URL or ATS URL
- Source type, usually `auto`
- Include keywords
- Exclude keywords
- Locations
- Check interval
- Enabled state
- Notes

Supported source types:

- `greenhouse`
- `lever`
- `ashby`
- `google_careers`
- `workday`
- `generic_static`
- `generic_playwright`
- `unknown`

## Filters

Default include keywords target SWE internships and early-career roles:

```text
software engineer intern
software engineering intern
swe intern
backend intern
machine learning intern
data engineering intern
new grad software engineer
university grad
early career
entry level software engineer
```

Default exclude keywords:

```text
senior
staff
principal
manager
director
lead
mechanical
electrical
hardware
sales
marketing
recruiter
```

A job matches when title or description contains an include keyword, contains no exclude keyword, and matches a configured location when location filters are present.

For a temporary smoke test, set `ALERT_ON_ALL_JOBS=true` in `.env`. That makes every newly detected job count as a match.

Email alerts are sent only for high-confidence job feeds by default: Greenhouse, Lever, Ashby, Google Careers, and Workday. Generic static scrapes are still stored for review, but they do not send email unless `ALLOW_GENERIC_ALERTS=true`.

## Manual Checks

From the UI, click `Check now` on a company.

From the API:

```bash
curl -X POST http://127.0.0.1:8000/companies/1/check-now
curl -X POST http://127.0.0.1:8000/checks/run-all
```

## Scheduler

The FastAPI app starts an APScheduler job that wakes every 5 minutes and checks enabled companies that are due based on each company's `check_interval_minutes`.

Good free personal-use intervals:

- Important companies: 30 minutes
- Normal companies: 2 hours
- Low-priority companies: 6 hours

Avoid extremely frequent checks. DirectJobPing is meant to fetch politely.

## Tests

```bash
python -m pytest
```

Tests cover keyword matching, exclude filtering, location filtering, deduping by external ID and URL, `first_seen_at` preservation, alert deduping, and adapter normalization with mocked responses. They do not require live scraping.

## API Routes

Companies:

- `GET /companies`
- `POST /companies`
- `GET /companies/{id}`
- `PUT /companies/{id}`
- `DELETE /companies/{id}`
- `POST /companies/{id}/check-now`

Jobs:

- `GET /jobs`
- `GET /jobs?company_id=`
- `GET /jobs?active=true`
- `GET /jobs?matched=true`
- `GET /jobs/{id}`

Checks:

- `POST /checks/run-all`
- `GET /checks/recent`
- `GET /checks/{id}`

Settings:

- `GET /settings`
- `PUT /settings`
- `POST /settings/test-email`

## Known Limitations

- Some career pages render heavily with JavaScript or change structure often.
- The Google Careers adapter is intentionally conservative and fails clearly if the public page does not expose parseable job links.
- `generic_static` favors fewer false positives over finding every possible listing.
- Runtime settings are read from `.env`; the settings UI displays config and can send a test email.
- Optional Playwright support requires installing the `playwright` extra and browser binaries.

## Future TODOs

- Daily digest emails
- SMS alerts
- Discord alerts
- Browser extension
- Public multi-user SaaS
- OAuth login
- More ATS adapters
- AI-based job relevance scoring
- Resume/job fit scoring
- Slack bot
- Deployment to free hosted services
- Browser automation for more complex career pages
- Export to CSV
- Apply status tracking
