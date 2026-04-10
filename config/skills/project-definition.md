---
name: project-definition
description: How to define and set up a new project from scratch — requirements gathering, tech stack selection, initial roadmap, epic identification, foundation documentation layout. Use ONLY when starting a new project or major greenfield initiative. For daily planning in existing projects, use planning-methodology. For architectural decisions within existing projects, use architecture-decisions.
---

# Project Definition

This skill is for the **greenfield case** — starting a new project or major initiative from nothing. It's the most comprehensive of the planning skills because the decisions made here shape everything that comes after.

**When this skill activates:**
- Starting a new project
- Beginning a major greenfield initiative within an existing org
- Running the `define-project.sh` workflow

**When this skill does NOT activate:**
- Adding features to an existing project → use `planning-methodology`
- Making architectural decisions within an existing project → use `architecture-decisions`
- Setting up tests in a new codebase → use `testing-scaffolding`

## First Principles

### Front-Loading Reduces Drift
Projects drift when foundation decisions aren't made explicit. Investing in project definition upfront — even spending extra days on it — prevents weeks of rework later. The biggest mistake is starting to code before the foundation is solid.

### You Can't Skip Phases, You Can Only Pay Later
Every project has requirements gathering, architecture decisions, phasing, and planning. Skipping them doesn't save time — it just moves the work to later, when it's more expensive because code already exists.

### Write Everything Down
During project definition, nothing is in your head. Everything is on paper (or markdown). This is the time when you're making decisions with the least information and the most optionality. Capture the reasoning so future you can reconstruct it.

### Small Projects Need Less, Not Zero
A one-week project doesn't need the same ceremony as a one-year project. But it still needs SOME of the foundation. Scale the effort, don't eliminate it.

## The Project Definition Process

Follow these stages in order. Don't skip ahead.

### Stage 1: Requirements Gathering

Before deciding anything technical, understand what the project is actually trying to accomplish.

#### Functional Requirements (WHAT the system must do)

Capture in user-facing terms:
- **User stories:** "As a [role], I want [action] so that [outcome]"
- **Features:** Named groupings of related functionality
- **Scenarios:** Concrete examples of how it will be used
- **Acceptance criteria:** How will we know each feature works?

Be specific. "Users can authenticate" is vague. "Users can sign up with email + password, log in, reset their password via email, and stay logged in across browser sessions" is specific.

#### Non-Functional Requirements (HOW WELL)

These are often ignored until they bite you. Get them explicit upfront:

- **Performance targets:** Latency, throughput, response time budgets
- **Scalability:** Expected load, growth projections, peak scenarios
- **Availability:** Uptime requirements (99%? 99.9%? 99.99%?)
- **Security:** Auth model, data sensitivity, compliance (GDPR, HIPAA, etc.)
- **Reliability:** Recovery time, data durability, failure modes
- **Maintainability:** Who will own this? What's their skill set?
- **Observability:** Monitoring, alerting, debugging requirements
- **Accessibility:** WCAG level, supported assistive technologies
- **Internationalization:** Languages, locales, time zones
- **Deployment:** Cloud, on-prem, edge, hybrid?

**Rule:** If you can't answer "how fast must this be?" with a number, you don't have a performance requirement. You have a hope.

#### Constraints

What must be true? What cannot change?

- **Budget:** Hard limits on cost
- **Timeline:** Deadlines that cannot slip
- **Tech stack:** Must use/avoid specific technologies
- **Team:** Size, skills, availability
- **Existing systems:** Must integrate with these
- **Regulatory:** Compliance requirements
- **Organizational:** Political or strategic constraints

#### Assumptions

Every project rests on assumptions. Make them explicit so you can verify them.

- "We assume users have modern browsers"
- "We assume the backend API will be available 99.9% of the time"
- "We assume peak load will be 10K concurrent users"

Each assumption is a risk. If it's wrong, the project may fail. Track which ones are verified and which are still unverified.

