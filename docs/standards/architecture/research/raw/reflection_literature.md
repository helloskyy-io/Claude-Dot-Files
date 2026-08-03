# Reflective-Loop and Self-Improving-Agent Architectures: Literature Synthesis

```
Topic:          What does the literature establish about agents that critique and revise their own work?
Feeds:          Phase: Continuous Process Improvement — the reflection channel and the plateau question
Last validated: 2026-07-23
Revalidate:     medium — 3 months
Confidence:     Definitive on the published findings; DERIVED and weakly supported on transfer to our topology, since the studied systems are single-context self-review, not split-run.
Critic:         PASS — 2026-07-23
```

*Prepared as source material for CSCI-6905 §2 (Background & Related Work).*
*Voice: research assistant / literature review, not marketing.*

## 1. Field overview

Reflection-based self-improvement for LLM agents emerged as a distinct research thread in early 2023, when several groups independently demonstrated that a language model could be pushed toward higher task accuracy by asking it to critique and revise its own outputs at inference time, without weight updates. The canonical members of this "verbal reinforcement" family — Reflexion, Self-Refine, CRITIC, and Self-RAG — established the shared assumption that an inner loop of generate-evaluate-revise, run inside a single process against a single episode of interaction, is the natural unit of self-improvement. By 2024, the frontier moved in two directions: (a) *quality* of the reflection signal, exemplified by Process Reward Models (PRMs) that supervise intermediate reasoning steps rather than only final outcomes, and (b) *durability* of the reflection artifact, exemplified by Voyager's growing skill library and by more recent experience-graph systems.

By 2025-2026 the literature converges on a shared framing that self-improvement is bounded by what can be *verified*. The recursive-self-improvement survey by Ambroise et al. (2026) makes this explicit: it orders the field along a verification hierarchy from formal verifiers down to intrinsic self-assessment, and shows that demonstrable improvement strength tracks that ordering. Lilian Weng's 2026 harness-engineering essay names the same idea as "the verifiability constraint" — self-improvement loops work where evaluation is objective, and stall where it is not. What almost no paper in the corpus engages with, however, is the *substrate* on which the loop runs. Every reflection paper below assumes the loop lives in one process, in one context window, in one uninterrupted session — an assumption that quietly caps how many iterations a loop can actually accumulate before the substrate itself becomes the failure mode.

## 2. Per-paper summaries

### 2.1 Reflexion (Shinn et al., 2023) — arXiv:2303.11366

- **Key contribution.** Introduces "verbal reinforcement learning": an agent maintains a natural-language *reflection* on prior failures and prepends it to subsequent attempts, achieving 91% pass@1 on HumanEval vs. 80% for base GPT-4.
- **Method.** Three-role decomposition (Actor, Evaluator, Self-Reflection). The Evaluator scores a trajectory; the Self-Reflection module writes a verbal critique; the critique is stored in an *episodic memory buffer* and injected into the Actor's prompt on the next attempt.
- **Stated limitations.** Depends on availability of an external or simulated reward signal; the reflection buffer is not learned but text-appended; the paper does not evaluate horizons beyond a small handful of trials.
- **In-memory assumption.** The "episodic memory buffer" is a Python list held in the same process as the agent loop. There is no mechanism for the buffer to survive a crash, an OS restart, a redeploy, or a human review pause; the paper treats each task as one continuous session.

### 2.2 Self-Refine (Madaan et al., 2023) — arXiv:2303.17651

- **Key contribution.** Shows that a *single* LLM, with no external verifier and no additional training, can improve its own output by iterating generate → self-feedback → refine, yielding ~20% absolute improvement across seven tasks.
- **Method.** One model plays generator, feedback provider, and refiner in sequence. The refinement conditions on the concatenated history of prior draft plus prior feedback within a single prompt.
- **Stated limitations.** Improvement plateaus quickly (typically after 3-5 iterations); the same model providing generation and critique cannot catch its own systematic errors; requires strong base models (weaker models regress under self-refinement).
- **In-memory assumption.** The entire generate-feedback-refine trace lives inside one context window of one API call chain. The paper does not address what happens when the trace exceeds context, and treats the iteration count as a small constant chosen at design time.

