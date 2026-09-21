import os
import re
import random
import datetime
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv
from services.deduplicator import clean_canonical_url

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")

# Mock news templates for realistic academic / viva demonstration across domains
DEMO_NEWS_ARCHIVE = [
    {
        "domain": "ai",
        "title": "Autonomous AI Agents Achieve Breakthrough in Multi-Step Workflow Orchestration",
        "url": "https://techcrunch.com/2026/03/18/autonomous-ai-agents-breakthrough-orchestration?utm_source=rss",
        "source": "TechCrunch",
        "content": "Researchers have demonstrated autonomous agentic architectures operating with dynamic tool usage, reflection loops, and self-correcting memory. The benchmark results indicate a 40% reduction in workflow errors compared to linear chains.",
        "days_ago": 1
    },
    {
        "domain": "ai",
        "title": "Groq and Open Source LLM Acceleration Shift Cloud AI Unit Economics",
        "url": "https://venturebeat.com/ai/groq-open-source-llm-acceleration-cloud-shift?ref=newsfeed",
        "source": "VentureBeat",
        "content": "LPU hardware accelerators combined with optimized open weights models are enabling sub-second inference at one-tenth the energy footprint, prompting enterprise infrastructure migration.",
        "days_ago": 2
    },
    {
        "domain": "ai",
        "title": "Regulatory Scrutiny Intensifies Over Autonomous Agent Decision-Making Systems",
        "url": "https://www.reuters.com/technology/regulatory-scrutiny-intensifies-autonomous-agents-2026-03-15/",
        "source": "Reuters",
        "content": "European and US regulators published joint guidance demanding explainable audit trails and deterministic boundaries for autonomous AI systems deployed in financial and healthcare operations.",
        "days_ago": 3
    },
    {
        "domain": "ai",
        "title": "Multimodal Agent Frameworks Unify Computer Vision and Structured Reasoning",
        "url": "https://www.technologyreview.com/2026/03/12/multimodal-agent-frameworks-vision-reasoning/",
        "source": "MIT Technology Review",
        "content": "Next-generation vision-language agents can now inspect user interfaces, parse live telemetry, and trigger corrective code adjustments across complex software ecosystems.",
        "days_ago": 4
    },
    {
        "domain": "ai",
        "title": "Enterprise RAG and Agentic Knowledge Retrieval Move Beyond Vector Search",
        "url": "https://www.wired.com/story/enterprise-rag-agentic-retrieval-knowledge-graphs/",
        "source": "Wired",
        "content": "Hybrid architectures integrating knowledge graphs with autonomous query expansion are replacing simplistic cosine-similarity vector databases for mission-critical enterprise intelligence.",
        "days_ago": 5
    },
    {
        "domain": "quantum",
        "title": "Quantum Error Correction Reaches Commercial Fault-Tolerance Milestones",
        "url": "https://www.nature.com/articles/s41586-quantum-error-correction-fault-tolerance",
        "source": "Nature Electronics",
        "content": "Physicists have sustained logical qubits with surface codes that actively correct bit-flip and phase errors, passing the critical threshold required for scalable quantum advantage.",
        "days_ago": 1
    },
    {
        "domain": "quantum",
        "title": "NIST Issues Final Post-Quantum Cryptography Migration Guidelines",
        "url": "https://www.securityweek.com/nist-issues-final-pqc-migration-guidelines?cmpid=nl",
        "source": "SecurityWeek",
        "content": "Federal cybersecurity directives mandate organizations begin retiring legacy RSA-2048 encryption in favor of lattice-based algorithms to thwart future quantum decryption attacks.",
        "days_ago": 3
    },
    {
        "domain": "quantum",
        "title": "Semiconductor Giants Unveil Cryogenic CMOS Control Chips for Quantum Processors",
        "url": "https://spectrum.ieee.org/cryogenic-cmos-quantum-control-silicon",
        "source": "IEEE Spectrum",
        "content": "Engineers developed silicon control circuits operating at 4 Kelvin, eliminating the bulky coaxial cabling that previously constrained dilution refrigerator scaling.",
        "days_ago": 6
    },
    {
        "domain": "energy",
        "title": "Next-Gen Solid-State Battery Chemistry Enters Pilot Production Phase",
        "url": "https://arstechnica.com/science/solid-state-battery-pilot-production-2026/",
        "source": "Ars Technica",
        "content": "Automotive battery developers reported achieving 450 Wh/kg energy density with zero dendrite formation across 1,000 rapid charging cycles using sulfide-based solid electrolytes.",
        "days_ago": 2
    },
    {
        "domain": "energy",
        "title": "Grid-Scale Sodium-Ion Energy Storage Outpaces Lithium in Cost Benchmarks",
        "url": "https://www.bloomberg.com/news/articles/grid-scale-sodium-ion-cost-advantages",
        "source": "Bloomberg Energy",
        "content": "Abundant mineral supply chains and lower thermal runaway risks have accelerated the adoption of sodium-ion battery arrays for renewable grid balancing across major energy operators.",
        "days_ago": 5
    }
]