#### Out of Scope

As important as what you're building is what you're NOT building. Make the boundary explicit to prevent scope creep.

- "This project does NOT include mobile apps"
- "This project does NOT support offline mode"
- "This project does NOT include admin UI (that's a separate project)"

**Output of Stage 1:** A requirements document in `docs/development/requirements.md` or similar. This is the source of truth for everything that follows.

### Stage 2: Stakeholder & Success Criteria

Who cares about this project, and how will you know it succeeded?

#### Stakeholders

Who is affected by this project?
- **Users:** Who uses the thing?
- **Owners:** Who pays for it, who decides what it does?
- **Operators:** Who keeps it running?
- **Developers:** Who builds and maintains it?
- **Integrators:** Who connects to it from other systems?

For each, understand their needs and how they'll evaluate the project.

#### Success Criteria

Define success before building. Otherwise "done" becomes whenever you run out of budget.

**Good success criteria are:**
- **Observable:** You can measure them externally
- **Specific:** Concrete numbers or behaviors
- **Tied to requirements:** Each links back to a stated need
- **Time-bounded:** When will this be measured?

**Examples:**

Bad:
- "The system is fast"
- "Users like it"
- "We ship on time"

Good:
- "p95 API latency under 200ms at 1000 concurrent users"
- "NPS score ≥ 40 after 3 months"
- "MVP shipped by end of Q2, with 80% of MVP features complete"

#### Anti-Success Criteria

What would indicate the project is going off track?

- "Engineering velocity declines over time"
- "Number of production incidents exceeds 2 per month"
- "Onboarding time for new developers exceeds 1 week"

Track these actively — they're early warning signs.

### Stage 3: Tech Stack Selection

Now (not before) you can choose technology. Stack decisions flow from requirements, not the other way around.

#### Framework for Tech Stack Decisions

For each layer of the stack, apply the decision-making process from `architecture-decisions` skill:

**Languages:** What programming languages will be used? Why?
**Runtime:** What runs the code? (Node, Go, Python, JVM, etc.)
**Framework:** What web/app framework? (Express, FastAPI, Spring, Rails, Next.js)
**Database:** What stores the data? (Postgres, MySQL, DynamoDB, MongoDB)
**Cache:** What handles fast lookups? (Redis, Memcached, or nothing)
**Queue:** What handles async work? (SQS, RabbitMQ, Kafka, or nothing)
**Deployment:** Where does it run? (AWS, GCP, Vercel, bare metal)
**Infrastructure-as-code:** How is infra defined? (Terraform, CDK, Pulumi)
**CI/CD:** How does code ship? (GitHub Actions, GitLab CI, CircleCI)
**Monitoring:** How do you see it? (Datadog, Sentry, CloudWatch)
**Testing:** What frameworks? (Per language — see testing-scaffolding)

**For each decision, write an ADR.** These are foundational decisions that will be questioned later. Capture the reasoning now.

#### Guiding Principles for Stack Selection

1. **Boring is beautiful.** Prefer mature, well-understood technology. Novel tech adds risk.

2. **Team expertise matters.** The best framework your team doesn't know is worse than a decent framework they do.

3. **Operational simplicity wins.** You'll spend more time running it than writing it. Optimize for the long haul.

4. **Start simple, add complexity when needed.** You probably don't need Kafka on day one. Start with a simpler queue or none at all.

5. **Avoid flavor-of-the-month.** Libraries with exponential growth and no clear use case are risky.

6. **Follow the requirements, not the hype.** If the requirement is "store records reliably," almost any database works. Don't pick the trendy one.

7. **Minimize vendor lock-in where practical.** Some lock-in is unavoidable. Extreme lock-in is a problem.

8. **Consider the 5-year operational cost.** Licenses, infra, ops time, hiring difficulty.

#### Writing Tech Stack ADRs

Each major stack decision gets its own ADR. Use the format from `documentation-structure`.

