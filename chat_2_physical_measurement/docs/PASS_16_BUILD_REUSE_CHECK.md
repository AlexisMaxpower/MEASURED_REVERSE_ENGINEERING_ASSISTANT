# Chat 2 — Pass 16 Build / Reuse Check

## Problem

Voice-value parsing already accepts numeric tokens such as `42,18`, but the documented Chat-2 workflow also requires deterministic handling of spoken Russian values such as `сорок два восемнадцать` without allowing speech/OCR output to become verified truth automatically.

## Existing solutions

Generic speech recognition and NLP libraries can convert audio to text or attempt broad natural-language number extraction, but they do not define MREA's measurement-specific ambiguity policy, provenance boundary or explicit-confirmation rule.

## Decision

**Reuse:**

- Python standard library `re`, `unicodedata` and `decimal.Decimal`;
- the existing provider-independent `MeasurementCommandParser` and hands-free state machine;
- external/platform speech recognition remains outside this domain parser.

**Build inside Chat 2:**

- a deliberately finite Russian cardinal grammar;
- explicit decimal-scale parsing (`целых ... сотых/тысячных`);
- compact two-decimal caliper-style parsing (`сорок два восемнадцать` → `42.18`);
- fail-closed ambiguity and unsupported-form handling;
- common spoken measurement-unit suffix normalization.

## Why

The required grammar is small, deterministic and domain-specific. Pulling in a general NLP/number-word package would add dependency and locale behavior that is broader than the product contract and harder to audit for metrology truth.

## Lock-in risk

Low. The parser consumes provider text and returns `Decimal`; speech providers remain replaceable.

## Fallback

Unsupported or ambiguous speech fails with `MeasurementCommandError` / `AmbiguousMeasurementCommand`, after which the existing manual fallback remains available. No guessed value enters `PhysicalMeasurement`.