### 2.3 CRITIC (Gou et al., 2023) — arXiv:2305.11738

- **Key contribution.** Grounds self-correction in *external tools* — search engines, code interpreters, toxicity detectors — rather than in the model's own judgment. Demonstrates that intrinsic self-critique is unreliable and that tool-mediated critique consistently improves factuality, code correctness, and safety.
- **Method.** Initial generation → tool-based verification of specific claims → tool feedback fed back into the model → revised generation. Loop is bounded by an iteration limit.
- **Stated limitations.** Effectiveness depends on tool coverage of the failure modes; ungrounded reasoning steps (aesthetic judgment, novel synthesis) remain uncorrectable; tool outputs must themselves be interpretable to the model.
- **In-memory assumption.** Tool interactions are treated as synchronous function calls inside the same process. No treatment of tool calls that outlive the agent process, of tools that fail intermittently, or of resuming a partially-verified trace.

### 2.4 Self-RAG (Asai et al., 2023) — arXiv:2310.11511

- **Key contribution.** Trains a single LM to emit special *reflection tokens* that decide, at generation time, whether to retrieve, whether the retrieved passage is relevant, and whether the generated span is supported. Reflection is folded into the decoding loop rather than sitting outside it.
- **Method.** Supervised training on trajectories annotated with four reflection-token types (Retrieve, IsRel, IsSup, IsUse). At inference, the tokens gate retrieval and enable controllable generation.
- **Stated limitations.** Reflection quality bounded by training-time annotation quality; the reflection signal is per-token and per-passage, not per-episode; does not accumulate a durable trace of past reflections across sessions.
- **In-memory assumption.** Reflection tokens are decoded within one generation; they do not persist to any store. Cross-session learning would require an outer loop the paper does not define.

### 2.5 Let's Verify Step by Step / PRM800K (Lightman et al., 2023) — arXiv:2305.20050

- **Key contribution.** Empirically establishes that *process supervision* — a reward model trained on step-level correctness labels — outperforms *outcome supervision* on mathematical reasoning (78% MATH accuracy). Releases PRM800K, the first large-scale step-labeled dataset. Foundational for the 2024-2025 PRM literature.
- **Method.** Human raters label each step of MATH solutions as correct/incorrect/neutral; a reward model is trained on these labels; the RM re-ranks solutions from a generator model. Active-learning variants reduce human annotation cost.
- **Stated limitations.** Domain-bounded to MATH; generalization to open-ended reasoning is an open question; process labels are expensive.
- **In-memory assumption.** The reward model is applied to complete traces within a single scoring pass. Nothing in the training or evaluation loop assumes the traces are recoverable across process boundaries — they are treated as JSON blobs that either exist or don't.

### 2.6 Voyager (Wang et al., 2023) — arXiv:2305.16291

- **Key contribution.** First LLM-driven lifelong-learning agent that maintains a *skill library* of executable code, grown open-endedly across a Minecraft game. Skills are temporally extended, compositional, and reusable across new worlds. Provides the reference model for "durable improvement artifact = code library."
- **Method.** Three components — automatic curriculum, skill library, iterative prompting with self-verification and error feedback. New skills are proposed, tested, and added to the library only after verification succeeds.
- **Stated limitations.** Confined to Minecraft's programmatic environment where verification is cheap; requires GPT-4-class model; the library grows monotonically without a compaction or pruning strategy.
- **In-memory assumption.** The skill library is a directory of files, which superficially looks durable, but the agent's *episodic state* (curriculum position, in-progress task, tool responses) is in-process. A crash mid-skill-authoring loses everything but committed skills. The paper does not address recovery, replay, or multi-day continuation.

### 2.7 Self-Reflection in LLM Agents (Renze & Guven, 2024) — arXiv:2405.06682

- **Key contribution.** Empirical study across nine models and eight reflection-agent variants confirming that self-reflection improves problem-solving on multiple-choice tasks (p < 0.001), and providing a comparative ranking of reflection strategies.
- **Method.** Baseline the model, ask each variant to reflect on its wrong answers, re-answer, and measure recovery rate.
- **Stated limitations.** Multiple-choice format is a narrow proxy; no cross-task transfer measured; single-turn reflection cycle.
- **In-memory assumption.** Each experiment is a single request-response-reflect-request chain. No cross-episode retention; each question starts fresh.

