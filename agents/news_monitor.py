import time
import json
import datetime
from sqlalchemy.orm import Session
from database.models import Topic, Article, MonitoringLog, Alert
from services.news_fetcher import (
    build_search_queries,
    fetch_from_tavily,
    generate_mock_articles,
    normalize_article_payload,
    compute_relevance_precheck,
    TAVILY_API_KEY,
    DEMO_MODE
)
from services.deduplicator import is_duplicate_article, clean_canonical_url
from services.article_analyzer import analyze_article_with_groq
from services.trend_detector import detect_topic_trends


class NewsMonitorAgent:
    """
    Autonomous 12-Step Agentic News Monitoring Pipeline.
    Executes and audits the entire topic intelligence gathering cycle.
    """

    def __init__(self, topic_id: int, db_session: Session, article_cap: int = 8):
        self.topic_id = topic_id
        self.db = db_session
        self.article_cap = article_cap
        self.steps = []
        self.log_entry = None

    def _record_step(self, step_number: int, name: str, status: str, duration_ms: int, details: str):
        self.steps.append({
            "step_number": step_number,
            "name": name,
            "status": status,
            "duration_ms": duration_ms,
            "details": details,
            "timestamp": datetime.datetime.utcnow().strftime("%H:%M:%S.%f")[:-3]
        })

    def run(self) -> dict:
        start_overall = time.time()
        articles_found = 0
        articles_processed = 0
        duplicates_removed = 0
        alerts_created = 0
        status = "Success"
        error_message = None

        try:
            # -------------------------------------------------------------
            # Step 1: Load topic and keywords
            # -------------------------------------------------------------
            t0 = time.time()
            topic = self.db.query(Topic).filter(Topic.id == self.topic_id).first()
            if not topic:
                raise ValueError(f"Topic with ID {self.topic_id} does not exist.")
            
            keywords = topic.get_keywords_list()
            d1 = int((time.time() - t0) * 1000)
            self._record_step(
                1, "Load Topic & Keywords", "success", d1,
                f"Loaded topic '{topic.name}' with {len(keywords)} active keywords: [{', '.join(keywords)}]"
            )

            # -------------------------------------------------------------
            # Step 2: Build search queries from keywords
            # -------------------------------------------------------------
            t0 = time.time()
            queries = build_search_queries(topic.name, keywords)
            d2 = int((time.time() - t0) * 1000)
            self._record_step(
                2, "Build Search Queries", "success", d2,
                f"Generated {len(queries)} precision search query vectors: {queries}"
            )

            # -------------------------------------------------------------
            # Step 3: Fetch articles via Tavily (or Demo Generator)
            # -------------------------------------------------------------
            t0 = time.time()
            raw_articles = []
            
            # If Tavily key exists and not forced demo mode
            if TAVILY_API_KEY and not DEMO_MODE:
                for q in queries[:2]:
                    batch = fetch_from_tavily(q, max_results=self.article_cap)
                    raw_articles.extend(batch)
                
            # If no key, or demo mode, or Tavily returned empty
            if not raw_articles:
                raw_articles = generate_mock_articles(topic.name, keywords, count=self.article_cap)
                fetch_source = "Demo Intelligent Simulation"
            else:
                fetch_source = "Tavily News API"

            articles_found = len(raw_articles)
            d3 = int((time.time() - t0) * 1000)
            self._record_step(
                3, "Fetch Articles", "success", d3,
                f"Retrieved {articles_found} raw candidates using {fetch_source}"
            )

            # -------------------------------------------------------------
            # Step 4: Normalize fields (title, url, source, date, snippet)
            # -------------------------------------------------------------
            t0 = time.time()
            normalized = []
            for item in raw_articles:
                try:
                    norm = normalize_article_payload(item)
                    normalized.append(norm)
                except Exception as norm_err:
                    print(f"[WARN] Failed to normalize item: {norm_err}")
            
            d4 = int((time.time() - t0) * 1000)
            self._record_step(
                4, "Normalize Fields", "success", d4,
                f"Normalized metadata and canonical URLs for {len(normalized)} articles"
            )

            # -------------------------------------------------------------
            # Step 5: Relevance pre-check (keyword match score)
            # -------------------------------------------------------------
            t0 = time.time()
            prechecked = []
            for art in normalized:
                score = compute_relevance_precheck(art, topic.name, keywords)
                art["precheck_relevance"] = score
                # Keep articles meeting minimum baseline
                if score >= 35:
                    prechecked.append(art)
            
            d5 = int((time.time() - t0) * 1000)
            self._record_step(
                5, "Relevance Pre-Check", "success", d5,
                f"Scored relevance across tokens. Retained {len(prechecked)}/{len(normalized)} articles meeting threshold"
            )

            # -------------------------------------------------------------
            # Step 6: 3-Layer Duplicate Detection
            # -------------------------------------------------------------
            t0 = time.time()
            deduped_batch = []
            for candidate in prechecked:
                # Deduplicate against batch already accepted in this run
                is_dup, reason, matched = is_duplicate_article(candidate, deduped_batch)
                if is_dup:
                    duplicates_removed += 1
                else:
                    deduped_batch.append(candidate)

            d6 = int((time.time() - t0) * 1000)
            self._record_step(
                6, "3-Layer Duplicate Detection", "success", d6,
                f"Executed Canonical URL, Title Normalization, and Jaccard Token tests. Removed {duplicates_removed} intra-batch duplicates"
            )

            # -------------------------------------------------------------
            # Step 7: Skip articles already stored in database
            # -------------------------------------------------------------
            t0 = time.time()
            existing_articles = self.db.query(Article).filter(Article.topic_id == self.topic_id).all()
            existing_dicts = [{"canonical_url": a.canonical_url, "title": a.title, "url": a.url} for a in existing_articles]
            
            to_analyze = []
            db_dups_count = 0
            for candidate in deduped_batch:
                is_db_dup, reason, matched = is_duplicate_article(candidate, existing_dicts)
                if is_db_dup:
                    db_dups_count += 1
                    duplicates_removed += 1
                else:
                    to_analyze.append(candidate)

            # Cap articles to prevent serverless timeout
            to_analyze = to_analyze[:self.article_cap]

            d7 = int((time.time() - t0) * 1000)
            self._record_step(
                7, "Filter Existing Stored Articles", "success", d7,
                f"Checked {len(existing_articles)} historical DB entries. Skipped {db_dups_count} already stored. {len(to_analyze)} ready for AI analysis"
            )

            # -------------------------------------------------------------
            # Step 8: Send remaining articles to Groq for structured analysis
            # -------------------------------------------------------------
            t0 = time.time()
            analyzed_articles = []
            for art in to_analyze:
                try:
                    analysis = analyze_article_with_groq(
                        art,
                        topic_name=topic.name,
                        keywords=keywords,
                        precheck_score=art.get("precheck_relevance", 65)
                    )
                    art["ai_analysis"] = analysis
                    analyzed_articles.append(art)
                except Exception as ai_err:
                    print(f"[WARN] Error analyzing article '{art.get('title')}': {ai_err}")
                    # Resilience: One failing article must never crash the run
                    art["ai_analysis"] = {
                        "summary": art.get("title", "News Item"),
                        "key_points": ["Analysis encountered parsing exception", "Item preserved for review", "Automatic fallback"],
                        "category": "Uncategorized",
                        "relevance": 50,
                        "importance": "Low",
                        "entities": [],
                        "trend": "General",
                        "reason_for_importance": "Fallback on analysis exception",
                        "is_ai_analyzed": False
                    }
                    analyzed_articles.append(art)

            d8 = int((time.time() - t0) * 1000)
            self._record_step(
                8, "Groq AI Structured Analysis", "success", d8,
                f"Generated validated JSON intelligence for {len(analyzed_articles)} articles via Groq / Structured Engine"
            )

            # -------------------------------------------------------------
            # Step 9: Store results in database
            # -------------------------------------------------------------
            t0 = time.time()
            saved_entities = []
            for item in analyzed_articles:
                ai = item.get("ai_analysis", {})
                new_art = Article(
                    topic_id=self.topic_id,
                    title=item.get("title"),
                    url=item.get("url"),
                    canonical_url=item.get("canonical_url") or clean_canonical_url(item.get("url")),
                    source=item.get("source"),
                    published_at=item.get("published_at"),
                    category=ai.get("category", "General"),
                    summary=ai.get("summary", ""),
                    key_points=json.dumps(ai.get("key_points", [])),
                    importance=ai.get("importance", "Medium"),
                    relevance=ai.get("relevance", 50),
                    trend=ai.get("trend", ""),
                    entities=json.dumps(ai.get("entities", [])),
                    reason=ai.get("reason_for_importance", ""),
                    is_demo=item.get("is_demo", False)
                )
                self.db.add(new_art)
                saved_entities.append(new_art)

            self.db.flush()  # Populate IDs
            articles_processed = len(saved_entities)
            d9 = int((time.time() - t0) * 1000)
            self._record_step(
                9, "Persist Results to Database", "success", d9,
                f"Saved {articles_processed} new analyzed articles to storage table"
            )

            # -------------------------------------------------------------
            # Step 10: Recompute trends for the topic
            # -------------------------------------------------------------
            t0 = time.time()
            trends_calc = detect_topic_trends(topic_id=self.topic_id, db_session=self.db)
            d10 = int((time.time() - t0) * 1000)
            self._record_step(
                10, "Recompute Topic Trends", "success", d10,
                f"Recomputed 7d vs prior 7d growth metrics. Found {trends_calc.get('emerging_count', 0)} emerging trends across {trends_calc.get('total_trends', 0)} clusters"
            )

            # -------------------------------------------------------------
            # Step 11: Create an alert if any article is rated High importance
            # -------------------------------------------------------------
            t0 = time.time()
            for art in saved_entities:
                if art.importance == "High":
                    alert_msg = f"High Priority: {art.title} ({art.source}) - {art.reason}"
                    alert = Alert(
                        article_id=art.id,
                        message=alert_msg,
                        read=False
                    )
                    self.db.add(alert)
                    alerts_created += 1

            self.db.flush()
            d11 = int((time.time() - t0) * 1000)
            self._record_step(
                11, "Generate High-Importance Alerts", "success", d11,
                f"Scanned new articles. Generated {alerts_created} immediate alerts for High importance signals"
            )

        except Exception as main_err:
            status = "Error"
            error_message = str(main_err)
            print(f"[ERROR] Agent pipeline failure on topic {self.topic_id}: {main_err}")
            self._record_step(
                len(self.steps) + 1, "Pipeline Exception Handler", "failed", 0,
                f"Pipeline encountered error: {error_message}"
            )

        # -------------------------------------------------------------
        # Step 12: Write monitoring log row
        # -------------------------------------------------------------
        t0 = time.time()
        log_row = MonitoringLog(
            topic_id=self.topic_id,
            run_time=datetime.datetime.utcnow(),
            articles_found=articles_found,
            articles_processed=articles_processed,
            duplicates_removed=duplicates_removed,
            status=status,
            error=error_message,
            steps=json.dumps(self.steps)
        )
        self.db.add(log_row)
        self.db.commit()

        d12 = int((time.time() - t0) * 1000)
        self._record_step(
            12, "Write Monitoring Audit Log", "success", d12,
            f"Logged complete execution telemetry with {len(self.steps)} step benchmarks"
        )
        # Update stored log with step 12 included
        log_row.steps = json.dumps(self.steps)
        self.db.commit()

        total_duration_sec = round(time.time() - start_overall, 2)

        return {
            "success": status != "Error",
            "topic_id": self.topic_id,
            "topic_name": topic.name if 'topic' in locals() and topic else "Unknown",
            "status": status,
            "error": error_message,
            "articles_found": articles_found,
            "articles_processed": articles_processed,
            "duplicates_removed": duplicates_removed,
            "alerts_created": alerts_created,
            "duration_seconds": total_duration_sec,
            "steps": self.steps
        }