Required ADRs for most projects:
- Language(s) choice
- Framework choice
- Database choice
- Deployment target
- Authentication approach

Optional ADRs (write if decision is non-obvious):
- Caching strategy
- Queue choice
- Monitoring stack
- Testing framework

### Stage 4: High-Level Architecture

Before detailed planning, sketch the architecture at a high level.

#### System Overview

Create `docs/architecture/system-overview.md` with:

**Component diagram:** What are the major pieces?
```
[User] → [CDN] → [API Gateway] → [Service] → [Database]
                      ↓
                 [Cache] ← [Queue] → [Worker]
```

**Data flow:** How does data move through the system?
- User request lifecycle
- Write path
- Read path
- Background processing

**External integrations:** What connects to the outside?
- Third-party APIs
- Webhooks
- Email, SMS, payment processors
- Identity providers

**Key design patterns:** What patterns will the codebase follow?
- MVC? Clean architecture? Hexagonal?
- Event-driven? Request/response? Streaming?
- Microservices? Modular monolith? Monolith?

#### Tech Stack Diagram

Create `docs/architecture/tech-stack.md` listing what's used where and why. This is the summary of all the tech stack ADRs.

### Stage 5: Phase Breakdown

Break the project into phases that can ship independently.

#### Principles of Phasing for New Projects

**Phase 0: Foundation** — everything before you can build features
- Repo setup
- CI/CD pipeline
- Local dev environment
- Basic observability
- Initial standards docs

**Phase 1: Walking skeleton** — simplest possible end-to-end version
- One feature, all layers
- Deployed to production-like environment
- Proves the architecture works

**Phase 2-N: Feature phases** — each shipping meaningful value
- Vertical slices, not horizontal layers
- Each phase independently useful
- Build on previous phases, don't replace them

**Final phase: Hardening & polish**
- Performance tuning
- Security review
- Documentation
- Monitoring fine-tuning

#### Phase Template for New Projects

For each phase, write a phase doc (see `documentation-structure` for format):

```markdown
# Phase N: [Phase Name]

## Goal
[What this phase delivers]

## Prerequisites
- Previous phase complete
- Required infra provisioned
- Required decisions made

## Scope
### In Scope
- ...
### Out of Scope
- ...

## Success Criteria
- [ ] Observable outcome 1
- [ ] Observable outcome 2

## Major Tasks
(See the planning-methodology skill for task breakdown)
```

**Don't over-detail phases that are far in the future.** Phase 1 should be fully detailed. Phase 5 can be a paragraph until you get closer to it.

### Stage 6: Identify Epics

Within each phase, identify the major epics (feature groupings).

**An epic is:**
- Larger than a task, smaller than a phase
- A user-facing capability or technical capability
- Usually spans multiple files and commits
- Has its own success criteria

**Example epics in an auth phase:**
- User registration
- Login with email/password
- Password reset
- Session management
- Account deletion

**Create an epic doc** in `docs/development/features/<feature-name>/overview.md` for each epic. Phase docs can reference these.

### Stage 7: Dependency Identification

Map dependencies between phases, epics, and external systems.

**Internal dependencies:**
- Phase 2 requires Phase 1 foundation
- Epic X depends on data model from Epic Y
- Feature A requires the auth system from Feature B

**External dependencies:**
- Waiting on third-party API credentials
- Need infrastructure provisioning
- Need design assets from stakeholders

**Document dependencies explicitly.** A dependency graph (even just as a list) prevents working in the wrong order.

### Stage 8: Security Audit (Initial)

Even a new project deserves a security pass at the foundation.

**Questions:**
- What data is sensitive? (PII, payment, credentials, proprietary)
- What's the auth model? Is it well-understood?
- Are there known attack vectors for the chosen stack?
- What compliance applies? (GDPR, HIPAA, SOC2, PCI-DSS)
- How will secrets be managed?
- What's the backup/recovery strategy?
- Have you thought about abuse scenarios?