### 2.8 EXG: Self-Evolving Agents with Experience Graphs (2026) — arXiv:2605.17721

- **Key contribution.** Structures accumulated task experience (successes and failures) as a relational graph rather than a flat buffer or a code library. Positions the graph as a plug-and-play external memory that any self-evolving agent can consume.
- **Method.** Two operating modes — online (graph grows during agent execution) and offline (consolidated graphs are reused as external memory). Nodes and edges encode task decompositions, tool invocations, and outcomes.
- **Stated limitations.** Presented as an external module; the paper does not specify how the graph is stored across process restarts, nor how concurrent writers coordinate. Compaction and forgetting policies are not addressed.
- **In-memory assumption.** The graph is described at the data-structure layer; persistence is implied by "external memory" but is not formalized. No treatment of atomic updates, replay, or crash recovery of in-progress graph mutations.

### 2.9 A Survey of Self-Evolving Agents (Xiang et al., 2025) — arXiv:2507.21046

- **Key contribution.** Organizes the 2023-2025 self-evolving-agent literature along three axes — *what* evolves (model, memory, tools, architecture), *when* it evolves (intra- vs inter-test-time), and *how* it evolves (scalar rewards, textual feedback, multi-agent debate). Establishes the standard taxonomy.
- **Limitations acknowledged.** Safety, scalability, and evaluation of co-evolutionary dynamics are open. Memory persistence is named as an evolvable component but the *runtime mechanism* for persistence is out of scope.
- **In-memory assumption.** Treats persistence as a property of the data structure, not of the execution model. Substrate for the loop itself is not discussed.

### 2.10 Recursive Self-Improvement in AI (Ambroise et al., 2026) — arXiv:2607.07663

- **Key contribution.** Surveys ~1,250 arXiv papers 2024-2026 and separates *bounded self-refinement* ("convergent, evaluable, already industrial practice") from *open-ended recursive self-improvement* ("constrained by grounding requirements, collapse dynamics, and computational limits"). Formalizes a verification hierarchy — formal verifiers > execution-grounded > retrieval-grounded > model-as-judge > intrinsic self-critique — and shows improvement strength tracks it.
- **Named failure modes.** Self-confirming loops, model collapse, diversity collapse.
- **In-memory assumption.** The paper's own framing treats "the loop" as an abstraction over the reflection cycle; substrate concerns (durability, replay, HITL pause) are noted only in the discussion of governance, not architecture.

### 2.11 Dynamics of Agentic Loops (2026) — arXiv:2512.10350

- **Key contribution.** First formal treatment of reflective-loop *convergence* as a discrete dynamical system in semantic space. Identifies three regimes — contractive (convergence to an attractor), oscillatory, and exploratory (unbounded divergence) — and shows prompt design selects the regime.
- **Method.** Iterative paraphrasing (contractive) and iterative negation (exploratory) as calibration experiments; dispersion measured across iterations.
- **Limitations.** Analysis is purely semantic — no coupling to task performance, external ground truth, or execution substrate.
- **In-memory assumption.** The loop is modeled as a discrete-time map on an embedding space; whether the map is realized by one process, many processes, or a replayable event log is outside scope.

### 2.12 Emergent Convergence in Multi-Agent LLM Annotation (2026) — arXiv:2512.00047

- **Key contribution.** Empirical convergence measurement across 7,500 multi-agent discussions. Introduces process-level metrics — *code stability*, *semantic self-consistency*, *lexical confidence* — usable as observable convergence indicators for black-box agents.
- **In-memory assumption.** Not applicable at the substrate level, but relevant because the convergence metrics assume the full transcript is available for post-hoc analysis — precisely what a durable event history would guarantee.

### 2.13 Lilian Weng, "Harness Engineering for Self-Improvement" (2026)

