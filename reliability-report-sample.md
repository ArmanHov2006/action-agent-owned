<!-- FORMAT SAMPLE — NOT A RESULT.
     Generated from mock judge verdicts to show the shape of the report
     output, including the kappa + bootstrap CI line added in piece 10.
     The numbers below are fabricated. No model was called. Do not cite
     these as evidence of judge reliability. -->

# Judge reliability report

- Judge A: `gpt-4o-mini`
- Judge B: `gpt-4o`
- Agreement rate: 75%
- Disagreements: 2
- kappa: 0.53 [0.00, 1.00]

## Disagreements (where A and B split)

### 1. >=200 reviews and >=4.5 stars
- A (gpt-4o-mini): pass=True — 18.2K ratings, 4.6 stars — clears both thresholds
- B (gpt-4o): pass=False — rating is for the store page, not the product listing

### 2. >=200 reviews and >=4.5 stars
- A (gpt-4o-mini): pass=True — 312 reviews at 4.5 — meets the bar exactly
- B (gpt-4o): pass=False — 4.5 is rounded from 4.46; does not meet >=4.5
