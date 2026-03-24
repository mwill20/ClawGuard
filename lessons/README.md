# Lessons

Teaching-oriented documentation built alongside the project. Each entry captures real insights from building ClawGuard — not theoretical, but grounded in actual deployment experience.

These are designed to be LinkedIn-ready articles and interview talking points.

## Planned Entries

| # | Title | Status |
|---|---|---|
| 1 | What Job Site Bot Detection Teaches Us About AI Agent Security Monitoring | 🔲 Draft |
| 2 | Skill Supply Chain Security: Why We Write Our Own OpenClaw Skills | 🔲 Draft |

## Entry 1 Preview: Bot Detection ↔ Agent Monitoring

Job platform anti-bot techniques map directly to AI agent security monitoring patterns:

| Job Site Technique | ClawGuard Equivalent |
|---|---|
| Speed detection | Agent behavioral velocity monitoring |
| Behavioral analysis (mouse patterns, click timing) | Agent action pattern analysis |
| Browser fingerprinting | Agent identity/provenance verification |
| Rate limiting / account flagging | Agent rate anomaly detection |
| CAPTCHA / human verification | Human-in-the-loop checkpoints |

## Entry 2 Preview: Skill Supply Chain Security

The February 2026 ClawHavoc attack poisoned OpenClaw's ClawHub with 1,184 malicious skills. Our decision to write custom skills instead of installing community ones demonstrates guardrails-first thinking applied to the agent supply chain.
