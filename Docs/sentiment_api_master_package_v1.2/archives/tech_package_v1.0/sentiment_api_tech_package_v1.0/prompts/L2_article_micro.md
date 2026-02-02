# L2 Article Micro Summary — Contract v1.0

## Input
- Article raw: `article_id`, `title_en`, `content_en`, `published_at`, `source_url`
- L1 facts (optional but recommended)

## Output (JSON ONLY)

### JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ArticleMicroL2",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "article_id": { "type": "string" },

    "headline_en": { "type": "string", "minLength": 1, "maxLength": 200 },

    "topics": {
      "type": "array",
      "minItems": 1,
      "maxItems": 12,
      "items": { "type": "string", "minLength": 1 }
    },

    "regions": {
      "type": "array",
      "maxItems": 12,
      "items": { "type": "string", "minLength": 2, "maxLength": 8 }
    },

    "tone": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "polarity": { "type": "number", "minimum": -1, "maximum": 1 },
        "subjectivity": { "type": "number", "minimum": 0, "maximum": 1 }
      },
      "required": ["polarity", "subjectivity"]
    },

    "key_claims_en": {
      "type": "array",
      "minItems": 1,
      "maxItems": 3,
      "items": { "type": "string", "minLength": 1, "maxLength": 220 }
    },

    "why_it_matters_en": {
      "type": "array",
      "minItems": 0,
      "maxItems": 2,
      "items": { "type": "string", "minLength": 1, "maxLength": 220 }
    },

    "entities": {
      "type": "array",
      "maxItems": 30,
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

    "uncertainty_flags": {
      "type": "array",
      "maxItems": 20,
      "items": { "type": "string", "minLength": 1 }
    },

    "evidence_refs": {
      "type": "array",
      "minItems": 1,
      "maxItems": 8,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "url": { "type": "string", "format": "uri" },
          "quote_en": { "type": "string", "minLength": 1, "maxLength": 240 }
        },
        "required": ["url", "quote_en"]
      }
    }
  },
  "required": [
    "article_id",
    "headline_en",
    "topics",
    "regions",
    "tone",
    "key_claims_en",
    "why_it_matters_en",
    "entities",
    "uncertainty_flags",
    "evidence_refs"
  ]
}
```

## Topic tagging rules
Use a stable taxonomy string set, e.g.:
- `rates`, `inflation`, `growth`, `fiscal`, `financial_stability`
- `geopolitics`, `sanctions`, `conflict`, `trade`, `energy`, `nuclear`, `disasters`

## Region tagging rules
- Use short tags: `US`, `EU`, `GB`, `CN`, `JP`, `GLOBAL`, etc.
- If unclear, use `GLOBAL` or omit.

