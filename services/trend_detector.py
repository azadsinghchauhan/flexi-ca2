import datetime
from collections import defaultdict
from database.models import Article


def detect_topic_trends(topic_id=None, db_session=None):
    """
    Explainable Trend Detection Engine.
    No black-box ML:
    1. Aggregates AI-assigned trend labels and extracted entities.
    2. Compares article occurrences in the last 7 days vs previous 7 days.
    3. Calculates Growth = (Recent - Previous) / max(Previous, 1)
    4. Flags as 'Emerging' when Recent >= 3 and Growth >= +50% (0.50).
    """
    if db_session is None:
        return {"trends": [], "emerging_count": 0, "total_trends": 0}

    now = datetime.datetime.utcnow()
    seven_days_ago = now - datetime.timedelta(days=7)
    fourteen_days_ago = now - datetime.timedelta(days=14)

    query = db_session.query(Article)
    if topic_id:
        query = query.filter(Article.topic_id == topic_id)
    
    articles = query.all()
    if not articles:
        return {
            "formula": "Growth = (Recent - Previous) / max(Previous, 1)",
            "criteria": "Emerging when Recent >= 3 AND Growth >= +50%",
            "trends": [],
            "emerging_count": 0,
            "total_trends": 0
        }

    # Group counts and track references
    recent_counts = defaultdict(int)
    prev_counts = defaultdict(int)
    total_counts = defaultdict(int)
    trend_articles = defaultdict(list)
    trend_entities = defaultdict(set)

    for art in articles:
        # Determine trend key
        trend_name = (art.trend or "General Developments").strip()
        # Clean capitalization
        trend_name = " ".join(w.capitalize() for w in trend_name.split())
        
        art_date = art.published_at or art.created_at or now

        total_counts[trend_name] += 1
        trend_articles[trend_name].append({
            "id": art.id,
            "title": art.title,
            "url": art.url,
            "source": art.source or "Web",
            "importance": art.importance,
            "published_at": art_date.strftime("%Y-%m-%d")
        })

        for ent in art.get_entities_list():
            trend_entities[trend_name].add(ent)

        if art_date >= seven_days_ago:
            recent_counts[trend_name] += 1
        elif art_date >= fourteen_days_ago:
            prev_counts[trend_name] += 1

    trends_list = []
    emerging_count = 0

    for trend_name, total_cnt in total_counts.items():
        recent = recent_counts[trend_name]
        prev = prev_counts[trend_name]
        
        # Exact viva formula
        growth = (recent - prev) / max(prev, 1)
        growth_pct = round(growth * 100, 1)

        # Emerging condition: recent >= 3 and growth >= 50%
        is_emerging = bool(recent >= 3 and growth >= 0.50)
        if is_emerging:
            emerging_count += 1

        # Status badge label
        if is_emerging:
            status_badge = "Emerging"
            badge_class = "badge-emerging"
        elif growth > 0:
            status_badge = "Growing"
            badge_class = "badge-growing"
        elif growth == 0:
            status_badge = "Stable"
            badge_class = "badge-stable"
        else:
            status_badge = "Cooling"
            badge_class = "badge-cooling"

        trends_list.append({
            "name": trend_name,
            "recent_count": recent,
            "previous_count": prev,
            "total_count": total_cnt,
            "growth": round(growth, 2),
            "growth_pct": growth_pct,
            "is_emerging": is_emerging,
            "status_badge": status_badge,
            "badge_class": badge_class,
            "related_keywords": list(trend_entities[trend_name])[:5],
            "example_articles": trend_articles[trend_name][:3]
        })

    # Sort: Emerging first, then highest recent count, then growth percentage
    trends_list.sort(key=lambda t: (t["is_emerging"], t["recent_count"], t["growth_pct"]), reverse=True)

    return {
        "formula": "Growth = (Recent - Previous) / max(Previous, 1)",
        "criteria": "Emerging when Recent >= 3 AND Growth >= +50%",
        "trends": trends_list,
        "emerging_count": emerging_count,
        "total_trends": len(trends_list)
    }
