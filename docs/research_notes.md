# Research Notes: Tunable LLM-based Proactive Recommendation Agent (T-PRA) & Adaptations

**Date:** 2026-09-29  
**Target Domain:** Movie Recommendations with Dynamic User Preference Memory  
**Paper Reference:** *Tunable LLM-based Proactive Recommendation Agent* (T-PRA), ACL 2025.  
**Authors:** Mingze Wang, Chongming Gao, Wenjie Wang, Yangyang Li, Fuli Feng.  
**Official Codebase:** `https://github.com/gnaWeinrE/T-PRA`

---

## 1. Base Paper Inspection (Task 0.1)

### 1.1 Problem Formulation in T-PRA
Traditional recommender systems are typically **reactive** and optimize for short-term engagement on historical items, leading to "filter bubbles" and "echo chambers." 

T-PRA re-frames recommendation as a **proactive sequential decision process**:
- The goal is to proactively expand and cultivate a user's latent interests toward target items or diverse domains over a multi-turn trajectory.
- The agent takes sequential actions: at step $t$, it recommends an item $a_t$ based on historical interaction context and user feedback.
- Rather than waiting for explicit user search queries, the agent plans paths between past preferences and candidate areas of latent interest.

### 1.2 Agent Architecture
T-PRA employs an **Actor-Critic Agent Framework**:
1. **Actor (Planner/Generator):** Uses an LLM with ReAct prompting (`Thought`, `Action`, `Observation`). Generates thoughts analyzing user response and emits actions of the form `recommend[item]`.
2. **Advisor (Reflexion):** Maintains reflections from previous trials to help the agent steer clear of repetitive recommendations or past user rejections.
3. **Critic:** Evaluates the agent's actions across multiple turns and calculates advantages/rewards to construct preference datasets for fine-tuning.

### 1.3 Reward Functions
T-PRA formulates three reward signals:
1. **User Acceptance / Preference Score:** Simulated or historical user satisfaction score for the recommended item (0 to 1).
2. **Step Length / Coherence Reward:** Semantic distance / relevance between item $a_t$ and previous item $a_{t-1}$ to prevent abrupt, jarring jumps.
3. **Forward Length / Target Proximity Reward:** Measures whether $a_t$ bridges the gap toward candidate expansion / target interests.

### 1.4 Training & Alignment Procedure
- **Direct Preference Optimization (DPO):** The agent generates trajectories, and the Critic labels higher vs. lower advantage trajectories.
- **LoRA Fine-Tuning:** Uses LLaMA-Factory with Llama 3.1 8B Instruct, fine-tuning LoRA adapters over 3 epochs with cosine learning rate schedule (`5e-6`), batch size 1, gradient accumulation 8, `bf16` precision.

### 1.5 Evaluation Metrics & Datasets in Base Paper
- Datasets: Steam (game recommendation) and Amazon (product recommendation).
- Metrics: Success Rate, Path Coherence, User Acceptance rate, Average Reward over multi-turn interactions.

### 1.6 Limitations of the Base Paper
- Evaluated solely on synthetic simulated multi-turn rollouts rather than human user studies or live web environments.
- Relies on offline static training of LLM checkpoints with heavy GPU requirements (multi-GPU A100/V100 setups).
- Lacks a dynamic time-decayed memory model for real-world asynchronous streaming events (likes, dislikes, ratings, dismissals).

---

## 2. Official Repository Inspection & Environment Plan (Task 0.2)

### 2.1 Repository Analysis (`gnaWeinrE/T-PRA`)
Inspection of the official repository structure:
- `Agents/`:
  - `agent_a2c.py`: Implementation of Actor-Critic agent loop with LangChain prompts and LLM invocation.
  - `agent_base.py`: Base agent definitions.
  - `agent_reflexion.py`: Multi-trial reflection mechanism.
  - `prompts.py`: ReAct and reflection prompt templates for LLaMA 3.1 instruct.
