# Automated News Topic Monitoring Using Agentic AI
> **Academic Flexi Credit Project // College Capstone / Viva Evaluation**  
> An autonomous multi-step intelligence pipeline for news topic monitoring, 3-layer deduplication, Groq AI structured extraction, explainable trend analytics, and automated alerting.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Framework](https://img.shields.io/badge/Framework-Flask_3.1-black?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![AI Engine](https://img.shields.io/badge/AI_Engine-Groq_LPU-f55036?logo=groq&logoColor=white)](https://groq.com/)
[![Search](https://img.shields.io/badge/Search_API-Tavily_News-00f0ff)](https://tavily.com/)
[![Deployment](https://img.shields.io/badge/Deployment-Vercel_Serverless-black?logo=vercel&logoColor=white)](https://vercel.com/)

---

## 1. Project Overview & Agentic Philosophy

Unlike conventional RSS readers or news websites with a simple "summarize" button, this system is an **autonomous agentic workflow**. The user provides only high-level monitoring goals (a topic title plus target keyword vectors). 

Upon triggering, the autonomous agent executes a deterministic, audited **12-step pipeline**:
1. Formulates multi-vector search queries.
2. Queries the Tavily News API (or secondary RSS / simulation pool).
3. Normalizes unstructured metadata across publishers.
4. Computes keyword relevance pre-scores.
5. Filters duplicates across a **3-layer explainable deduplication hierarchy**.
6. Compares candidates against historically indexed database articles.
7. Dispatches unique articles to **Groq AI in JSON Mode** for deep structural extraction.
8. Enforces strict schema validation (summary, 3 key takeaways, entities, category, priority, reason).
9. Persists intelligence into SQLAlchemy storage.
10. Recomputes mathematical **7-day comparative trend growth velocity**.
11. Triggers instantaneous **tactical alerts** for `High` importance signals.
12. Writes detailed execution telemetry with millisecond benchmarks to the audit log.

---

## 2. System Architecture

```
                                  [ USER / BROWSER ]
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   ▼                                             ▼
          Interactive Web UI                           "Run Monitoring Now"
    (Dashboard, Feeds, Trends, Logs)              (Sequential Browser Orchestrator)
                   │                                             │
                   │                                     POST /api/monitor/
                   │                                        run-topic/:id
                   ▼                                             ▼
            Flask Web Server                            12-Step Agent Pipeline
               (app.py)                                (agents/news_monitor.py)
                   │                                             │
                   ├───────────────────────┬─────────────────────┤
                   ▼                       ▼                     ▼
          [ Tavily Search API ]    [ Groq LPU API ]    [ SQLAlchemy DB ]
          - Real-time News         - JSON Mode          - SQLite (Local)
          - Recent 7-Day Window    - Reasoning Model    - Neon Postgres (Vercel)
```

---

## 3. The 12-Step Agent Workflow

| Step # | Stage Name | Purpose & Verification |
| :---: | :--- | :--- |
| **1** | **Load Topic & Keywords** | Retrieves active topic goals and parses keyword vectors. |
| **2** | **Build Search Queries** | Synthesizes Boolean and topical search vectors (e.g. `Topic + Keywords + Developments 2026`). |
| **3** | **Fetch Articles** | Queries Tavily Search API targeting news within the past 7 days (or realistic academic generator in demo mode). |
| **4** | **Normalize Fields** | Strips tracking parameters, extracts root publisher domains, and parses ISO timestamps. |
| **5** | **Relevance Pre-Check** | Evaluates token matches across title (60% weight) and snippet (40% weight), discarding irrelevant noise. |
| **6** | **3-Layer Deduplication** | Removes intra-batch duplicates via canonical URL, normalized title, and token Jaccard similarity. |
| **7** | **Filter Historical DB** | Compares candidates against existing stored articles to guarantee zero re-processing. |
| **8** | **Groq AI Analysis** | Dispatches unique articles to Groq using JSON Mode (`response_format={"type": "json_object"}`). |
| **9** | **Store Results** | Writes structured intelligence, 3 key points, entity tags, and importance ratings to the database. |
| **10** | **Recompute Trends** | Calculates 7-day comparative growth rates across detected trend clusters. |
| **11** | **Generate Alerts** | Immediately flags articles with `High` importance and issues actionable notifications. |
| **12** | **Write Audit Log** | Writes execution telemetry with millisecond execution durations for each step to the audit trail. |

> **Resilience Guarantee:** A single failing or malformed article never crashes the monitoring cycle. The agent isolates exceptions per article, falls back to marked heuristic intelligence, and continues execution.

---

## 4. Key Academic Algorithms (Viva Defense)

### A. 3-Layer Explainable Deduplication Engine (`services/deduplicator.py`)
Rather than relying on opaque embeddings for basic duplicate checking, the system uses an explainable, deterministic 3-tier hierarchy:
1. **Layer 1 — Canonical URL Normalization:**  
   Strips query tracking parameters (`utm_source`, `utm_medium`, `fbclid`, `gclid`, `ref`, etc.), lowercases the hostname, discards URL fragments (`#...`), and normalizes trailing slashes.
2. **Layer 2 — Normalized Title Match:**  
   Strips publisher suffixes (e.g. ` - TechCrunch`, ` | Reuters`), eliminates punctuation, lowercases characters, and collapses whitespace.
3. **Layer 3 — Title Token Jaccard Similarity:**  
   Computes token intersection over union between word sets:
   $$\text{Jaccard}(A, B) = \frac{|A \cap B|}{|A \cup B|}$$
   Combined with SequenceMatcher ratio. Pairs exceeding threshold $\ge 0.75$ are classified as duplicates.

### B. Explainable Mathematical Trend Velocity Model (`services/trend_detector.py`)
The system partitions monitored articles into two consecutive 7-day temporal windows:
- **Recent Window ($W_{\text{recent}}$):** Articles published within $t_{0}$ to $t_{-7}$ days.
- **Previous Baseline Window ($W_{\text{prev}}$):** Articles published within $t_{-7}$ to $t_{-14}$ days.

**Growth Velocity Formula:**
$$\text{Growth} = \frac{\text{Recent} - \text{Previous}}{\max(\text{Previous}, 1)}$$
$$\text{Growth Percentage} = \text{Growth} \times 100\%$$

**Emerging Trend Criteria:**
A trend cluster is formally classified as **Emerging** if and only if:
$$(\text{Recent} \ge 3) \land (\text{Growth} \ge +50.0\%)$$

---

## 5. Technology Stack

- **Backend:** Python 3.10+, Flask 3.1
- **Database:** SQLAlchemy 2.0 (SQLite locally; Neon PostgreSQL in production)
- **AI Engine:** Groq Cloud API (`GROQ_MODEL=openai/gpt-oss-20b` or `llama-3.3-70b-versatile`) with JSON Mode
- **News Aggregation:** Tavily Search API (news domain, recent days filter) + optional feedparser RSS
- **Frontend:** Server-rendered Jinja2 templates, Vanilla CSS (Cyber-Intelligence Glassmorphism), Vanilla JavaScript, Chart.js 4.4 from CDN (Zero frontend build step required)
- **Deployment:** Vercel Serverless Functions + Vercel Cron

---

## 6. Local Quickstart Guide

### Prerequisites
- Python 3.10+ installed
- Git installed

### Installation Steps

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/azadsinghchauhan/flexi-ca2.git
   cd flexi-ca2
   ```

2. **Install Dependencies:**
   ```bash
   python -m pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your API keys:
   ```env
   GROQ_API_KEY=gsk_...
   GROQ_MODEL=openai/gpt-oss-20b
   TAVILY_API_KEY=tvly-...
   DATABASE_URL=sqlite:///news_monitor.db
   CRON_SECRET=your_secret_token
   DEMO_MODE=false
   ```
   *(Note: If API keys are left blank or `DEMO_MODE=true`, the app automatically activates the zero-config realistic simulation generator so examiners can test with zero external dependencies!)*

4. **Initialize Database & Seed Academic Defaults:**
   ```bash
   python -c "from database.db import init_db; init_db(); print('Database schema created.')"
   ```

5. **Run the Application:**
   ```bash
   python app.py
   ```
   Open your browser at: **`http://127.0.0.1:5000`**

6. **Execute Automated Unit Tests:**
   ```bash
   python -m unittest discover tests -v
   ```

---

## 7. Vercel Serverless Architecture & Deployment

### Serverless Design Constraints Addressed:
1. **Read-Only / Ephemeral Filesystem:**  
   Vercel serverless functions cannot write persistent data to disk. The application automatically redirects local SQLite files to `/tmp` in ephemeral environments, and integrates natively with **Neon Serverless PostgreSQL** when `DATABASE_URL=postgresql://...` is set.
2. **Function Execution Timeouts:**  
   Vercel functions enforce strict timeouts (10s on hobby plans, up to 60s via `maxDuration`). Rather than running a monolithic multi-minute batch job, the "Run Monitoring Now" button executes a **browser-driven sequential orchestrator** (`static/js/app.js`):
   - Browser calls `/api/monitor/run-topic/<id>` one topic at a time.
   - Each topic monitors capped articles (e.g. 4-8), completing in ~3-6 seconds.
   - Live SSE/JSON telemetry updates the on-screen 12-step animation modal in real time.
3. **Automated Scheduling (Vercel Cron):**  
   Scheduled via `vercel.json` calling `/api/cron/monitor` daily. Protected with `Authorization: Bearer <CRON_SECRET>` headers.

### Deploying to Vercel:
1. Push project to GitHub.
2. Import repository into [Vercel](https://vercel.com).
3. In Vercel Project Settings &rarr; Environment Variables, add:
   - `GROQ_API_KEY`
   - `GROQ_MODEL`
   - `TAVILY_API_KEY`
   - `DATABASE_URL` (Neon PostgreSQL connection string)
   - `CRON_SECRET`
4. Click **Deploy**. Vercel will automatically configure serverless functions via `vercel.json`.

---

## 8. Project Structure

```
├── agents/
│   └── news_monitor.py         # Autonomous 12-step agent pipeline & telemetry
├── database/
│   ├── db.py                   # SQLAlchemy engine, session scoping, Vercel /tmp fallback
│   └── models.py               # Topic, Article, MonitoringLog, and Alert entities
├── services/
│   ├── article_analyzer.py     # Groq JSON Mode integration, schema validation, rate-limit backoff
│   ├── deduplicator.py         # 3-layer explainable deduplication (URL, Title, Token Jaccard)
│   ├── news_fetcher.py         # Tavily Search client, metadata normalization, mock generator
│   ├── report_builder.py       # Executive intelligence briefing synthesis & Markdown export
│   └── trend_detector.py       # 7-day comparative growth formula & emerging signal detection
├── static/
│   ├── css/
│   │   └── style.css           # Cyber-Intelligence Glassmorphism design system
│   └── js/
│       └── app.js              # Client-side sequential orchestrator & modal visualizer
├── templates/
│   ├── base.html               # Global navigation, agent modal runner, system status indicator
│   ├── dashboard.html          # KPI grid, Chart.js trends, recent articles, audit table
│   ├── topics.html             # Topic goals management, active toggle, seed button
│   ├── articles.html           # Multi-filter intelligence feed with AI analysis badges
│   ├── trends.html             # Mathematical formula banner, 7d vs 7d Chart.js, emerging signals
│   ├── logs.html               # Full telemetry audit trail with 12-step inspection modal
│   ├── reports.html            # Executive intelligence briefing generator with Markdown copy & PDF
│   └── alerts.html             # High-priority tactical alert notifications center
├── tests/
│   └── test_agent_pipeline.py  # 9 comprehensive unit tests
├── .env.example                # Sample environment template
├── .gitignore                  # Git exclusion rules (.env, *.db, __pycache__)
├── app.py                      # Clean Flask route declarations
├── requirements.txt            # Python dependencies
├── vercel.json                 # Vercel serverless build, routing, and cron config
└── README.md                   # Comprehensive documentation & Viva guide
```

---

## 9. Academic Evaluation & Viva Defense Highlights

When presenting this project for your Flexi Credit viva evaluation, emphasize:
- **True Agentic Workflow:** It is not a news website with a summarize button. It autonomously formulates search vectors, normalizes schemas, verifies relevance, filters duplicates, analyzes priorities with Groq, computes trend calculus, issues alerts, and records execution audit logs.
- **Explainability:** Explain why Layer 1 (URL), Layer 2 (Title), and Layer 3 (Jaccard) deduplication are used instead of black-box clustering. Point directly to the formula banner on the `/trends` page showing $\text{Growth} = \frac{\text{Recent} - \text{Previous}}{\max(\text{Previous}, 1)}$.
- **Production Resilience:** Demonstrate that Groq API rate limits (HTTP 429) back off exponentially, malformed JSON is retried once, and isolated article errors fall back gracefully without aborting the overall monitoring run.
- **Zero-Config Demo Capability:** Show that examiners can run the application with or without external API keys by toggling `DEMO_MODE=true`.

---
*Created for Flexi Credit Academic Project Evaluation &bull; 2026*