**Output:** A security considerations doc in `docs/architecture/security.md` capturing the foundational decisions. More detailed security work comes later, but the foundation should be thought through.

### Stage 9: Initial Roadmap

Now assemble everything into the top-level roadmap.

Create `docs/development/roadmap.md`:

```markdown
# Project Name — Roadmap

## Overview
[1-2 paragraph summary of what we're building and why]

## Success Criteria
[Top-level success criteria from Stage 2]

## Phases

### Phase 0: Foundation [✅ Complete | In Progress | Not Started]
[Brief description, link to phase doc]

### Phase 1: Walking Skeleton
[Brief description, link to phase doc]

### Phase 2: [First Feature Set]
[Brief description, link to phase doc]

...

## Current Status
[Where we are right now, what's blocking]

## Related Documentation
- [Requirements](requirements.md)
- [Architecture Overview](../architecture/system-overview.md)
- [Tech Stack](../architecture/tech-stack.md)
```

### Stage 10: Initial Documentation Layout

Set up the full four-bucket layout per `documentation-structure` skill:

```
docs/
├── architecture/
│   ├── README.md              (explains purpose)
│   ├── ADR-001-tech-stack.md
│   ├── ADR-002-database.md
│   ├── ADR-003-auth.md
│   ├── system-overview.md
│   ├── tech-stack.md
│   └── security.md
├── development/
│   ├── roadmap.md
│   ├── requirements.md
│   └── features/
│       └── (empty initially, populated as features are planned)
├── standards/
│   ├── code-style.md
│   ├── git-workflow.md
│   ├── testing.md (references testing-scaffolding skill)
│   └── (add as conventions emerge)
├── guide/
│   └── (empty initially, populated as user-facing docs are needed)
└── file_structure.txt
```

Create empty README.md in folders that aren't populated yet, explaining what will go there.

### Stage 11: Set Up CLAUDE.md

Create project root `CLAUDE.md` with:
- Project name and brief description
- Tech stack reference (pointing to tech-stack.md)
- How to run, build, and test
- Standards references (pointing to docs/standards/)
- Any project-specific rules or constraints

This is the entry point for any Claude session working on the project.

## Deliverables Checklist

After project definition is complete, you should have:

**Documents:**
- [ ] `docs/development/requirements.md` — functional, non-functional, constraints, assumptions, out of scope
- [ ] `docs/architecture/system-overview.md` — high-level architecture
- [ ] `docs/architecture/tech-stack.md` — summary of stack choices
- [ ] `docs/architecture/security.md` — security considerations
- [ ] `docs/architecture/ADR-###-*.md` — one ADR per major stack decision
- [ ] `docs/development/roadmap.md` — top-level phased plan
- [ ] `docs/development/features/` — directory ready for feature docs
- [ ] `docs/standards/` — initial coding standards
- [ ] `docs/guide/` — directory ready for user docs
- [ ] `docs/file_structure.txt` — annotated map
- [ ] `CLAUDE.md` — project entry point
- [ ] `README.md` — repo description for humans

**Decisions:**
- [ ] Language(s) chosen and documented
- [ ] Framework chosen and documented
- [ ] Database chosen and documented
- [ ] Auth model chosen and documented
- [ ] Deployment target chosen and documented
- [ ] Success criteria defined and measurable
- [ ] Phase breakdown with at least Phase 1 fully detailed

**Setup:**
- [ ] Repo initialized with gitignore
- [ ] Initial commit with foundation docs
- [ ] Branch protection rules (if applicable)

## Scaling the Process

Not every project needs all of this. Scale to the project size.

### Very Small (1-2 weeks, solo)
- Skip formal requirements doc, use README
- 1-2 ADRs for the big decisions
- Simple roadmap with 1-3 phases
- Minimal standards (rely on defaults)
- Total definition time: 1-4 hours

### Small (1-3 months, 1-2 people)
- Requirements doc (functional only, lighter on non-functional)
- 3-5 ADRs
- Detailed Phase 0 and Phase 1
- Basic standards
- Total definition time: 1-2 days

