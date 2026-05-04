# 🎓 Lesson 06: The Next Detector - ASI01 Goal Hijack Scaffold

## 🛡️ Welcome Back, Threat Modeler

Goal: understand the ASI01 scaffold, why it is not implemented yet, and how it differs from ASI06.

Time estimate: 30 minutes

Prerequisites:

- Complete Lessons 00-05.
- Understand the current ASI06 detector path.
- Know that ASI01 runtime logic is intentionally not shipped yet.

Why this matters: good architecture is knowing what not to build too early. ASI01 is harder than ASI06 because it is behavioral and semantic, not just content-pattern matching.

## 1. Introduction Section

### Learning objectives

- Explain the ASI01 threat model.
- Distinguish ASI01 goal hijack from ASI06 job-content injection.
- Identify required evidence fields for future ASI01 findings.
- Explain why Layer 4 semantic analysis is primary for ASI01.
- Describe the trigger for building ASI01 runtime code.
- Avoid overclaiming scaffolded work as implemented detection.

### Plain-English explanation

ASI01 asks: "Did untrusted content redirect the agent away from the user's goal?" That is harder than "Did this text match a known-bad string?" because you must compare intended goal, external instruction, and actual agent behavior.

Analogy: ASI06 is a security guard spotting a fake badge. ASI01 is an investigator checking whether someone convinced the guard to abandon their post.

### Project implements

- Rule spec: `detections/asi01_goal_hijack/ASI01-001.md`
- README: `detections/asi01_goal_hijack/README.md`
- Status: scaffold only.
- Detection layer decision: semantic and behavioral primary.

### Recommended (not implemented here)

- Deterministic policy checks comparing action outcome to allowed goals.
- Semantic guardrail judge for ambiguous goal changes.
- Prompt quarantine when external content contains agent-directed instructions.
- Cross-rule correlation from ASI06 evidence to ASI01 attempted goal redirection.

## 2. Key Concepts Section

### Terms

| Term | Meaning |
|---|---|
| Goal hijack | External content redirects the agent's objective. |
| Intended goal | The configured user-approved task. |
| Attempted goal | What untrusted content wants the agent to do instead. |
| Behavioral deviation | The agent acts outside the approved workflow. |
| Seed indicator | A regex or ASI06 finding that suggests semantic review may be needed. |

### Current ASI01 contrast

Project implements:

- ASI01 documentation says regex is only a seed.
- ASI01 requires evidence such as intended goal, attempted goal, source field, and related ASI06 rule.
- Runtime ASI01 waits for a live redirect signal or ASI06 prompt-injection event.

Recommended (not implemented here):

- LLM-as-judge prompt with strict schema output.
- Human review queue for high-risk goal redirection.
- Policy engine that compares proposed action to allowed action set.

## 3. Code Walkthrough Section

### Rule header

File: `detections/asi01_goal_hijack/ASI01-001.md`

```text
Status: Rule stub
Rule ID: ASI01-001
Name: External Content Goal Redirection
OWASP mapping: ASI01 - Goal Hijacking and Instruction Override
Severity: HIGH
Detection layer: Layer 4 semantic and behavioral analysis primary; Layer 1 regex only for seed indicators
Current runtime location: Not implemented; scaffold only
```

What it does:

1. Makes the status explicit.
2. Maps the rule to OWASP ASI01.
3. States the detection layer decision.
4. Prevents readers from mistaking scaffold for runtime code.

### Trigger condition

File: `detections/asi01_goal_hijack/ASI01-001.md`

```text
Trigger when untrusted content or observed agent output indicates that the agent's behavior is being redirected away from the user's intended goal.
```

Why: ASI01 is not just malicious text. It is malicious text plus possible goal impact.

### Evidence requirements

File: `detections/asi01_goal_hijack/ASI01-001.md`

```text
- intended_goal
- attempted_goal
- evidence.matched_text
- evidence.snippet
- related_asi06_rule_id when the signal came from ASI06 content detection
```

Why: future ASI01 findings need to explain what the agent was supposed to do and what the attack tried to make it do instead.

## 4. Hands-On Exercises Section

### 🧪 Exercise 1: Read the ASI01 spec

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
Get-Content detections\asi01_goal_hijack\ASI01-001.md | Select-Object -First 40
```

Expected output begins:

```text
# ASI01-001: External Content Goal Redirection

Status: Rule stub
Rule ID: ASI01-001
```

### 🧪 Exercise 2: Confirm ASI01 is not a runtime module yet

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
Test-Path detections\asi01_goal_hijack\detector.py
```

Expected output:

```text
False
```

### 🧪 Exercise 3: Find ASI01 references

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
Select-String -Path README.md,PHASE1_PROGRESS.md,detections\asi01_goal_hijack\ASI01-001.md -Pattern "ASI01|semantic|behavioral"
```

Expected output includes:

```text
ASI01
semantic
behavioral
```

### 🧪 Exercise 4: Intentional overclaim check

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
Select-String -Path detections\asi01_goal_hijack\ASI01-001.md -Pattern "Not implemented; scaffold only"
```

Expected output:

```text
Current runtime location: Not implemented; scaffold only
```

Why: this keeps interview language honest.

## 5. Interview Preparation Section

**Q: Why is ASI01 harder than ASI06?**

**A:** ASI06 can often start with deterministic content checks like "ignore previous instructions." ASI01 requires judging whether external content or agent output changed the agent's goal. That needs behavioral context and often semantic analysis.

**Q: Why not implement ASI01 immediately?**

**A:** The project has ASI06 evidence and clean baselines, but no live goal-redirect event yet. Building ASI01 too early risks theoretical rules with poor signal. The scaffold documents the design while waiting for real evidence.

**Q: How would you implement ASI01 first?**

**A:** Start by correlating ASI06 prompt-injection findings with intended goal, attempted goal, and observed action outcome. Use deterministic policy checks first, then add semantic review for ambiguous cases.

## 6. Key Takeaways Section

- ASI01 is scaffolded, not runtime implemented.
- It is semantic and behavioral first.
- Regex should seed review, not be the primary ASI01 engine.
- Future ASI01 should reuse ASI06 evidence and session correlation.
- Honest status labeling is part of good engineering.

## 7. Summary Reference Card

| Item | Details |
|---|---|
| Rule spec | `detections/asi01_goal_hijack/ASI01-001.md` |
| Runtime module | Not present yet |
| Primary layer | Layer 4 semantic and behavioral analysis |
| Seed layer | Layer 1 regex indicators |
| Future evidence | `intended_goal`, `attempted_goal`, `related_asi06_rule_id` |
| Build trigger | Live redirect signal or ASI06 prompt-injection event |

## 8. Next Steps

Next module to study: ASI01 `detector.py`. Optional advanced topic: design a policy schema that defines allowed OpenClaw actions during maintenance mode.

Remember: the best detector roadmap says what is implemented and what is not. 🛡️
