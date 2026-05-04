# Model Card

## Model Status

This repository does not train, fine-tune, evaluate, or deploy an AI/ML model.

ClawGuard currently uses deterministic Python rules for ASI06 job-description content detection. No model weights, model API calls, embeddings, or LLM-as-judge components are included in the local detector implementation.

## Intended Use

This file exists to make the model status explicit for reviewers.

The project is intended to demonstrate:

- Agent security telemetry.
- Deterministic ASI06 detection rules.
- Evidence preservation.
- OpenClaw runtime integration.

## Out-of-Scope Use

Do not interpret this repository as:

- A trained model.
- A fine-tuning project.
- A benchmarked ML classifier.
- A production LLM guardrail service.

## Future Model or Semantic Guardrail Work

Recommended but not implemented here:

- Semantic ASI01 review using deterministic policy checks or LLM-as-judge.
- Prompt sanitization/quarantine before future LLM review.
- Labeled evaluation data for measuring semantic guardrail quality.
- Model/provider documentation if any model is added later.

If a future contribution adds a model, this file must be replaced with a full model card covering model source, version, license, intended use, out-of-scope use, inputs, outputs, evaluation, safety limitations, and deployment considerations.
