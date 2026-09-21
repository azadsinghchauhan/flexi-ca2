import os
import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from dotenv import load_dotenv

# Database & Models
from database.db import get_db, init_db, engine
from database.models import Topic, Article, MonitoringLog, Alert

# Services & Agent
from agents.news_monitor import NewsMonitorAgent
from services.trend_detector import detect_topic_trends
from services.report_builder import generate_intelligence_report
from services.news_fetcher import TAVILY_API_KEY, DEMO_MODE
from services.article_analyzer import GROQ_API_KEY, GROQ_MODEL

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "news-agent-secret-key-2026")

# Automatically initialize database schema on startup
try:
    init_db()
    with get_db() as _db:
        if _db.query(Topic).count() == 0:
            defaults = [
                {
                    "name": "Autonomous AI Agents & Orchestration",
                    "keywords": "agentic workflows, LLM reasoning, multi-agent systems, tool use, reflection loop",
                    "frequency": "Daily"
                },
                {
                    "name": "Quantum Computing & Post-Quantum Security",
                    "keywords": "fault-tolerant quantum, logical qubits, NIST PQC, surface code, cryogenic CMOS",
                    "frequency": "Daily"
                },
                {
                    "name": "Next-Gen Energy Storage & Batteries",
                    "keywords": "solid-state battery, sodium-ion grid, energy density, cathode chemistry, fast charging",
                    "frequency": "Daily"
                }
            ]
            for item in defaults:
                _db.add(Topic(name=item["name"], keywords=item["keywords"], frequency=item["frequency"], active=True))
            _db.commit()
except Exception as init_err:
    print(f"[WARN] Database initialization warning: {init_err}")

CRON_SECRET = os.getenv("CRON_SECRET", "super_secret_cron_token_change_me_in_production")


# ==============================================================================
# Template Context Processors & Helpers
# ==============================================================================
@app.context_processor
def inject_global_stats():
    """Inject unread alerts count and system status into all templates."""
    try:
        with get_db() as db:
            unread_alerts = db.query(Alert).filter(Alert.read == False).count()
            active_topics_count = db.query(Topic).filter(Topic.active == True).count()
            is_demo = DEMO_MODE or not bool(GROQ_API_KEY and TAVILY_API_KEY)
            return {
                "unread_alerts_count": unread_alerts,
                "active_topics_count": active_topics_count,
                "is_demo_mode": is_demo,
                "groq_model": GROQ_MODEL,
                "has_groq_key": bool(GROQ_API_KEY),
                "has_tavily_key": bool(TAVILY_API_KEY),
                "now": datetime.datetime.utcnow()
            }
    except Exception:
        return {
            "unread_alerts_count": 0,
            "active_topics_count": 0,
            "is_demo_mode": True,
            "groq_model": GROQ_MODEL,
            "has_groq_key": False,
            "has_tavily_key": False,
            "now": datetime.datetime.utcnow()
        }


class VercelPathMiddleware(object):
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        if path.startswith("/api/index.py"):
            environ["PATH_INFO"] = path[len("/api/index.py"):] or "/"
        elif path.startswith("/api/index"):
            environ["PATH_INFO"] = path[len("/api/index"):] or "/"
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathMiddleware(app.wsgi_app)


# Explicit static route ensuring CSS and JS assets are always served reliably on serverless
@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)


# ==============================================================================
# UI Routes (Views Only)
# ==============================================================================

@app.route("/")
@app.route("/api/index")
@app.route("/api/index.py")
def dashboard():
    """Dashboard view with high-level metrics, live chart data, and quick alerts."""
    with get_db() as db:
        total_articles = db.query(Article).count()
        total_topics = db.query(Topic).count()
        high_alerts = db.query(Alert).filter(Alert.read == False).order_by(Alert.created_at.desc()).limit(5).all()
        recent_logs = db.query(MonitoringLog).order_by(MonitoringLog.run_time.desc()).limit(5).all()
        recent_articles = db.query(Article).order_by(Article.published_at.desc()).limit(6).all()
        topics = db.query(Topic).all()

        trends_data = detect_topic_trends(db_session=db)
        
        return render_template(
            "dashboard.html",
            total_articles=total_articles,
            total_topics=total_topics,
            high_alerts=high_alerts,
            recent_logs=recent_logs,
            recent_articles=recent_articles,
            trends=trends_data.get("trends", [])[:4],
            emerging_count=trends_data.get("emerging_count", 0),
            topics=topics
        )


@app.route("/topics")
def topics_page():
    """Topic configuration and management view."""
    with get_db() as db:
        topics = db.query(Topic).order_by(Topic.created_at.desc()).all()
        return render_template("topics.html", topics=topics)


