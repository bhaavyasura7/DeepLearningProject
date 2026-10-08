---
name: readme-writer
description: Creates or refines grounded, production-grade README.md files tailored to the specific project archetype. Analyzes repository structure, manifests, configuration, scripts, and tests to produce value-first, copy-pasteable documentation with zero fluff or hallucinated claims.
---

# README Writer

Use this skill to produce or revise a repository `README.md` that is rigorously grounded in the codebase and immediately actionable for users, evaluators, and contributors.

## Core Principles

1. **Grounded in Evidence**: Never fabricate commands, benchmark scores, badges, or architecture. Every line must trace directly back to manifests (`requirements.txt`, `package.json`), entry points, configs, or test suites.
2. **Value-First Opening**: State what the project is, the exact problem it solves, and why someone should care within the first 10 seconds of reading.
3. **Run in 5 Commands (or Fewer)**: Deliver a frictionless, copy-pasteable quickstart with real paths and verified CLI arguments.
4. **Project-Type Section Profile**: Match the documentation to the project archetype (e.g., ML/RecSys projects require architecture flowcharts, evaluation methodology, hardware specs, and reproducibility commands).
5. **Interactive / Visual Walkthrough**: Provide step-by-step guidance for demos, presets, or user interfaces.
6. **No Fluff / No Generic Boilerplate**: Eliminate empty marketing buzzwords, unconfigured badge placeholders, and generic sections that don't apply.

## Suggested Section Structure for RecSys / ML Applications

1. **Title & One-Sentence Pitch**: Crisp name, punchy value proposition, and core differentiator.
2. **Architecture & Pipeline**: Flowchart (Mermaid) mapping data flow, reasoning stages, and storage.
3. **Quickstart & Setup**: Sequential, tested commands (`make setup`, `make data`, etc.).
4. **Interactive Demo Guide**: Step-by-step click script explaining what to observe.
5. **Empirical Benchmarks & Evaluation**: Ground-truth split protocol, benchmark comparison table, and live latency stats.
6. **Pipeline Deep-Dive (Stages 1–4)**: Clear breakdown of understanding, candidate discovery, judging, and ranking.
7. **Repository Structure**: Curated file tree highlighting key modules.
8. **Configuration & Customization**: Explanation of parameters (`config.yaml`, `.env`).
9. **Verification & Testing**: Commands to validate acceptance criteria and test coverage.
10. **Hardware & Limitations**: Resource usage, local LLM specs, and known constraints.
11. **References & Citations**: Academic papers and foundational algorithms.
