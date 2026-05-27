# Test Input Fixtures

## Files

- `sample.pdf`: 6-page academic-style fixture.
  - Page 1: text content only
  - Page 2: tabular content
  - Page 3: embedded image with related text
  - Pages 4-6: additional text content
- `sample_input.json`: valid serialized `RAGAgentInput` payload targeting `sample.pdf`.

## Notes

- The fixture is used for page-count, extraction, and end-to-end schema tests.
- Threshold filtering tests reuse the same input and override `relevance_threshold` to `1.0`.
- Baseline runtime (sample_input.json on local dev machine): 4.53 seconds end-to-end.
