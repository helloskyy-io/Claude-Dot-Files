
# puma wrote this manually:

## Early planning, research and feasibility:

1. research children training: (to get what we really want with a high level of accuracy)

problem statement is formatted via standards with AI PM (HiL), (problem we are solving, rough concepts, architecture, generalities more than stack)
then the research is run against that to produce the synthesis. It first derives a pool size of topics taht need to be researched to support the problem statement 
it generates the papers using real sources taht are fully documented as if it were collegel level research papers
it then generates a synthesis, taht brings togehter the lessons and concepts from the various papers
what comes back is food to feed the revision of the problem statement again and guide the Human to correctly identify the problem and a trajectory towards solving that problem
run this cycle till you and the research team agree on direction, agree on teh problem, and are aligned on a trajectory of resolution grounded in research. 
(what problem are we solving, how are others solving this, how novel is our approach)


2. marketing children training: (to get what we want with a high level of accuracy)

workflow runs with marketing in mind, doing research to see if the research synthsis generated supports the problem statement, or if its trajectory is a bit different, then do marketing analysis to see if there is a need for a product that solves this problem, and lastly decide between revising the problem statement, doing more research, or moving forward. (who has this problem? how comon is it? can we sell the solution?)

working towards completion:
when research and marketing are complete: (this is the HiL stage)
needs additional research = research re-run + marketing rerun
needs change in problem statement = research re-run + marketing rerun
repeat till moving forward with actual planning!

For HiL review:
Start with synthesis.md — it's the decision deliverable and holds all 15 action candidates. That's "what are the new recommendations."

General flow of an idea to an implementation:
research > master planner > phase planning > build-phase > revision > testing 
(loops again via completion of master planning that uncovers lots of decisions still beign made)
(loops again via research-refresh)

General flow of researching an idea for feasability:
research > marketing-viability > target-audience, opportunities
(loops again via opportunities picking up things the current trajectory doesnt allow for)


3. plan children training: (to get what we want with a high level of accuracy)

a;lsdjfa;slkdfj


4. build children training: (to get what we want with a high level of accuracy)

asl;dkjfas;lsdkfj



## design of children and parents:

### Scenario: Large project research and planning:
run on the project as a whole, either initial planning or a follow up to previous with additional info/ideas. This is for a large project. It exemplifies researching will satisfied,
then planning till satisfied, then building the plan. 

research --project: (parent)
- research-write
- research-verify
- review-pr
(usually HiL at this step, repeat till happ

plan-project --project(flag): (parent) (run on the reasearch that was previously ran "project as a whole")
- triage-candidates (triage of candidate list and labels correctly the candidates for inclusion in sprints/features/phases or rejects them with reasoning)
- plan-candidates (activity NOT child workflow!) (Creates scaffolding for missing items recently triaged)
- research-write: (if research is missing or stale, run research, targeting the sprint/feature or scaffolding)
- research-verify: (if above ran, run verify, targeting the sprint/feature)

wrong from here down!
- plan-feature: (plans the feature/roadmap/phases (epics) that are referenced onto the sprint)
- plan-verify: (checks and verifies the planning, fixes issues, assignes an estimated hours value based on the complexity of each phase)
- plan-sprint: (adds the new feature from above (if any), any changes to the phase hour estimates triggers a change to the total in the sprint, new sprints are calculated at the time of creation)
- review-pr
(usually HiL at this point, repeat till happy)



### Scenario: Project Creation and expansion
run on the project as a whole, either initial planning or a follow up to previous with additional info/ideas. This is for a small project. It exemplifies researching will satisfied,
then planning till satisfied, then building the plan. 

research --project: (parent)
- research-write or research-write --minor: (large or small project)
- research-verify
- review-pr
(usually HiL at this point, repeat till happy)

plan-project --project(flag): (parent) (run on the reasearch that was previously ran "project as a whole")
- triage-candidates (triage of candidate list and labels correctly the candidates for inclusion in sprints/features/phases or rejects them with reasoning)
- plan-candidates (activity NOT child workflow!) (Creates scaffolding for missing items recently triaged)
- research-write: (if research is missing or stale, run research, targeting the sprint/feature or scaffolding)
- research-verify: (if above ran, run verify, targeting the sprint/feature)

wrong from here down!
- plan-feature: (plans the feature/roadmap/phases (epics) that are referenced onto the sprint)
- plan-verify: (checks and verifies the planning, fixes issues, assignes an estimated hours value based on the complexity of each phase)
- plan-sprint: (adds the new feature from above (if any), any changes to the phase hour estimates triggers a change to the total in the sprint, new sprints are calculated at the time of creation)
- review-pr
(usually HiL at this point, repeat till happy)



### Scenario: Feature creation and expansion
run on an identified feature with either a stub or a fully developed feature. For all sizes of projects

feature-manager: (parent of a parent, most likely cron based on expired research)
   |  
   ├─research --feature: (parent)
   |  ├─research-write --minor: (targeting feature)
   |  ├─research-verify: (targeting feature)
   |  ├─review pr
   |  └─(usually HiL at this point, repeat till happy)
   |
   ├─plan-feature --feature(flag): (parent) (pointed at the feature, or feature stub, and the research. research not required)
   |  ├─plan --feature: (plans the feature/roadmap/phases (epics) that are referenced onto the sprint)
   |  ├─plan-verify: (checks and verifies the planning, fixes issues, assignes an estimated hours value based on the complexity of each phase)
   |  ├─plan-sprint: (adds the new feature from above (if any), any changes to the phase hour estimates triggers a change to the total in the sprint, new sprints are calculated at the time of creation)
   |  ├─review-pr
   |  └─(usually HiL at this point, repeat till happy)
   |
   ├─build-feature: (parent)
   |  ├─build: 
   |  ├─build-refine:
   |  ├─review-pr
   |  └─(usually HiL at this point, repeat till happy)
   |
   └─(usually HiL at this point, repeat till happy)

### Scenario4: 
run a targeted security audit on a design

security-audit: (parent)



### Scenario5:
run a build on a targeted design phase: 

build --what flags? if any?: (parent)
- build-draft: (creates the work based on the phase or the prompt, then opens a PR for it, returns the URL)
- CI gate: (parent code only)
- build-refine: (runs multiple agents to check then fixes the concerns)
- review-pr: (rules on the status of the build, decides MERGE or HOLD: if HOLD and issues need no HiL it loops, otherwise it stops for HiL.




In the future the "scenarios" can become long running god like workflows that a user sets off and comes back hours/days later to inspect (or crons that dump notification to standup)
This is accomplished by scenarios that chain or loop large long runnign parent workflows. 