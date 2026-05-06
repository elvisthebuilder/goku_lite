# [SKILL: SKILL ANALYZER]
[DESCRIPTION: Analyze blind comparison results and benchmark data to understand WHY one skill version performed better than another. Use this to iteratively refine skills based on evidence.]

## Analysis Process:

### 1. Blind Comparison (A vs B)
- **Unblind the Results**: Examine the winner and loser skills and their execution transcripts.
- **Identify Differences**: Look for clarity of instructions, tool usage patterns, and example coverage.
- **Instruction Following**: Score the agent 1-10 on how well it adhered to the skill. Note where it diverged or improvised.
- **Winner Strengths**: Quote specific instructions or tools that made the winner better.
- **Loser Weaknesses**: Identify the exact ambiguities or missing tools that caused the failure.

### 2. Improvement Suggestions
- **Categorize**: Group suggestions into `instructions`, `tools`, `examples`, or `error_handling`.
- **Prioritize**: Mark changes as `high`, `medium`, or `low` based on whether they would have changed the outcome.
- **Actionable**: Suggestions must be concrete code or prose changes, not vague advice.

### 3. Benchmark Pattern Recognition
- **Aggregate Analysis**: Look for assertions that always pass (non-discriminating) or always fail (beyond capability).
- **Resource Usage**: Identify if a skill adds too much execution time or token cost for the value it provides.
- **Flakiness**: Flag evals with high variance across runs.

## JSON Analysis Format:
When asked for a formal analysis, produce a structured report including:
- `comparison_summary`: Who won and why.
- `winner_strengths` & `loser_weaknesses`: Bulleted insights.
- `instruction_following`: Detailed scoring for both.
- `improvement_suggestions`: Actionable steps with expected impact.
- `transcript_insights`: Step-by-step execution patterns.
