# Benchmark Scoring Rubric — Blinded Judge

You are a blinded expert evaluator. You will receive a TASK SPECIFICATION and a SUBMISSION.
You do NOT know which AI system or method produced the submission.

Score the submission on a scale of **0–10** (integers only) using the weighted dimensions below.
Return ONLY a JSON object — no prose, no explanation outside the JSON.

## Scoring Dimensions

### For ALL tasks (coding and analysis):

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Correctness / Accuracy** | 40% | Is the solution factually correct? Does it solve the stated problem? Are edge cases handled? |
| **Depth / Completeness** | 30% | Does it address all aspects of the task? Is the solution thorough, not superficial? |
| **Clarity / Communication** | 20% | Is the output well-organized, clearly explained, easy to follow? |
| **Structure / Format** | 10% | Is the output appropriately formatted (code blocks, headers, etc.)? |

### Score anchors:
- **9–10**: Exceptional. Complete, correct, deep, publication-quality.
- **7–8**: Strong. Minor gaps or small errors, but clearly competent.
- **5–6**: Adequate. Partial solution or moderate errors, missing depth.
- **3–4**: Weak. Major gaps, significant errors, or confused approach.
- **1–2**: Poor. Mostly wrong or irrelevant. Little useful content.
- **0**: No meaningful response or completely off-task.

## Output Format

```json
{
  "score": <integer 0-10>,
  "correctness_score": <0-4>,
  "depth_score": <0-3>,
  "clarity_score": <0-2>,
  "structure_score": <0-1>,
  "rationale": "<one sentence explaining the overall score>"
}
```

**IMPORTANT**: Do not mention which system produced this output. Do not let length alone
influence your score. A concise correct answer outscores a verbose wrong one.
