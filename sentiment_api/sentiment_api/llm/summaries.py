"""M4 — Summaries L1-L4 (LLM or rule-based fallback)."""

import json
import logging
import os
from typing import Any

logger = logging.getLogger("sentiment_api.llm.summaries")


def _call_llm(system: str, user: str, model: str = "gpt-4o-mini") -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return ""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.1,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        logger.warning("LLM call failed: %s", e)
        return ""


def _extract_json(text: str) -> dict | None:
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return None


def summarize_l1(article_id: str, title_en: str, content_en: str, source_url: str, published_at: str) -> dict:
    """L1 fact extraction."""
    system = "Extract facts as JSON. Output ONLY valid JSON matching schema: article_id, facts (array of {fact, fact_type, entities, evidence}), uncertainty_flags."
    user = f"article_id={article_id}\ntitle={title_en}\ncontent={content_en[:3000]}\nurl={source_url}"
    out = _call_llm(system, user)
    if out:
        obj = _extract_json(out)
        if obj:
            obj.setdefault("article_id", article_id)
            obj.setdefault("facts", [])
            obj.setdefault("uncertainty_flags", [])
            return obj
    return {"article_id": article_id, "facts": [], "uncertainty_flags": []}


def summarize_l2(article_id: str, title_en: str, content_en: str, source_url: str, l1: dict | None = None) -> dict:
    """L2 article micro summary."""
    system = "Output JSON: headline_en, topics, regions, tone {polarity, subjectivity}, key_claims_en, why_it_matters_en, entities, uncertainty_flags, evidence_refs."
    user = f"article_id={article_id}\ntitle={title_en}\ncontent={content_en[:3000]}\nurl={source_url}"
    out = _call_llm(system, user)
    if out:
        obj = _extract_json(out)
        if obj:
            obj.setdefault("article_id", article_id)
            obj.setdefault("headline_en", title_en[:200])
            obj.setdefault("topics", ["general"])
            obj.setdefault("regions", [])
            obj.setdefault("tone", {"polarity": 0, "subjectivity": 0.5})
            obj.setdefault("key_claims_en", [])
            obj.setdefault("why_it_matters_en", [])
            obj.setdefault("entities", [])
            obj.setdefault("uncertainty_flags", [])
            obj.setdefault("evidence_refs", [{"url": source_url, "quote_en": title_en[:240]}])
            return obj
    return {
        "article_id": article_id,
        "headline_en": title_en[:200] or "Untitled",
        "topics": ["general"],
        "regions": [],
        "tone": {"polarity": 0, "subjectivity": 0.5},
        "key_claims_en": [],
        "why_it_matters_en": [],
        "entities": [],
        "uncertainty_flags": [],
        "evidence_refs": [{"url": source_url, "quote_en": (title_en or content_en[:100])[:240]}],
    }


def summarize_l3(
    cluster_id: str,
    articles: list[dict],
    evidence: list[dict],
) -> dict:
    """L3 cluster summary."""
    text = "\n".join(
        f"- {a.get('headline_en','')}: {a.get('key_claims_en',[])[:2]}"
        for a in articles[:5]
    )
    system = "Output JSON: headline_en, summary_bullets_en, what_changed_en, why_it_matters_en, what_to_watch_en, topics, regions, channels, evidence, uncertainty_flags."
    user = f"cluster_id={cluster_id}\narticles:\n{text[:2000]}"
    out = _call_llm(system, user)
    if out:
        obj = _extract_json(out)
        if obj:
            obj.setdefault("cluster_id", cluster_id)
            obj.setdefault("headline_en", articles[0].get("headline_en", "Cluster") if articles else "Cluster")
            obj.setdefault("summary_bullets_en", [])
            obj.setdefault("what_changed_en", "")
            obj.setdefault("why_it_matters_en", "")
            obj.setdefault("what_to_watch_en", "")
            obj.setdefault("topics", [])
            obj.setdefault("regions", [])
            obj.setdefault("channels", [])
            obj.setdefault("evidence", evidence[:5])
            obj.setdefault("uncertainty_flags", [])
            return obj
    headline = articles[0].get("headline_en", "Cluster") if articles else "Cluster"
    return {
        "cluster_id": cluster_id,
        "headline_en": headline[:200],
        "summary_bullets_en": [headline[:240]],
        "what_changed_en": "",
        "why_it_matters_en": "",
        "what_to_watch_en": "",
        "topics": [],
        "regions": [],
        "channels": [],
        "evidence": evidence[:5],
        "uncertainty_flags": [],
    }


def summarize_l4(cluster_id: str, state_key: str, prev_state: str | None, l3: dict) -> dict:
    """L4 narrative state delta."""
    return {
        "cluster_id": cluster_id,
        "state_key": state_key,
        "prev_state_en": prev_state,
        "new_state_en": l3.get("what_changed_en", "")[:200] or l3.get("headline_en", ""),
        "change_direction": "sideways",
        "change_confidence": 0.5,
        "supporting_clusters": [cluster_id],
        "notes_en": "",
    }
