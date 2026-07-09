# Graph Report - .  (2026-07-09)

## Corpus Check
- 3 files · ~264 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 6 nodes · 4 edges · 3 communities detected
- Extraction: 75% EXTRACTED · 25% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]

## God Nodes (most connected - your core abstractions)
1. `ask()` - 2 edges
2. `loop()` - 2 edges

## Surprising Connections (you probably didn't know these)
- `loop()` --calls--> `ask()`  [INFERRED]
  main.py → llm.py

## Communities

### Community 0 - "Community 0"
Cohesion: 1.0
Nodes (1): ask()

### Community 1 - "Community 1"
Cohesion: 1.0
Nodes (1): loop()

### Community 2 - "Community 2"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **Thin community `Community 0`** (2 nodes): `ask()`, `llm.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 1`** (2 nodes): `loop()`, `main.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 2`** (2 nodes): `httpGet()`, `tools.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ask()` connect `Community 0` to `Community 1`?**
  _High betweenness centrality (0.200) - this node is a cross-community bridge._
- **Why does `loop()` connect `Community 1` to `Community 0`?**
  _High betweenness centrality (0.200) - this node is a cross-community bridge._