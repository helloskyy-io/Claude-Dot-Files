  Agents are basically the same problem space Temporal was built for:

  ┌───────────────────────────────────────────────────────────────────┬───────────────────────────────────────────┐
  │                      Agentic AI failure mode                      │     Temporal primitive that solves it     │
  ├───────────────────────────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ LLM call fails or gets rate-limited mid-workflow                  │ Activities with retry policies            │
  ├───────────────────────────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ Agent needs to run for hours/days (long research task, human      │ Durable workflows that survive process    │
  │ approval loop)                                                    │ restarts                                  │
  ├───────────────────────────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ Multi-agent coordination (planner delegates to sub-agents)        │ Child workflows                           │
  ├───────────────────────────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ Agent needs to pause and wait for external event                  │ Signals + selectors + timers              │
  ├───────────────────────────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ Tool call is non-idempotent and could double-charge / double-send │ Activity idempotency + deterministic      │
  │                                                                   │ replay                                    │
  ├───────────────────────────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ Need to un-do partial work when downstream step fails             │ Saga pattern via compensating activities  │
  ├───────────────────────────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ Need to inspect what an agent did after the fact                  │ Full event history / query API            │
  └───────────────────────────────────────────────────────────────────┴───────────────────────────────────────────┘

  Every serious production agent orchestration I know of that's past the prototype stage has ended up either using
  Temporal, or reinventing 60% of it in Redis + Postgres + wrappers. Sourcegraph's Cody, Databricks' agent operations,
  Fireflies, Vercel's AI SDK backends — all end up in this pattern.

  Meanwhile, the LangGraph/CrewAI/OpenAI-Assistants-API layer that most Agentic AI courses teach handles the flow 
  logic of an agent, but skips almost every one of the failure modes above. Prototype-grade orchestration, not
  production-grade.