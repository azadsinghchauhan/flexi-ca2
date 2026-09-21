import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import difflib

# Tracking query parameters commonly found in news and analytics links
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "mc_cid", "mc_eid", "ref", "source", "cmpid"
}

def clean_canonical_url(url: str) -> str:
    """
    Layer 1: Canonical URL Normalization.
    Strips tracking query parameters, fragments, trailing slashes, and lowercases hostname.
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        
        # Filter tracking parameters
        query_dict = parse_qs(parsed.query, keep_blank_values=False)
        clean_params = {k: v for k, v in query_dict.items() if k.lower() not in TRACKING_PARAMS}
        
        # Re-sort query params for canonical consistency
        sorted_query = urlencode(clean_params, doseq=True)
        path = parsed.path.rstrip("/")
        
        # Build canonical representation (discard fragment)
        canonical = urlunparse((
            parsed.scheme.lower() or "https",
            netloc,
            path,
            "",
            sorted_query,
            ""
        ))
        return canonical
    except Exception:
        return url.strip().lower().rstrip("/")

def normalize_title(title: str) -> str:
    """
    Layer 2: Normalized Title Representation.
    Lowercases, strips punctuation, numbers/symbols, and collapses whitespace.
    """
    if not title:
        return ""
    # Lowercase
    cleaned = title.lower()
    # Remove common news publisher suffixes (e.g. " - TechCrunch", " | Reuters")
    cleaned = re.sub(r"\s*[-|–—]\s*[^–—|-]+$", "", cleaned)
    # Strip non-alphanumeric chars
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def calculate_token_jaccard_similarity(title_a: str, title_b: str) -> float:
    """
    Layer 3: Title Token Jaccard Similarity.
    Computes intersection over union of word tokens.
    Jaccard(A, B) = |A ∩ B| / |A ∪ B|
    """
    norm_a = normalize_title(title_a)
    norm_b = normalize_title(title_b)
    
    tokens_a = set(norm_a.split())
    tokens_b = set(norm_b.split())
    
    if not tokens_a or not tokens_b:
        return 0.0
    
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    
    if not union:
        return 0.0
    
    jaccard = len(intersection) / len(union)
    
    # Also calculate SequenceMatcher ratio as a secondary check for rephrased titles
    seq_ratio = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()
    return max(jaccard, seq_ratio)

def is_duplicate_article(candidate, existing_articles, similarity_threshold: float = 0.75):
    """
    Evaluates a candidate article against a collection of existing articles using
    the 3-layer explainable duplicate detection hierarchy:
    1. Canonical URL match
    2. Normalized exact title match
    3. Token Jaccard / Sequence similarity >= threshold
    
    Returns: (is_duplicate: bool, layer_reason: str or None, matched_article_title: str or None)
    """
    cand_url = clean_canonical_url(candidate.get("url") or candidate.get("canonical_url", ""))
    cand_norm_title = normalize_title(candidate.get("title", ""))

    for item in existing_articles:
        item_url = clean_canonical_url(item.get("url") or item.get("canonical_url", ""))
        item_title = item.get("title", "")
        item_norm_title = normalize_title(item_title)

        # Layer 1: Canonical URL
        if cand_url and item_url and cand_url == item_url:
            return True, "Layer 1: Canonical URL Match", item_title

        # Layer 2: Exact Normalized Title
        if cand_norm_title and item_norm_title and cand_norm_title == item_norm_title:
            return True, "Layer 2: Normalized Title Match", item_title

        # Layer 3: Token Similarity
        sim = calculate_token_jaccard_similarity(candidate.get("title", ""), item_title)
        if sim >= similarity_threshold:
            return True, f"Layer 3: Token Similarity ({int(sim * 100)}% >= {int(similarity_threshold * 100)}%)", item_title

    return False, None, None