- **Key contribution.** Not an arXiv paper but a widely-cited essay that names the shared frame the 2026 literature had been converging on: *the verifiability constraint*. "Current self-improvement loops work best for tasks when evaluation metrics are measurable and objective." Introduces the notion of the *harness* — "the system surrounding a base model that orchestrates execution and decides how the model thinks and plans, calls tools and acts, perceives and manages context, stores artifacts, and evaluates results." Argues durable, file-system-backed state is a prerequisite for agents that "recover after interruptions and reason over their own execution history."
- **Relevance to this paper.** Weng articulates the verifiability constraint but leaves the *substrate* question as an engineering recommendation ("keep durable state in files"), not a research architecture. This is the gap the present work addresses.

## 3. Cross-paper synthesis

The shared framework across the reflection corpus is a three-stage inner loop — **generate → evaluate → revise** — with three axes of variation:

| Axis | Range across the corpus |
|---|---|
| Evaluator grounding | intrinsic self-critique (Self-Refine) → external tools (CRITIC) → step-labeled reward model (PRM) → executable verification (Voyager) → formal verifier (RSI survey ceiling) |
| Reflection artifact | prompt-embedded (Self-RAG tokens) → episodic buffer (Reflexion) → code library (Voyager) → relational graph (EXG) |
| Iteration horizon | 1-5 in-context iterations (Self-Refine, CRITIC) → tens of task episodes (Reflexion) → open-ended lifelong (Voyager, EXG) |

The *convergence discussion* is the corpus's weakest surface. Two 2026 papers (2512.10350, 2512.00047) begin to give it formal treatment, but both operate at the semantic-embedding layer and neither ties convergence indicators to a persistent execution record. Prior to those two papers, convergence is discussed only implicitly, as "the number of iterations before improvement plateaus" — a per-run empirical observation, not a measurable property of a loop across time. No paper in the corpus defines convergence *over a durable execution history*, and none defines what it would mean for a reflective loop to *have converged multi-day*.

## 4. Gap analysis — what the literature does not engage with

Four gaps are relevant to the present paper's contribution.

1. **Durable substrate for the loop itself.** Every reflection paper above assumes the reflection cycle lives in one Python process, one context window, one uninterrupted session. Even Voyager and EXG, which persist the *artifact* (skill library / graph), do not persist the *loop* — a crash mid-iteration loses in-progress reflections, tool call state, and evaluation partial results. Weng's harness essay names durable file-system state as necessary but stops short of specifying the execution model (event history, replay semantics, idempotency). The recursive-self-improvement survey treats substrate only as governance context. No paper in the corpus treats durable execution — event-sourced, replay-based, crash-safe — as the substrate on which the reflection loop runs.

2. **Verifiable convergence via event history.** The convergence metrics of 2512.10350 (attractor dynamics) and 2512.00047 (code stability, semantic self-consistency, lexical confidence) are only meaningful if the entire reflection trajectory is recoverable and inspectable. In a substrate that guarantees an event history (every decision, every tool call, every reflection persisted with causal order), convergence becomes a *replayable* property — the loop's history can be audited to prove the loop converged, rather than trusted to have converged. The literature has the metrics; it has not connected them to a substrate that makes them verifiable rather than observational.

3. **Extended horizon beyond the session.** All seven foundational papers cap horizons at what fits in one context window or one training-time buffer. The 2026 literature on long-horizon agents (context folding, ACON, ARC) treats this as a context-management problem — how to compress state into the window — rather than as a substrate problem — how to move state *out of* the window into a durable log the loop can page back in on demand. The multi-day horizon that a real software-engineering agent needs (a design decision on Monday informing a refactor on Wednesday) is unaddressed except by systems like Voyager, whose "lifelong" claim rests on a monotonically-growing skill file directory with no defined recovery semantics.

