# 🗂️ Project Architecture & Module Guide

> **Document Version:** 1.0.0  |  **Last Updated:** 2025-07-06

This document provides a bird’s-eye view of the Autonomous AI Blog System codebase and a detailed description of every major file. Use this guide to quickly understand where functionality lives and how the parts fit together.

---

## 1. High-Level Layers

| Layer | Package / Path | Responsibility |
|-------|----------------|----------------|
| **Trend Detection** | `src/trends/` | Discover trending topics and relevant article URLs. |
| **Aggregation** | `src/aggregator/` | Fetch, parse and deduplicate external articles. |
| **Generation** | `src/generator/` | Produce blog posts with AI and validate quality. |
| **Publishing** | `src/publisher/` | Export content to HTML, Notion and other platforms. |
| **Scheduling** | `src/scheduler/` | Orchestrate automated workflows and maintenance jobs. |
| **Persistence & Metrics** | `src/database/`, `src/monitoring/` | Store content, track metrics, monitor health. |
| **Security & Utilities** | `security_enhancements.py`, `src/utils/` | Secure endpoints, logging, backups, helpers. |

---

## 2. File-by-File Reference

### 2.1 Aggregator

| File | Key Classes / Functions | Purpose |
|------|------------------------|---------|
| **`src/aggregator/article_fetcher.py`** | `AsyncArticleFetcher`, `AsyncSessionManager`, `BrowserManager` | Asynchronously download articles with retries, resolve redirects, manage browser and HTTP sessions safely. |
| **`src/aggregator/dedup_engine.py`** | `ContentDeduplicator`, `ContentFingerprint` | Detect exact and near-duplicate content/titles using hashes, shingles and diff ratios. Stores fingerprints to JSON file. |

### 2.2 Trend Detection

| File | Key Elements | Purpose |
|------|--------------|---------|
| **`src/trends/detect.py`** | `TrendDetector`, `TrendingTopic`, `FALLBACK_TOPICS` | Multi-source trending topic extractor (Google Trends, Reddit, RSS, BuzzFeed). Provides deduped ranked list. |
| **`src/trends/search.py`** | `ArticleFinder`, `ArticleSource` | Given a topic, query Google News, NewsAPI, Reddit and RSS feeds for article URLs. Handles API keys and async cleanup. |

### 2.3 Generation

| File | Highlights | Purpose |
|------|-----------|---------|
| **`src/generator/generate_post.py`** | `AIGenerator`, `ContentValidator`, `ContentResult` | Central AI pipeline: builds prompts, calls Ollama, runs multi-strategy retries, validates output length/safety, returns scored result. |
| **`src/generator/quality_scorer.py`** | `ContentQualityScorer`, `QualityScore` | Calculates readability (Flesch), SEO, engagement and technical formatting scores; provides actionable recommendations. |

### 2.4 Publishing

| File | Highlights | Purpose |
|------|-----------|---------|
| **`src/publisher/post_to_site.py`** | `save_blog_to_database_and_files`, helpers | Converts markdown to HTML, generates post URLs, tags, stores in DB and forwards to Notion. |
| **`src/publisher/notion_publisher.py`** | `publish_to_notion`, utilities | Robust Notion API wrapper: maps blog metadata to database properties, splits long content into blocks, retries on rate limits. |

### 2.5 Database & Models

| File | Highlights | Purpose |
|------|-----------|---------|
| **`src/database/models.py`** | `BlogPost`, `DatabaseManager` | SQLite schema, CRUD helpers, unique constraints, duplicate cleanup. |
| **`src/database/manager.py`** | `get_engine`, `get_session_factory` | SQLAlchemy engine / session factory helper (Postgres or SQLite). |

### 2.6 Scheduling & Automation

| File | Highlights | Purpose |
|------|-----------|---------|
| **`src/scheduler/schedule.py`** | `BlogScheduler` | APScheduler-powered cron tasks: periodic generation, maintenance, cleanup, graceful shutdown. |

### 2.7 Monitoring & Health

| File | Highlights | Purpose |
|------|-----------|---------|
| **`src/monitoring/analytics.py`** | `AnalyticsDashboard` | Aggregates content stats, system metrics and trend charts for dashboards. |
| **`src/monitoring/health_check.py`** | `HealthChecker`, `HealthStatus` | Checks CPU, memory, disk, AI service, file permissions, uptime. |
| **`src/monitoring/metrics.py`** | `MetricsCollector`, decorators | In-memory metrics, timers, counters with retention and cleanup. |
| **`src/monitoring/alerts.py`** | `AlertManager`, helpers | Centralized alerting: email, webhook, file fallback with rate-limiting. |

### 2.8 Utilities & Support

| File | Highlights | Purpose |
|------|-----------|---------|
| **`backup.py`** | `create_backup`, `schedule_backups` | Zip-based backup of key directories with rotation.
| **`monitor.py`** | `check_system_health` CLI | CLI wrapper for quick system health overview.
| **`structured_logging.py`** | `StructuredLogger`, `JSONFormatter` | JSON & human log formats with rotation and context fields.

### 2.9 Core Entrypoint & Security

| File | Highlights | Purpose |
|------|-----------|---------|
| **`main.py`** | `BlogSystemManager` | Application bootstrap: loads env, starts Flask UI, launches scheduler, handles shutdown.
| **`security_enhancements.py`** | `SecurityManager`, `InputValidator` | Adds CSRF, CSP, rate limiting, API key auth, secure file upload validation.

---

## 3. Data Flow Cheat Sheet

1. **Scheduler** triggers `blog_generation_task`.
2. **TrendDetector** fetches topics ➜ `ArticleFinder` returns URLs.
3. **AsyncArticleFetcher** downloads & resolves each URL.
4. **DedupEngine** checks similarity; valid texts passed forward.
5. **AIGenerator** crafts multi-strategy prompts → Ollama.
6. **QualityScorer** rates output; if acceptable → continue.
7. **Post_to_site** stores post in DB → `NotionPublisher` / HTML.
8. **MetricsCollector** logs timings; **AnalyticsDashboard** updates dashboards.
9. **HealthChecker** runs periodic system checks; **AlertManager** notifies on issues.

---

## 4. Extension Points

| Extension | How-To | File to Modify |
|-----------|-------|----------------|
| **New Publishing Platform** | Create new publisher class implementing `publish()`; add to `PublishingConfig.platforms`. | `src/publisher/` |
| **Custom AI Model** | Update `AIConfig.model_name` and add prompt strategy if needed. | `config.py`, `generate_post.py` |
| **Extra Trend Source** | Add method in `TrendDetector.sources` dict. | `detect.py` |
| **Authentication Provider** | Extend `SecurityManager` with new auth decorator. | `security_enhancements.py` |

---

## 5. Development Tips

- **Run single cycle**: `python main.py --run-once`
- **Tail logs**: `tail -f blog_system.log`
- **Live documentation server**: `mkdocs serve` (docs directory)
- **Test coverage**: `pytest --cov=src/`

---

**Happy hacking!** For detailed contribution rules, see `CONTRIBUTING.md`.