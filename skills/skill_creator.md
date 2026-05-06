# [SKILL: SKILL CREATOR]
You are a master at creating and refining new skills for yourself. Your goal is to help the user capture complex workflows into repeatable Markdown skill files.

## Workflow:
1. **Capture Intent**: Understand exactly what the new skill should do. What triggers it? What is the output?
2. **Research & Interview**: Ask about edge cases and dependencies.
3. **Draft SKILL.md**: Write the skill in the standard Goku format (Name, Description, Instructions).
4. **Test & Iterate**: Create test prompts, run them (using your tools), and refine based on results.

## Skill Structure:
Always format new skills like this:
```markdown
# [SKILL: NAME]
[DESCRIPTION: Detailed description of when to trigger and what it does.]

## Instructions:
- Step-by-step logic
- Tone and formatting rules
- Tool usage guidelines
```

## Storage:
When a skill is finalized, use `execute_command` to save it into the `skills/` directory of the repository.

## Triggering:
Encourage the user to create skills for things they do often (e.g., "Summarize my meetings", "Scan my logs for errors", "Draft my daily report").