4. **First-class human-in-the-loop.** The reflection corpus treats HITL as either (a) an evaluation-time gold signal (PRM training, Reflexion's simulated feedback) or (b) a design-time governance concern (RSI survey). No paper models a *pause* — the moment where the loop suspends, a human reviews the accumulated state, and the loop resumes with the human's decision folded into its history. In a durable-execution substrate this is a first-class primitive: the loop is signal-able and resumable. In every substrate the corpus assumes, a pause is indistinguishable from a crash.

The paper's contribution is to argue that these four gaps are one gap — the substrate gap — and that durable execution (event-sourced, replay-based, crash-safe, signal-able) resolves them together. Prior work treats persistence as a property of the *artifact* the loop produces (skill library, experience graph, PRM800K dataset). The present work treats persistence as a property of the *loop itself*.

## 5. Citation list

- Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K., & Yao, S. (2023). *Reflexion: Language Agents with Verbal Reinforcement Learning.* NeurIPS 2023. arXiv:2303.11366. https://arxiv.org/abs/2303.11366
- Madaan, A., Tandon, N., Gupta, P., Hallinan, S., Gao, L., Wiegreffe, S., et al. (2023). *Self-Refine: Iterative Refinement with Self-Feedback.* NeurIPS 2023. arXiv:2303.17651. https://arxiv.org/abs/2303.17651
- Gou, Z., Shao, Z., Gong, Y., Shen, Y., Yang, Y., Duan, N., & Chen, W. (2023). *CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing.* ICLR 2024. arXiv:2305.11738. https://arxiv.org/abs/2305.11738
- Asai, A., Wu, Z., Wang, Y., Sil, A., & Hajishirzi, H. (2023). *Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection.* ICLR 2024. arXiv:2310.11511. https://arxiv.org/abs/2310.11511
- Lightman, H., Kosaraju, V., Burda, Y., Edwards, H., Baker, B., Lee, T., Leike, J., Schulman, J., Sutskever, I., & Cobbe, K. (2023). *Let's Verify Step by Step.* ICLR 2024. arXiv:2305.20050. https://arxiv.org/abs/2305.20050
- Wang, G., Xie, Y., Jiang, Y., Mandlekar, A., Xiao, C., Zhu, Y., Fan, L., & Anandkumar, A. (2023). *Voyager: An Open-Ended Embodied Agent with Large Language Models.* TMLR 2024. arXiv:2305.16291. https://arxiv.org/abs/2305.16291
- Renze, M., & Guven, E. (2024). *Self-Reflection in LLM Agents: Effects on Problem-Solving Performance.* FLLM 2024. arXiv:2405.06682. https://arxiv.org/abs/2405.06682
- Xiang, J., et al. (2025). *A Survey of Self-Evolving Agents: What, When, How, and Where to Evolve on the Path to Artificial Super Intelligence.* arXiv:2507.21046. https://arxiv.org/abs/2507.21046
- Authors of EXG (2026). *EXG: Self-Evolving Agents with Experience Graphs.* arXiv:2605.17721. https://arxiv.org/abs/2605.17721
- Ambroise et al. (2026). *Recursive Self-Improvement in AI: From Bounded Self-Refinement to Autonomous Research Loops.* arXiv:2607.07663. https://arxiv.org/abs/2607.07663
- Authors of "Dynamics of Agentic Loops" (2026). *Dynamics of Agentic Loops in Large Language Models: A Geometric Theory of Trajectories From Semantic Contraction to Exploratory Divergence.* arXiv:2512.10350. https://arxiv.org/abs/2512.10350
- Authors of "Emergent Convergence" (2026). *Emergent Convergence in Multi-Agent LLM Annotation.* arXiv:2512.00047. https://arxiv.org/abs/2512.00047
- Authors of MAR (2026). *MAR: Multi-Agent Reflexion Improves Reasoning Abilities in LLMs.* arXiv:2512.20845. https://arxiv.org/abs/2512.20845
- Weng, L. (2026). *Harness Engineering for Self-Improvement.* Lil'Log, 4 July 2026. https://lilianweng.github.io/posts/2026-07-04-harness/

*Notes for §2 authoring:* the paper's framing should lean on Ambroise et al. (2026) for the verification hierarchy and Weng (2026) for the verifiability constraint terminology. Reflexion (2303.11366) and Voyager (2305.16291) are the natural "prior art we are directly extending" citations — Reflexion for the reflection buffer we make durable, Voyager for the artifact-persistence pattern we generalize. 2512.10350 and 2512.00047 supply the convergence-metric vocabulary; the paper's original contribution is grounding those metrics in a durable event history rather than in embedding-space observation.