@app.route("/articles")
def articles_page():
    """Intelligence feed view with filters by topic, importance, category, and search."""
    topic_id = request.args.get("topic_id", type=int)
    importance = request.args.get("importance", "").strip()
    category = request.args.get("category", "").strip()
    query_str = request.args.get("q", "").strip()

    with get_db() as db:
        query = db.query(Article)

        if topic_id:
            query = query.filter(Article.topic_id == topic_id)
        if importance and importance in ("High", "Medium", "Low"):
            query = query.filter(Article.importance == importance)
        if category:
            query = query.filter(Article.category == category)
        if query_str:
            query = query.filter(Article.title.ilike(f"%{query_str}%") | Article.summary.ilike(f"%{query_str}%"))

        articles = query.order_by(Article.published_at.desc()).limit(50).all()
        topics = db.query(Topic).all()
        
        # Get distinct categories
        all_categories = [c[0] for c in db.query(Article.category).distinct() if c[0]]

        return render_template(
            "articles.html",
            articles=articles,
            topics=topics,
            categories=all_categories,
            selected_topic_id=topic_id,
            selected_importance=importance,
            selected_category=category,
            search_query=query_str
        )


@app.route("/trends")
def trends_page():
    """Explainable Trend Analysis with mathematical growth formula and comparative breakdown."""
    topic_id = request.args.get("topic_id", type=int)

    with get_db() as db:
        topics = db.query(Topic).all()
        trend_report = detect_topic_trends(topic_id=topic_id, db_session=db)
        selected_topic = db.query(Topic).filter(Topic.id == topic_id).first() if topic_id else None

        return render_template(
            "trends.html",
            topics=topics,
            selected_topic=selected_topic,
            selected_topic_id=topic_id,
            trends=trend_report.get("trends", []),
            emerging_count=trend_report.get("emerging_count", 0),
            total_trends=trend_report.get("total_trends", 0),
            formula=trend_report.get("formula"),
            criteria=trend_report.get("criteria")
        )


@app.route("/logs")
def logs_page():
    """Agent run audit trail showing 12-step timings, status badges, and details."""
    with get_db() as db:
        logs = db.query(MonitoringLog).order_by(MonitoringLog.run_time.desc()).limit(30).all()
        return render_template("logs.html", logs=logs)


@app.route("/reports")
def reports_page():
    """Executive intelligence briefing and markdown export view."""
    topic_id = request.args.get("topic_id", type=int)

    with get_db() as db:
        topics = db.query(Topic).all()
        briefing = generate_intelligence_report(topic_id=topic_id, db_session=db)

        return render_template(
            "reports.html",
            topics=topics,
            selected_topic_id=topic_id,
            briefing=briefing
        )


@app.route("/alerts")
def alerts_page():
    """Alerts center view."""
    with get_db() as db:
        alerts = db.query(Alert).order_by(Alert.created_at.desc()).all()
        return render_template("alerts.html", alerts=alerts)


# ==============================================================================
# API Endpoints (Backend Orchestration)
# ==============================================================================

@app.route("/api/monitor/run-topic/<int:topic_id>", methods=["POST"])
def api_run_topic_agent(topic_id: int):
    """
    Executes the 12-step autonomous agent for a single topic.
    Vercel-optimized: One request processes one topic within serverless limits.
    """
    try:
        with get_db() as db:
            agent = NewsMonitorAgent(topic_id=topic_id, db_session=db, article_cap=8)
            result = agent.run()
            return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/topics/active", methods=["GET"])
def api_get_active_topics():
    """Returns all active topics for sequential browser execution."""
    with get_db() as db:
        topics = db.query(Topic).filter(Topic.active == True).all()
        return jsonify([{"id": t.id, "name": t.name, "keywords": t.get_keywords_list()} for t in topics])


@app.route("/api/topics", methods=["POST"])
def api_create_topic():
    """Creates a new monitoring topic."""
    name = request.form.get("name", "").strip()
    keywords = request.form.get("keywords", "").strip()
    frequency = request.form.get("frequency", "Daily").strip()

    if not name or not keywords:
        flash("Topic name and keywords are required.", "error")
        return redirect(url_for("topics_page"))

    with get_db() as db:
        topic = Topic(name=name, keywords=keywords, frequency=frequency, active=True)
        db.add(topic)
        db.commit()

    flash(f"Topic '{name}' created successfully.", "success")
    return redirect(url_for("topics_page"))


