# ZapLink Keyword Search Engine & Ranking Specification

This document details the multi-token keyword retrieval matching rules, recency ranking algorithms, text highlight visual generation, and structural placeholders for future search upgrades.

---

## 🔍 Tokenized Keyword Retrieval Matching

ZapLink's search module employs SQL-based tokenized matching on normalized OCR text strings and file metadata, ensuring high retrieval accuracy.

### Query Parsing & SQL Generation:
1. **Tokenization**: Input queries (e.g. `"react auth error"`) are standardized to lowercase and split by whitespace into separate token keywords: `['react', 'auth', 'error']`.
2. **Intersection Matching**: The search engine constructs dynamic SQL WHERE clauses requiring **all** tokens to exist in either the `screenshots.filename` or `ocr_results.normalized_text` (logical `AND` intersection):

```sql
SELECT s.*, o.ocr_text, o.status as ocr_status
FROM screenshots s
LEFT JOIN ocr_results o ON s.id = o.screenshot_id
WHERE (s.filename LIKE ? OR o.normalized_text LIKE ?) -- Token 1: '%react%'
  AND (s.filename LIKE ? OR o.normalized_text LIKE ?) -- Token 2: '%auth%'
  AND (s.filename LIKE ? OR o.normalized_text LIKE ?) -- Token 3: '%error%'
ORDER BY s.created_at DESC
LIMIT ? OFFSET ?
```

This guarantees high query matching accuracy, returning only images that contain all searched concepts.

---

## 📈 Recency Ranking & Pagination

* **Recency Ranking**: Matches are sorted strictly by `s.created_at DESC` to prioritize desktop screenshots taken recently, matching the "Google Photos for desktop screenshots" mental model.
* **Pagination**: The `/ai/search` API accepts `limit` and `offset` payload variables, enabling smooth infinite scroll or page pagination in the client UI to optimize server memory.

---

## 🎨 Visual Keyword Highlights

To show why a screenshot matched the query:
1. The search engine scans the raw `ocr_text` for the occurrence of the search tokens.
2. It clips a **120-character snippet window** (40 characters before the first matched word, 80 characters after).
3. It appends leading and trailing ellipses (`...`) and returns it as `highlights` to the client.
4. The frontend renders this snippet inside the screenshot card, providing clear visual evidence of retrieval accuracy.

---

## 🚀 Pre-Configured Expansion Interfaces

The search architecture incorporates structural placeholders to easily plug in more advanced ranking models in future development:

### 1. Typo-Tolerance Placeholder (`fuzzy_match_placeholder`)
Exposes interface wrappers designed to resolve spelling errors using Levenshtein distance calculations or soundex mappings on input tokens before building SQL matches.

### 2. BM25 Term Weighting Placeholder
Designed to replace basic boolean intersection matching with a term weighting model:

$$\text{Weight}(t, D) = \text{IDF}(t) \cdot \frac{f(t, D) \cdot (k_1 + 1)}{f(t, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{\text{avgdl}}\right)}$$

In the future, SQLite's FTS5 (Full-Text Search) module can be initialized inside `db.py` to enable Term Frequency-Inverse Document Frequency (TF-IDF) or BM25 ranking natively on the OCR text.