### Medium (3-12 months, small team)
- Full requirements doc
- 5-10 ADRs
- Detailed Phase 0, Phase 1, Phase 2
- Comprehensive standards
- Security review
- Total definition time: 3-7 days

### Large (1+ years, multi-team)
- Multi-section requirements with versioning
- 10-20 ADRs
- Detailed phases through Phase 3+
- Complete standards library
- Formal security review
- Stakeholder sign-off
- Total definition time: 1-4 weeks

**Rule:** The cost of over-definition is small. The cost of under-definition is large. When in doubt, do more.

## Red Flags in Project Definition

Watch for these — they predict project problems:

### Skipping Requirements Because "We Know What We Want"
Verbal understanding is not documentation. Write it down.

### Making Tech Decisions Before Understanding Requirements
Leads to choosing tools that don't fit the problem.

### "We'll Figure Out Architecture As We Go"
Foundation decisions made late are more expensive. Do them now.

### No Success Criteria
How will you know when you're done? When you're off-track?

### Optimism About Timelines
Your first estimate is usually too optimistic. Add a buffer.

### Assuming Expertise You Don't Have
If nobody on the team knows the tech, that's a huge risk. Factor it in.

### No Out-of-Scope Section
Without explicit boundaries, scope will creep relentlessly.

### No Phase 0 (Foundation)
Jumping straight to features without CI/CD, testing, observability foundations.

### Plans That Require All Phases to Complete
If Phase 1 alone isn't valuable, you've built a horizontal slice that ships nothing.

## Integration With Other Skills

### documentation-structure
- Defines the four-bucket layout you'll use
- Provides all the document templates
- Your primary reference for where things go

### planning-methodology
- Use it for each phase within the project
- This skill sets up the project; planning-methodology handles phase-level planning

### architecture-decisions
- Use it for each tech stack decision during Stage 3
- Each major decision becomes an ADR
- This skill orchestrates; that skill executes each decision

### testing-scaffolding
- Use it during Phase 0 to set up the initial test infrastructure
- This skill coordinates the overall setup; testing-scaffolding handles tests specifically

## Integration With Workflows

This skill is specifically designed for `define-project.sh`. It's heavy machinery — don't invoke it for small tasks.

### define-project.sh
- Primary consumer of this skill
- Produces all the deliverables listed above
- Creates the full documentation scaffolding
- Makes the foundational ADRs

### Other workflows
- This skill should NOT activate for other workflows
- If you're in revision.sh or build-phase.sh, you're in an existing project
- Use planning-methodology or architecture-decisions instead

## Quick Decision Guide

**Am I defining a new project?**
- Yes → This is the right skill
- No → Use planning-methodology (existing project work) or architecture-decisions (existing project architecture)

**Should I do full project definition or a lighter version?**
- Very small (<2 weeks) → Light version: README, 1-2 ADRs, brief roadmap
- Small (<3 months) → Standard version with functional requirements
- Medium+ → Full version with all deliverables

**Where do I start?**
- Stage 1 (requirements) — always. Don't skip ahead to tech choices.

## Summary Checklist

- [ ] Have I gathered functional requirements?
- [ ] Have I gathered non-functional requirements?
- [ ] Have I documented constraints and assumptions?
- [ ] Have I defined out-of-scope explicitly?
- [ ] Have I identified stakeholders?
- [ ] Have I defined measurable success criteria?
- [ ] Have I chosen the tech stack with ADRs?
- [ ] Have I written the system overview?
- [ ] Have I done an initial security review?
- [ ] Have I broken the project into phases?
- [ ] Have I detailed Phase 0 and Phase 1?
- [ ] Have I identified dependencies (internal and external)?
- [ ] Have I set up the four-bucket documentation structure?
- [ ] Have I created the CLAUDE.md?
- [ ] Have I scaled the process to the project size?
