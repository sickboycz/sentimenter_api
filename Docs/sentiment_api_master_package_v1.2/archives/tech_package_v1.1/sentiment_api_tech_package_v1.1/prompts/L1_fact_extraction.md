# L1 Fact Extraction — Contract v1.0

## Input
- `article_id`
- `title_en`
- `content_en`
- `published_at` (UTC)
- `source_id`
- `source_url`

## Output (JSON ONLY)
Must conform to the schema below. Keep it minimal and evidence-based.

### JSON Schema (draft 2020-12)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ArticleFactsL1",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "article_id": { "type": "string" },
    "facts": {
      "type": "array",
      "maxItems": 50,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "fact": { "type": "string", "minLength": 1, "maxLength": 280 },
          "fact_type": {
            "type": "string",
            "enum": [
              "number",
              "date",
              "entity",
              "action",
              "policy",
              "sanction",
              "conflict",
              "other"
            ]
          },
          "entities": {
            "type": "array",
            "maxItems": 20,
            "items": {
              "type": "object",
              "additionalProperties": false,
              "properties": {
                "name": { "type": "string" },
                "entity_type": {
                  "type": "string",
                  "enum": ["person", "org", "country", "city", "commodity", "ticker", "other"]
                }
              },
              "required": ["name", "entity_type"]
            }
          },
          "evidence": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
              "url": { "type": "string", "format": "uri" },
              "quote_en": { "type": "string", "minLength": 1, "maxLength": 280 }
            },
            "required": ["url", "quote_en"]
          }
        },
        "required": ["fact", "fact_type", "entities", "evidence"]
      }
    },
    "uncertainty_flags": {
      "type": "array",
      "maxItems": 20,
      "items": { "type": "string", "minLength": 1 }
    }
  },
  "required": ["article_id", "facts", "uncertainty_flags"]
}
```

## Extraction rules
- Prefer concrete numbers and actions (who did what, when).
- If multiple claims conflict, include both with separate facts and add an uncertainty flag.
- Never invent tickers; only include if explicitly present.

