# Graph Report - .  (2026-07-24)

## Corpus Check
- 9 files · ~3,572 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 42 nodes · 61 edges · 8 communities detected
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 16 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]

## God Nodes (most connected - your core abstractions)
1. `provenance_filter()` - 8 edges
2. `judge_reliability()` - 8 edges
3. `full_judge()` - 6 edges
4. `judge()` - 4 edges
5. `cohen_kappa()` - 4 edges
6. `extract_fields()` - 3 edges
7. `collected_raw_from()` - 3 edges
8. `loop()` - 3 edges
9. `scorer_run()` - 3 edges
10. `test_report_renders_disagreement_reasons()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `provenance_filter()` --calls--> `test_substring_number_does_not_ground()`  [INFERRED]
  judge.py → test_provenance.py
- `provenance_filter()` --calls--> `test_offsite_source_url_dropped()`  [INFERRED]
  judge.py → test_provenance.py
- `provenance_filter()` --calls--> `test_same_domain_survives()`  [INFERRED]
  judge.py → test_provenance.py
- `provenance_filter()` --calls--> `test_scheme_differs_same_host_survives()`  [INFERRED]
  judge.py → test_provenance.py
- `full_judge()` --calls--> `scorer_run()`  [INFERRED]
  judge.py → scorer.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.36
Nodes (7): extract_fields(), full_judge(), judge(), judge_runs(), parse_thresholds(), reliability_report(), to_number()

### Community 1 - "Community 1"
Cohesion: 0.36
Nodes (7): domain_of(), _grounded_in(), provenance_filter(), test_offsite_source_url_dropped(), test_same_domain_survives(), test_scheme_differs_same_host_survives(), test_substring_number_does_not_ground()

### Community 2 - "Community 2"
Cohesion: 0.33
Nodes (4): ask(), collected_raw_from(), loop(), test_collected_raw_is_tool_only()

### Community 3 - "Community 3"
Cohesion: 0.53
Nodes (5): judge_reliability(), test_agreement_leaves_no_receipt(), test_disagreement_is_recorded(), test_empty_dataset_does_not_divide_by_zero(), test_report_renders_disagreement_reasons()

### Community 4 - "Community 4"
Cohesion: 0.5
Nodes (2): scorer_run(), test_scorer()

### Community 5 - "Community 5"
Cohesion: 0.67
Nodes (3): cohen_kappa(), test_kappa_known_value(), test_kappa_single_class_is_nan()

### Community 6 - "Community 6"
Cohesion: 0.67
Nodes (0): 

### Community 7 - "Community 7"
Cohesion: 1.0
Nodes (2): _run_reaching_llm(), test_reliability_tally_perfect_agreement_kappa()

## Knowledge Gaps
- **Thin community `Community 7`** (2 nodes): `_run_reaching_llm()`, `test_reliability_tally_perfect_agreement_kappa()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `judge_reliability()` connect `Community 3` to `Community 0`, `Community 5`, `Community 7`?**
  _High betweenness centrality (0.183) - this node is a cross-community bridge._
- **Why does `full_judge()` connect `Community 0` to `Community 1`, `Community 3`, `Community 4`?**
  _High betweenness centrality (0.176) - this node is a cross-community bridge._
- **Why does `provenance_filter()` connect `Community 1` to `Community 0`?**
  _High betweenness centrality (0.169) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `provenance_filter()` (e.g. with `test_substring_number_does_not_ground()` and `test_offsite_source_url_dropped()`) actually correct?**
  _`provenance_filter()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `judge_reliability()` (e.g. with `test_disagreement_is_recorded()` and `test_agreement_leaves_no_receipt()`) actually correct?**
  _`judge_reliability()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `cohen_kappa()` (e.g. with `test_kappa_known_value()` and `test_kappa_single_class_is_nan()`) actually correct?**
  _`cohen_kappa()` has 2 INFERRED edges - model-reasoned connections that need verification._