def build_search_queries(topic_name: str, keywords: list) -> list:
    """
    Step 2: Build targeted search queries from topic and keywords.
    Produces high-precision Boolean and topical search strings.
    """
    queries = []
    clean_kw = [k.strip() for k in keywords if k.strip()]
    
    # Primary topical query
    queries.append(f"{topic_name} news recent developments")
    
    # Keyword combination queries
    if clean_kw:
        top_kws = clean_kw[:3]
        queries.append(f"{topic_name} {' '.join(top_kws)}")
        
        # Emerging / trend query
        queries.append(f"{top_kws[0]} breakthrough trends 2026")
        
    return queries[:3]


def fetch_from_tavily(query: str, max_results: int = 8) -> list:
    """
    Step 3: Query Tavily News Search API.
    """
    if not TAVILY_API_KEY:
        return []

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "topic": "news",
        "days": 7,
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False
    }

    try:
        response = requests.post(url, json=payload, timeout=12)
        if response.status_code == 200:
            data = response.json()
            return data.get("results", [])
        else:
            print(f"[WARN] Tavily API error {response.status_code}: {response.text}")
            return []
    except Exception as e:
        print(f"[ERROR] Failed to query Tavily API: {e}")
        return []


def generate_mock_articles(topic_name: str, keywords: list, count: int = 8) -> list:
    """
    Generates realistic, structured mock news articles for testing, demo mode,
    or whenever Tavily API key is not configured.
    """
    now = datetime.datetime.utcnow()
    results = []

    # Identify matching domain or synthesize
    topic_lower = topic_name.lower() + " " + " ".join(keywords).lower()
    
    selected_pool = []
    for item in DEMO_NEWS_ARCHIVE:
        if item["domain"] in topic_lower or any(k.lower() in item["title"].lower() for k in keywords):
            selected_pool.append(item)
    
    # If no specific match, use general pool
    if not selected_pool:
        selected_pool = DEMO_NEWS_ARCHIVE.copy()
        
    # Shuffle or cycle to satisfy count
    sample_items = selected_pool * 2
    for i, item in enumerate(sample_items[:count]):
        # Add slight variation if needed
        art_title = item["title"]
        if i >= len(selected_pool):
            art_title = f"Follow-up: {art_title} [Market Impact]"
            
        pub_date = now - datetime.timedelta(days=item.get("days_ago", random.randint(1, 6)), hours=random.randint(1, 12))
        
        results.append({
            "title": art_title,
            "url": item["url"],
            "source": item["source"],
            "published_date": pub_date.isoformat(),
            "content": item["content"],
            "is_demo": True
        })

    return results


def normalize_article_payload(raw_item: dict, default_source: str = "Online News") -> dict:
    """
    Step 4: Normalize raw article fields (title, url, source, published date, content snippet).
    """
    title = (raw_item.get("title") or "Untitled Article").strip()
    url = (raw_item.get("url") or "").strip()
    canonical_url = clean_canonical_url(url)
    
    # Source extraction
    source = raw_item.get("source")
    if not source and url:
        try:
            domain = urlparse(url).netloc
            source = domain.replace("www.", "")
        except Exception:
            source = default_source
    if not source:
        source = default_source

    # Date normalization
    raw_date = raw_item.get("published_date") or raw_item.get("publishedAt") or raw_item.get("published")
    published_at = datetime.datetime.utcnow()
    if raw_date:
        try:
            if isinstance(raw_date, str):
                # Try common formats
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                    try:
                        published_at = datetime.datetime.strptime(raw_date[:19], fmt[:len(raw_date[:19])])
                        break
                    except Exception:
                        pass
        except Exception:
            published_at = datetime.datetime.utcnow()

    # Content snippet normalization
    raw_content = raw_item.get("content") or raw_item.get("snippet") or raw_item.get("summary") or ""
    # Strip HTML tags
    cleaned_content = re.sub(r"<[^>]+>", "", raw_content)
    cleaned_content = re.sub(r"\s+", " ", cleaned_content).strip()

    return {
        "title": title,
        "url": url,
        "canonical_url": canonical_url,
        "source": source.strip(),
        "published_at": published_at,
        "content": cleaned_content,
        "is_demo": raw_item.get("is_demo", False)
    }


def compute_relevance_precheck(article: dict, topic_name: str, keywords: list) -> int:
    """
    Step 5: Relevance pre-check score (0 to 100).
    Evaluates keyword matches in title and content snippet.
    - Title match carries 60% weight.
    - Snippet match carries 40% weight.
    """
    title = article.get("title", "").lower()
    content = article.get("content", "").lower()
    
    tokens = [topic_name.lower()] + [k.lower() for k in keywords if k.strip()]
    if not tokens:
        return 50

    matches_in_title = 0
    matches_in_content = 0

    for tok in tokens:
        # Check whole word or substring
        if tok in title:
            matches_in_title += 1
        if tok in content:
            matches_in_content += 1

    total_tokens = max(len(tokens), 1)
    title_score = min(1.0, (matches_in_title / total_tokens) * 1.5)
    content_score = min(1.0, (matches_in_content / total_tokens) * 1.2)

    # Base baseline of 35 so slightly related articles aren't discarded before AI evaluation
    final_score = int(35 + (title_score * 40) + (content_score * 25))
    return min(100, max(0, final_score))
