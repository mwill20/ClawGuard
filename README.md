# 🛡️ ClawGuard

**Guardrail-first AI agent security monitoring framework**

ClawGuard detects [OWASP Agentic Top 10](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) threats against AI agents in real-time. It uses a live OpenClaw deployment as its real-world test target — not simulated telemetry, but actual agent behavior.

> *"I deployed a real AI agent platform, mapped its attack surface, and built an open-source security monitoring framework that detects OWASP Agentic Top 10 violations in real agent behavior — the EDR/SIEM equivalent for the agent era."*

---

## The Problem

AI agents can plan, decide, and execute multi-step actions autonomously — browsing the web, running shell commands, managing files, and calling APIs. That makes them powerful and dangerous. Goal hijacking, tool misuse, memory poisoning, and supply chain attacks against agent systems are the #1 emerging threat vector for 2026.

Everyone is building AI agents for security. Almost nobody is building security *for* AI agents.

## What ClawGuard Does

ClawGuard monitors AI agent behavior and detects OWASP Agentic Top 10 violations:

| Detection | OWASP Code | What It Catches |
|---|---|---|
| Goal Hijack Detection | ASI01 | Agent objective redirected mid-task (e.g., prompt injection in scraped content) |
| Tool Misuse Detection | ASI02 | Agent uses tools beyond intended scope or sends data to unexpected destinations |
| Memory Poisoning Detection | ASI06 | Adversarial inputs corrupt agent long-term memory or learned preferences |

## Architecture

ClawGuard follows a **guardrails-first** design philosophy — security is the architecture, not an afterthought.

- **Core thesis:** AI agents are untrusted by default
- **5-Layer Defense-in-Depth:** Regex → AST → ShellGuard → LLM → SOC Ledger
- **4-Layer Accountability:** Agent Acts → Monitor Observes → Ruleset Defines "Wrong" → Humans Audit Ruleset
- **Key innovation:** Context Ledger — unified context at machine speed

## Project Structure

```
clawguard/
├── target-agent/          # Live OpenClaw deployment (the defended asset)
│   ├── docs/              # Attack surface mapping & recon findings
│   ├── skills/            # Custom-built skills (audited, no community installs)
│   └── README.md          # Deployment & configuration guide
├── detections/            # ClawGuard detection modules
│   └── README.md          # Detection development guide
├── lessons/               # Teaching-oriented documentation
│   └── README.md          # Learning log & article drafts
└── README.md              # This file
```

## Target Agent

ClawGuard monitors a live [OpenClaw](https://docs.openclaw.ai) deployment running three real use cases:

1. **Job Hunting Agent** — Searches job boards, scores JDs against resume, tailors applications (human-in-the-loop for submission)
2. **Networking Manager** — Maintains professional relationship touchpoints on a schedule
3. **Threat Intel Brief** — Daily security news digest pushed to Telegram

Each use case generates real telemetry that ClawGuard monitors for OWASP violations. Skills are **custom-written and audited** — no community skills installed without source review.

## Status

🚧 **Active Development** — Phase 1 (Detection Engine MVP)

## Author

Built by [Michael Williams](https://github.com/mwill20) — SOC analyst with MSSP background transitioning to AI Security Engineering. GIAC certified, UT Austin AI/ML program graduate.

## License

MIT
