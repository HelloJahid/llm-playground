# Agentic AI

Agentic AI refers to artificial intelligence systems that possess the capacity to act autonomously in pursuit of goals. Such systems can perceive their environment, make decisions, plan sequences of actions, execute those actions, and adapt their behaviour based on feedback, all without continuous human supervision. Unlike traditional AI models that respond only to direct prompts or predefined instructions, agentic AI systems can initiate actions, evaluate intermediate outcomes, and adjust strategies to achieve specified objectives.

### How the agents communicated and coordinated

- Agents shared a common message schema (task description, context, constraints, expected output format) and passed structured messages through a controller/orchestrator.
- A **planner** agent decomposed high‑level requests into sub‑tasks, which were dispatched to **specialist** agents (e.g., retrieval, code, evaluation).
- Agents wrote their intermediate outputs to a shared memory or scratchpad, and a coordinator agent decided whether to accept, revise, or re‑route tasks based on quality checks.

### Benefits over a single model

- **Better quality:** Specialists (retrieval, reasoning, code, critique) produced more reliable outputs than one model trying to do everything in a single pass.
- **Scalability and robustness:** Work was parallelisable; if one agent failed or produced a weak answer, another could re‑plan or re‑attempt without restarting the whole pipeline.cloud.
- **Transparency:** The planner and critic agents made it easier to trace “who did what” and to insert human checks at key stages.