@app.route("/api/topics/<int:topic_id>/toggle", methods=["POST"])
def api_toggle_topic(topic_id: int):
    """Toggles active status of a topic."""
    with get_db() as db:
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if topic:
            topic.active = not topic.active
            db.commit()
            return jsonify({"success": True, "active": topic.active})
        return jsonify({"success": False, "error": "Topic not found"}), 404


@app.route("/api/topics/<int:topic_id>/delete", methods=["POST"])
def api_delete_topic(topic_id: int):
    """Deletes a topic and its associated articles and logs."""
    with get_db() as db:
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if topic:
            db.delete(topic)
            db.commit()
            flash(f"Topic '{topic.name}' deleted.", "info")
        return redirect(url_for("topics_page"))


@app.route("/api/topics/seed", methods=["POST"])
def api_seed_topics():
    """Seeds rich academic default topics if none exist."""
    defaults = [
        {
            "name": "Autonomous AI Agents & Orchestration",
            "keywords": "agentic workflows, LLM reasoning, multi-agent systems, tool use, reflection loop",
            "frequency": "Hourly"
        },
        {
            "name": "Quantum Computing & Post-Quantum Security",
            "keywords": "fault-tolerant quantum, logical qubits, NIST PQC, surface code, cryogenic CMOS",
            "frequency": "Daily"
        },
        {
            "name": "Next-Gen Energy Storage & Batteries",
            "keywords": "solid-state battery, sodium-ion grid, energy density, cathode chemistry, fast charging",
            "frequency": "Daily"
        }
    ]

    with get_db() as db:
        added_count = 0
        for item in defaults:
            existing = db.query(Topic).filter(Topic.name == item["name"]).first()
            if not existing:
                t = Topic(name=item["name"], keywords=item["keywords"], frequency=item["frequency"], active=True)
                db.add(t)
                added_count += 1
        db.commit()

    flash(f"Seeded {added_count} domain monitoring topics.", "success")
    return redirect(url_for("topics_page"))


@app.route("/api/alerts/<int:alert_id>/read", methods=["POST"])
def api_mark_alert_read(alert_id: int):
    """Marks a single alert as read."""
    with get_db() as db:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.read = True
            db.commit()
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Alert not found"}), 404


@app.route("/api/alerts/mark-all-read", methods=["POST"])
def api_mark_all_alerts_read():
    """Marks all alerts as read."""
    with get_db() as db:
        db.query(Alert).update({Alert.read: True})
        db.commit()
    flash("All alerts marked as read.", "success")
    return redirect(url_for("alerts_page"))


@app.route("/api/cron/monitor", methods=["GET", "POST"])
def api_cron_monitor():
    """
    Vercel Cron endpoint scheduled daily.
    Protected via Authorization: Bearer <CRON_SECRET> header or query param.
    Runs the agent for the oldest updated active topic to remain well within timeout limits.
    """
    auth_header = request.headers.get("Authorization", "")
    secret_param = request.args.get("secret", "")

    expected = f"Bearer {CRON_SECRET}"
    if auth_header != expected and secret_param != CRON_SECRET:
        return jsonify({"error": "Unauthorized cron trigger"}), 401

    with get_db() as db:
        active_topic = db.query(Topic).filter(Topic.active == True).first()
        if not active_topic:
            return jsonify({"message": "No active topics configured for monitoring."}), 200

        agent = NewsMonitorAgent(topic_id=active_topic.id, db_session=db, article_cap=6)
        result = agent.run()
        return jsonify({
            "cron_executed": True,
            "topic_monitored": active_topic.name,
            "result": result
        }), 200


@app.route("/api/health", methods=["GET"])
def api_health():
    """Health check returning database status, key settings, and operational metrics."""
    db_ok = False
    article_count = 0
    topic_count = 0
    db_err = None
    try:
        with get_db() as db:
            article_count = db.query(Article).count()
            topic_count = db.query(Topic).count()
            db_ok = True
    except Exception as e:
        db_err = str(e)

    return jsonify({
        "status": "online" if db_ok else "degraded",
        "database_connected": db_ok,
        "database_error": db_err,
        "engine_url": str(engine.url),
        "articles_monitored": article_count,
        "topics_registered": topic_count,
        "demo_mode": DEMO_MODE or not bool(GROQ_API_KEY and TAVILY_API_KEY),
        "groq_configured": bool(GROQ_API_KEY),
        "tavily_configured": bool(TAVILY_API_KEY),
        "groq_model": GROQ_MODEL,
        "vercel_serverless": bool(os.getenv("VERCEL")),
        "timestamp": datetime.datetime.utcnow().isoformat()
    })


@app.errorhandler(404)
def page_not_found(e):
    return render_template("dashboard.html"), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1")
    print(f"Starting News Topic Monitoring Agent on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
