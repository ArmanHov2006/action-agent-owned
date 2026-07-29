# action-agent-owned

An agent that acts, a judge that proves the agent's answer, and a harness that proves the judge.

The interesting part is not the agent loop. It is the three layers underneath it that decide whether an answer is *true*, and the statistics that say how much to trust the judge doing the deciding.

This is a re-derivation, by hand, of a system I had already shipped and could not explain. That constraint is the point of the repository — the goal was never a working agent, it was an agent I could defend line by line.

---

## The problem this exists to solve

A run finished. The agent reported a product with "18.2K reviews" against a goal requiring at least 200. The LLM judge's own written reason said both thresholds passed — and it emitted `"pass": false`.

The verdict token was generated, not forced by the inputs. A decidable arithmetic check had been handed to a predictor.

That single failure drives every design decision below.

---

## Design decisions

### Python owns the numbers, the LLM owns the judgment

The judge runs in layers. A deterministic gate decides the decidable thresholds first and short-circuits with no LLM cost on failure. Only if it passes does the model run, and it receives a whitelist-stripped view — `source_url` only — so `review_count` and `rating` never reach it. The final verdict is gate AND judgment.

The first attempt at this fix was a prompt instructing the model not to re-check numbers. It re-checked them anyway, under a "relevance" label.

**Withholding beats instructing.** Removing the numbers from context is the hard guarantee; a sentence in a system prompt is not.

### Provenance is layer 0, and it is default-deny

A row is grounded only if every numeric claim appears in the fetched page text. Ungrounded rows are dropped per row, and an entirely hallucinated run fails before the numeric gate and before any LLM call.

Three specifics that took a failing test each:

- **The raw text comes only from `role:"tool"` messages** — the actual fetched bytes. Assistant messages are excluded, so a number the model invents cannot ground itself against its own claim.
- **Word-boundary matching.** Substring matching grounded `50` inside `150`. That was committed as a deliberately failing test before it was fixed.
- **Same-domain gate.** A row survives only if its `source_url` host matches the fetched page host — otherwise correct numbers attributed to the wrong site pass as grounded.

### Rows are judged whole, and empty thresholds fail closed

Field extraction originally merged every row into one dictionary, last-write-wins. A weak later row — an accessory with 50 reviews — clobbered the real product's 18.2K and failed the gate on the wrong row.

Now each row is judged whole: the gate passes if any single row clears all thresholds on its own, and only the winning row's identity reaches the LLM layer.

Separately: a goal with no parseable thresholds fails closed. An empty constraint set is a parsing failure, not a free pass.

### The regression gate exits non-zero

The batch scorer runs the full judge over a labeled dataset, counts `verdict == expected`, and `sys.exit(1)` when correctness drops below a baseline. The baseline is injected as a parameter rather than read inside the scorer, which keeps the decision logic pure and testable.

A gate that only prints a number is not a gate.

### Cohen's κ, not raw agreement rate

Raw agreement overstates trust, because two judges agree by chance some of the time. κ subtracts that chance floor.

**Two lazy judges that pass everything agree 100% of the time and have measured nothing.** Exposing that is the entire reason this harness exists.

`p_e` is computed from each judge's own marginals rather than assuming they are equal.

One subtlety the harness bakes in: agreement only means anything on runs that actually *reach* the LLM. Provenance and gate short-circuits produce free deterministic agreement, which inflates the number while measuring nothing about judge behaviour. The test dataset is built to reach layer 2 for exactly this reason.

### Undefined κ is a branch, not an exception

On a single class, `p_e == 1`, κ is undefined, and the bootstrap raises. Returning `nan` is honest where returning `1.0` would be a lie.

The report branches on `math.isnan` before the call and prints `undefined` with the reason. The case is known and documented, so it is handled up front rather than caught after the fact. Before this, the report crashed outright on the most common real input: two judges that agree on everything.

### The bootstrap seed is fixed and not exposed

A report is an artifact that gets diffed and pasted into documents. Jitter between runs reads as a change when nothing has changed.

No caller needs a different seed today, so the parameter is not surfaced. It can be added when one does. Same reasoning for the resample count.

### Failures are classified before they are retried

Transient failures — 429, 5xx, network errors — retry up to three times with exponential backoff. Permanent failures — 401, 400 — raise immediately, because retrying cannot help. Exhausted retries raise into the loop's clean-abort path rather than spinning to max steps.

---

## What the numbers actually mean

`reliability-report-sample.md` is a **format sample** generated from mock verdicts, labelled as such in the file. It shows the shape of the output, not a reliability result.

It reports 75% agreement against a κ of 0.53 with a `[0.00, 1.00]` confidence interval — and that gap is itself the argument for shipping the interval. On eight rows the point estimate carries almost no information, and only the interval says so.

Reporting κ without an interval replaces one overconfident number with a second one.

---

## Layout

| File | What it holds |
|---|---|
| `main.py` | agent loop — model picks a tool, tool runs, result feeds back, repeat to finish or max steps |
| `llm.py` | OpenAI wire, error classification, retry with backoff |
| `tools.py` | `httpGet`, `askUser`, `finish` |
| `judge.py` | provenance filter (layer 0), deterministic threshold gate (layer 1), LLM judgment (layer 2), `cohen_kappa`, `kappa_bootstrap_ci` |
| `scorer.py` | batch scoring + the regression gate |
| `test_*.py` | 17 tests, offline — the judge seam is mocked, not the HTTP client |

## Running it

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=...
python main.py
pytest
```

---

## Provenance of this repository

Ten pieces, each rebuilt by hand and each held to the same bar before being counted: explain it cold, rebuild it from a blank file, and catch it if it were wrong.

Some commits carry a `Co-Authored-By: Claude` trailer from sessions where commits were made on my behalf. The code is hand-typed and the reasoning above is lifted from my own commit messages, but the trailers are left in place rather than rewritten, because an accurate history is worth more than a clean one.
