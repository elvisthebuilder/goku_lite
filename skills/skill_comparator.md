# [SKILL: SKILL COMPARATOR]
[DESCRIPTION: Judge which of two outputs (A or B) better accomplishes a task WITHOUT knowing which skill produced them. This prevents bias and ensures objective quality assessment.]

## Comparison Process:

### 1. Rubric-Based Scoring
Evaluate both outputs on a 1-10 scale across two dimensions:
- **Content Rubric**: Correctness, Completeness, Accuracy.
- **Structure Rubric**: Organization, Formatting, Usability.

### 2. Assertion Verification
If specific expectations (assertions) were provided:
- Check each assertion against both outputs.
- Calculate pass rates as secondary evidence.

### 3. Decisive Selection
- **The Winner**: Choose A, B, or TIE (Ties should be rare).
- **Primary Factor**: Overall rubric score.
- **Secondary Factor**: Assertion pass rate.
- **Reasoning**: Provide a clear, evidence-based explanation of why the winner was chosen.

## JSON Output Format:
Always produce a structured comparison JSON including:
- `winner`: The final decision.
- `reasoning`: Detailed justification.
- `rubric`: Scores for both A and B.
- `output_quality`: Strengths and weaknesses for both.
- `expectation_results`: Pass rates and details (if provided).

## Guidelines:
- **Stay Blind**: Do not try to guess which skill is which.
- **Be Decisive**: Pick the one that "fails less badly" if both are poor.
- **Cite Evidence**: Quote specific parts of the output in your reasoning.
