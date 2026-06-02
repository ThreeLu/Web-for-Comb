---
name: comb-search
version: 0.2
description: Fetch combinatorics arXiv paper data from Comb-Search
---

# Comb-Search Paper Data API

## Trigger
User wants to fetch combinatorics arXiv paper data from Comb-Search.

## Base URL
https://threelu.github.io/Web-for-Comb/

## URL Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `category` | arXiv category | `math.CO`, `math.NT`, `math.PR`, `cs.DM` |
| `author` | Author name | `Benny Sudakov` |
| `keywords` | Keywords (comma-separated) | `Hamilton,rainbow` |

## Filtering Logic

```
category AND (keywords OR author)
```

- `category`: Hard filter — only return papers in that category
- `keywords`: Searched in title and abstract (case-insensitive)
- `author`: Searched in author list (case-insensitive)
- `keywords` and `author` are combined with OR logic

## JSON Response

```json
{
  "category": "math.CO",
  "author": "Benny Sudakov",
  "keywords": ["Hamilton"],
  "count": 5,
  "papers": [
    {
      "id": "2401.00001",
      "title": "Paper Title",
      "authors": "Author 1, Author 2",
      "categories": ["math.CO"],
      "summary": "TL;DR summary",
      "date": "2024-01-01",
      "url": "https://arxiv.org/abs/2401.00001",
      "reason": "author: Benny Sudakov | keyword: Hamilton"
    }
  ]
}
```