- `env/`:
  - `env.py`: Gym-like recommendation environment.
  - `steam.py`, `amazon.py`: Datasets and simulated user feedback engines based on item feature similarity.
- `models/llama.py`: Wrapper for local LLaMA model inference.
- `tpra_start.sh`: Execution script running multi-GPU (`CUDA_VISIBLE_DEVICES=2,5`) LLaMA-Factory DPO training and evaluation.

### 2.2 Environment Incompatibilities & Blockers (Task 0.3)
1. **Hardware Incompatibility:**
   - The official script mandates NVIDIA CUDA GPUs (`CUDA_VISIBLE_DEVICES=2,5`, `bf16=true`, LLaMA-Factory training).
   - Our host environment is macOS Darwin (Apple Silicon, Python 3.9, no NVIDIA CUDA driver).
2. **Dataset Domain:**
   - The paper evaluated Steam and Amazon datasets. Our target project domain is **Movie Recommendations** using the **MovieLens dataset** (`ml-latest-small` / `ml-100k`).
3. **Execution Blocker for Base Training Script:**
   - Running `tpra_start.sh` locally fails immediately due to missing CUDA devices, missing Llama-3.1-8B local weights (~16GB), and incompatible LLaMA-Factory Linux dependencies.

### 2.3 Adaptation Plan & Reproducibility Strategy
To uphold academic integrity without fabricating results:
1. **Documented Adaptation:** Clearly delineate:
   - **Reproduced Concept:** The proactive, multi-turn recommendation paradigm with Actor-Critic ReAct prompting, explanation generation, and exclusion constraints.
   - **Domain Adaptation:** Applying the framework to the MovieLens movie dataset with genres, release years, and explicit ratings.
   - **Novel Extension (Dynamic Preference Memory):** Introducing explicit short-term vs. long-term preference components with time-decayed interaction weighting ($w = s \cdot e^{-\lambda \Delta t}$).
2. **Modular Architecture & Fallback:**
   - Implement a clean **LLM Provider Interface** that supports:
     - Deterministic content-based & collaborative-filtering baseline.
     - Structured LLM agent mode (OpenAI / Ollama / Mock agent adhering strictly to the T-PRA ReAct output schema).
     - Graceful automatic fallback to deterministic ranking if the LLM is unavailable or outputs malformed data.
3. **Evaluation Protocol:**
   - Implement an offline benchmark comparing:
     1. Popularity baseline.
     2. Content-Based / Matrix Factorization baseline.
     3. T-PRA base agent (static preference memory).
     4. Extended T-PRA agent (dynamic preference memory with time decay).
   - Test on a time-aware train/test split with simulated preference-shift scenarios.

---

## 3. Component Comparison Matrix

| Component | Base T-PRA Paper | Proposed Movie Recommendation System | Status |
| :--- | :--- | :--- | :--- |
| **Domain** | Steam (Games) & Amazon (Goods) | MovieLens Movies (`ml-latest-small`) | Adapted |
| **Proactive Trigger** | Step-by-step sequential game loop | Asynchronous background worker (Celery/RQ or background daemon) triggered by onboarding, interactions, and schedules | Newly Implemented |
| **Agent Prompting** | ReAct (`Thought`, `Action`, `Observation`) | ReAct + Structured JSON output with metadata grounding | Adapted |
| **Preference Memory** | Fixed prompt context history | Two-tier Dynamic Memory (Long-term + Time-decayed Short-term) | **Extension Contribution** |
| **User Controls** | None (Batch script) | Full Web App (Next.js dashboard, pause/resume, feedback, profile reset) | Newly Implemented |
| **Ranking Fallback** | Fails if LLM fails | Deterministic hybrid content-collaborative fallback | Newly Implemented |
| **Evaluation Metrics**| Path coherence, acceptance rate | Precision@K, Recall@K, NDCG@K, Diversity, Preference-Shift Adaptation | Adapted & Extended |
