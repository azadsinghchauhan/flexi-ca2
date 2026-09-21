import datetime
from database.models import Topic, Article, Alert
from services.trend_detector import detect_topic_trends


def generate_intelligence_report(topic_id=None, db_session=None):
    """
    Synthesizes topic intelligence, emerging trends, critical alerts, and
    article takeaways into an executive briefing report.
    """
    if db_session is None:
        return {"error": "Database session not provided"}

    topic = None
    if topic_id:
        topic = db_session.query(Topic).filter(Topic.id == topic_id).first()
        topic_name = topic.name if topic else f"Topic #{topic_id}"
        articles = db_session.query(Article).filter(Article.topic_id == topic_id).order_by(Article.published_at.desc()).all()
    else:
        topic_name = "Comprehensive Multi-Topic Intelligence"
        articles = db_session.query(Article).order_by(Article.published_at.desc()).all()

    alerts = db_session.query(Alert).filter(Alert.read == False).order_by(Alert.created_at.desc()).limit(10).all()
    trends_data = detect_topic_trends(topic_id=topic_id, db_session=db_session)

    high_priority_articles = [a for a in articles if a.importance == "High"]
    categories = set(a.category for a in articles if a.category)

    now_str = datetime.datetime.utcnow().strftime("%B %d, %Y - %H:%M UTC")

    # Synthesize briefing
    briefing = {
        "title": f"Executive Intelligence Briefing: {topic_name}",
        "generated_at": now_str,
        "topic_name": topic_name,
        "topic_id": topic_id,
        "stats": {
            "total_articles": len(articles),
            "high_priority_count": len(high_priority_articles),
            "emerging_trends_count": trends_data.get("emerging_count", 0),
            "categories_covered": len(categories)
        },
        "trends": trends_data.get("trends", [])[:5],
        "formula": trends_data.get("formula", ""),
        "criteria": trends_data.get("criteria", ""),
        "high_priority_signals": [a.to_dict() for a in high_priority_articles[:5]],
        "recent_articles": [a.to_dict() for a in articles[:8]],
        "active_alerts": [al.to_dict() for al in alerts[:5]],
    }

    # Generate Markdown representation for easy export
    md_lines = [
        f"# {briefing['title']}",
        f"**Generated:** {briefing['generated_at']}\n",
        "## Executive Summary",
        f"This autonomous monitoring briefing synthesizes **{len(articles)} articles** across **{len(categories)} distinct categories**. "
        f"The agent detected **{trends_data.get('emerging_count', 0)} emerging technological trends** and flagged "
        f"**{len(high_priority_articles)} high-priority strategic signals** requiring attention.\n",
        "## Key Quantitative Metrics",
        f"- **Total Monitored Articles:** {len(articles)}",
        f"- **High-Priority Signals:** {len(high_priority_articles)}",
        f"- **Emerging Trends (Growth ≥ +50%):** {trends_data.get('emerging_count', 0)}",
        f"- **Active Unread Alerts:** {len(alerts)}\n",
        "## Emerging Trends & Signals (Explainable Growth Model)",
        f"> *Mathematical Basis:* `{trends_data.get('formula')}` | *Threshold:* `{trends_data.get('criteria')}`\n"
    ]

    for t in trends_data.get("trends", [])[:5]:
        badge = "[EMERGING]" if t["is_emerging"] else f"[{t['status_badge'].upper()}]"
        md_lines.append(f"- **{t['name']}** {badge}: {t['recent_count']} recent mentions ({t['growth_pct']:+}% vs prior 7d). Key entities: {', '.join(t['related_keywords'])}")

    md_lines.append("\n## Critical High-Priority Signals")
    if high_priority_articles:
        for a in high_priority_articles[:5]:
            md_lines.append(f"### {a.title}")
            md_lines.append(f"- **Source:** {a.source} | **Category:** {a.category} | **Relevance:** {a.relevance}%")
            md_lines.append(f"- **Summary:** {a.summary}")
            md_lines.append(f"- **Strategic Significance:** {a.reason}")
            md_lines.append(f"- **Canonical Link:** [{a.url}]({a.url})\n")
    else:
        md_lines.append("No critical alerts flagged in this evaluation window.\n")

    briefing["markdown"] = "\n".join(md_lines)
    return briefing
