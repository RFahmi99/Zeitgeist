# ⚙️ Configuration Guide

This guide explains every key setting in `config.py`, how to override values with environment variables, and best-practice configuration patterns.

---

## 1. Environment File (`.env`)

The project relies on [python-dotenv](https://pypi.org/project/python-dotenv/) to load environment variables from a local `.env` file. Copy the example template:

```bash
cp .env.example .env
```

Then edit the values to match your environment. **Never commit `.env` files to version control.**

---

## 2. Configuration Hierarchy

1. **Hard-coded defaults** in the `dataclass` definitions
2. **Environment variables** (override defaults)
3. **Runtime overrides** via CLI flags (future feature)

---

## 3. DatabaseConfig

| Variable | Env Var | Default | Description |
|----------|---------|---------|-------------|
| `db_type` | `DB_TYPE` | `sqlite` | `sqlite` or `postgres` |
| `db_path` | `DB_PATH` | `blog_system.db` | SQLite file path |
| `backup_enabled` | `DB_BACKUP_ENABLED` | `true` | Enable automatic backups |
| `backup_interval_hours` | `DB_BACKUP_INTERVAL` | `24` | Hours between backups |

### Postgres Example

```bash
export DB_TYPE=postgres
export DATABASE_URL=postgresql://user:pass@localhost:5432/blogdb
```

---

## 4. ScrapingConfig

| Env Var | Default | Meaning |
|---------|---------|---------|
| `SCRAPING_MAX_RETRIES` | `3` | Retry attempts per URL |
| `SCRAPING_TIMEOUT` | `30` | HTTP timeout (s) |
| `SCRAPING_WAIT_TIME` | `3` | Delay between requests (s) |
| `MAX_SOURCES_PER_TOPIC` | `5` | Concurrency limit |

### Tips

- If you hit **429** rate-limit errors, increase `SCRAPING_WAIT_TIME` or decrease `MAX_SOURCES_PER_TOPIC`.
- Set `USER_AGENT_ROTATION=false` for deterministic testing.

---

## 5. AIConfig

| Env Var | Default | Description |
|---------|---------|-------------|
| `AI_MODEL` | `mistral` | Ollama model name |
| `AI_MAX_TOKENS` | `4000` | Max response tokens |
| `AI_TEMPERATURE` | `0.7` | Creativity level (0-1) |
| `AI_TIMEOUT` | `300` | Generation timeout (s) |
| `AI_MAX_RETRIES` | `3` | Generation retries |
| `MIN_CONTENT_LENGTH` | `500` | Minimum words in post |

---

## 6. SchedulingConfig

| Env Var | Default | Description |
|---------|---------|-------------|
| `SCHEDULING_ENABLED` | `true` | Enable APScheduler |
| `SCHEDULING_INTERVAL` | `6` | Hours between cycles |
| `MAX_POSTS_PER_DAY` | `8` | Safety cap |
| `BUSINESS_HOURS_ONLY` | `false` | Restrict to business hours |
| `TIMEZONE` | `UTC` | Scheduler timezone |

---

## 7. PublishingConfig

| Env Var | Default | Description |
|---------|---------|-------------|
| `PUBLISHING_PLATFORMS` | `html,notion` | Comma-separated list |
| `AUTO_PUBLISH` | `true` | Immediate publish after generation |
| `REQUIRE_APPROVAL` | `false` | Manual vetting |
| `SEO_OPTIMIZATION` | `true` | Enable automatic meta tags |

---

## 8. Monitoring/Logging

| Env Var | Default | Description |
|---------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Root logging level |
| `LOG_FILE` | `blog_system.log` | Log file path |
| `JSON_LOGGING` | `false` | JSON vs text |
| `METRICS_ENABLED` | `true` | Enable in-memory metrics |

---

## 9. Email & Webhook Alerts

Set these variables if you want email or Discord/Slack alerting:

```bash
EMAIL_ENABLED=true
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_USERNAME=bot@example.com
EMAIL_PASSWORD=yourpassword
EMAIL_FROM_ADDRESS=bot@example.com
EMAIL_TO_ADDRESS=admin@example.com

WEBHOOK_ENABLED=true
WEBHOOK_URL=https://discord.com/api/webhooks/.../...
```

---

## 10. Security Tips

- **SECRET_KEY** – Always set a strong random `SECRET_KEY` in production.
- Use **HTTPS** in production (enabled by default via Flask-Talisman).
- Rotate API keys (Reddit, NewsAPI, Notion) regularly.

---

## 11. Configuration Debugging

```bash
python - << 'PY'
from config import config
import pprint
pprint.pprint(config.get_summary())
PY
```

This prints a sanitized summary of active settings.

---

*For advanced tuning (e.g. AI prompt templates, scheduler cron triggers), see inline docs in the corresponding modules.*