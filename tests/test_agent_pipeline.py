import unittest
import json
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.db import Base
from database.models import Topic, Article, MonitoringLog, Alert
from services.deduplicator import (
    clean_canonical_url,
    normalize_title,
    calculate_token_jaccard_similarity,
    is_duplicate_article
)
from services.article_analyzer import validate_analysis_schema, get_heuristic_fallback
from services.trend_detector import detect_topic_trends
from services.news_fetcher import compute_relevance_precheck
from agents.news_monitor import NewsMonitorAgent
from app import app


class TestNewsTopicMonitoringAgent(unittest.TestCase):

    def setUp(self):
        # Create in-memory SQLite database for isolated testing
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.client = app.test_client()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_layer1_canonical_url_deduplication(self):
        """Test Layer 1: Canonical URL stripping of UTM/tracking query parameters."""
        url1 = "https://techcrunch.com/2026/03/ai-news?utm_source=twitter&utm_medium=social#heading"
        url2 = "https://techcrunch.com/2026/03/ai-news"
        url3 = "https://techcrunch.com/2026/03/ai-news/?ref=newsletter&fbclid=xyz"

        canon1 = clean_canonical_url(url1)
        canon2 = clean_canonical_url(url2)
        canon3 = clean_canonical_url(url3)

        self.assertEqual(canon1, canon2)
        self.assertEqual(canon2, canon3)

        cand = {"url": url1, "title": "Unique Title 1"}
        existing = [{"url": url2, "title": "Different Title"}]
        is_dup, reason, _ = is_duplicate_article(cand, existing)
        self.assertTrue(is_dup)
        self.assertIn("Canonical URL", reason)

    def test_layer2_normalized_title_deduplication(self):
        """Test Layer 2: Normalized title exact match after stripping symbols and source."""
        t1 = "Quantum Computing Reaches Fault-Tolerance! - TechCrunch"
        t2 = "quantum computing reaches faulttolerance"

        cand = {"url": "https://sourceA.com/art1", "title": t1}
        existing = [{"url": "https://sourceB.com/art2", "title": t2}]

        is_dup, reason, _ = is_duplicate_article(cand, existing)
        self.assertTrue(is_dup)
        self.assertIn("Normalized Title Match", reason)

    def test_layer3_token_jaccard_similarity(self):
        """Test Layer 3: Jaccard word token similarity."""
        t1 = "Autonomous AI agents transform enterprise workflow automation"
        t2 = "Autonomous AI agents revolutionize enterprise workflow systems"

        sim = calculate_token_jaccard_similarity(t1, t2)
        self.assertGreater(sim, 0.65)

        cand = {"url": "https://siteA.com/a", "title": t1}
        existing = [{"url": "https://siteB.com/b", "title": t2}]
        is_dup, reason, _ = is_duplicate_article(cand, existing, similarity_threshold=0.65)
        self.assertTrue(is_dup)
        self.assertIn("Token Similarity", reason)

    def test_groq_schema_validation(self):
        """Test Groq structured JSON schema validation and standardization."""
        raw_valid = {
            "summary": "This is a detailed 2 sentence summary. It explains the major breakthroughs.",
            "key_points": ["First point", "Second point", "Third point"],
            "category": "Artificial Intelligence",
            "relevance": 92,
            "importance": "High",
            "entities": ["Groq", "Llama 3.3", "Meta"],
            "trend": "LPU Hardware Acceleration",
            "reason_for_importance": "Critical architectural leap in inference latency."
        }

        validated = validate_analysis_schema(raw_valid)
        self.assertEqual(validated["importance"], "High")
        self.assertEqual(validated["relevance"], 92)
        self.assertEqual(len(validated["key_points"]), 3)
        self.assertTrue(validated["is_ai_analyzed"])

        # Test padding when key points < 3
        raw_short = {
            "summary": "Short summary",
            "key_points": ["Only one point"],
            "importance": "invalid_priority"
        }
        val_short = validate_analysis_schema(raw_short)
        self.assertEqual(len(val_short["key_points"]), 3)
        self.assertEqual(val_short["importance"], "Medium")

    def test_heuristic_fallback_resilience(self):
        """Test that heuristic fallback never crashes on empty/error inputs."""
        sample_art = {
            "title": "Critical Breakthrough in Sodium-Ion Grid Batteries",
            "content": "Engineers published a major report regarding energy storage.",
            "source": "Nature Energy"
        }
        fb = get_heuristic_fallback(sample_art, "Energy Storage", 80)
        self.assertEqual(fb["importance"], "High")  # 'Critical Breakthrough' triggers High
        self.assertEqual(len(fb["key_points"]), 3)
        self.assertFalse(fb["is_ai_analyzed"])

    def test_explainable_trend_detection_formula(self):
        """
        Verify the viva formula:
        Growth = (Recent - Previous) / max(Previous, 1)
        Emerging = Recent >= 3 AND Growth >= +50%
        """
        now = datetime.datetime.utcnow()
        t = Topic(name="AI Test Topic", keywords="agents, reasoning", active=True)
        self.db.add(t)
        self.db.commit()

        # Add 4 articles in recent 7 days (days_ago = 2)
        for i in range(4):
            art = Article(
                topic_id=t.id,
                title=f"Recent Agent Paper #{i}",
                url=f"https://arxiv.org/abs/2603.00{i}",
                canonical_url=f"https://arxiv.org/abs/2603.00{i}",
                published_at=now - datetime.timedelta(days=2),
                importance="High",
                trend="Autonomous Agents Velocity",
                entities=json.dumps(["Agent", "LLM"])
            )
            self.db.add(art)

        # Add 1 article in previous 7 days (days_ago = 10)
        art_prev = Article(
            topic_id=t.id,
            title="Old Baseline Paper",
            url="https://arxiv.org/abs/2602.001",
            canonical_url="https://arxiv.org/abs/2602.001",
            published_at=now - datetime.timedelta(days=10),
            importance="Medium",
            trend="Autonomous Agents Velocity",
            entities=json.dumps(["Agent"])
        )
        self.db.add(art_prev)
        self.db.commit()

        trends = detect_topic_trends(topic_id=t.id, db_session=self.db)
        self.assertEqual(trends["emerging_count"], 1)
        target_trend = trends["trends"][0]
        self.assertEqual(target_trend["name"], "Autonomous Agents Velocity")
        self.assertEqual(target_trend["recent_count"], 4)
        self.assertEqual(target_trend["previous_count"], 1)

        # Growth = (4 - 1) / max(1, 1) = 3.0 -> +300%
        self.assertEqual(target_trend["growth"], 3.0)
        self.assertEqual(target_trend["growth_pct"], 300.0)
        self.assertTrue(target_trend["is_emerging"])

    def test_relevance_precheck_scoring(self):
        """Test keyword match pre-scoring logic."""
        art = {
            "title": "Autonomous AI Agents Deploy Enterprise Tools",
            "content": "Deep research into multi-agent workflows and reasoning."
        }
        score = compute_relevance_precheck(art, "Autonomous AI Agents", ["multi-agent", "workflows"])
        self.assertGreaterEqual(score, 70)

    def test_full_agent_12_step_execution(self):
        """Test complete 12-step autonomous agent execution pipeline with DB persistence."""
        t = Topic(name="Autonomous Agent Systems", keywords="reasoning, reflection, tool use", active=True)
        self.db.add(t)
        self.db.commit()

        agent = NewsMonitorAgent(topic_id=t.id, db_session=self.db, article_cap=4)
        result = agent.run()

        self.assertTrue(result["success"])
        self.assertEqual(len(result["steps"]), 12)
        self.assertGreaterEqual(result["articles_processed"], 1)

        # Verify database entities created
        stored_articles = self.db.query(Article).filter(Article.topic_id == t.id).all()
        self.assertGreaterEqual(len(stored_articles), 1)

        # Verify monitoring log entry created
        stored_log = self.db.query(MonitoringLog).filter(MonitoringLog.topic_id == t.id).first()
        self.assertIsNotNone(stored_log)
        self.assertEqual(stored_log.status, "Success")
        steps_list = stored_log.get_steps_list()
        self.assertEqual(len(steps_list), 12)

    def test_flask_routes_and_api(self):
        """Test Flask view rendering and API status endpoints."""
        res_dash = self.client.get("/")
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn(b"Topic Intelligence Command Center", res_dash.data)

        res_topics = self.client.get("/topics")
        self.assertEqual(res_topics.status_code, 200)

        res_articles = self.client.get("/articles")
        self.assertEqual(res_articles.status_code, 200)

        res_trends = self.client.get("/trends")
        self.assertEqual(res_trends.status_code, 200)
        self.assertIn(b"Growth = (Recent - Previous)", res_trends.data)

        res_health = self.client.get("/api/health")
        self.assertEqual(res_health.status_code, 200)
        data = json.loads(res_health.data)
        self.assertTrue(data["database_connected"])


if __name__ == "__main__":
    unittest.main()
