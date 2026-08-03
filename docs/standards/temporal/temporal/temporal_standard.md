<!-- VENDORED — DO NOT EDIT LOCALLY -->
> **Vendored from `helloskyy-io/MDC-Master-Planning`** · `standards/development/temporal/temporal_standard.md.md` · `988c639` (2026-08-01)
>
> This file is a **verbatim copy**. Do not edit it here — corrections and amendments go upstream, then re-vendor.
> Local additions belong in [`README.md`](README.md) (applicability) or [`claude-dot-files-addendum.md`](claude-dot-files-addendum.md) (what is genuinely ours).
>
> Re-vendor with: `scripts/helpers/vendor-standards.sh`

---

# Temporal Standard

**Last Updated:** 2026-06-06

**Binding scope:** Temporal usage across the MDC platform — workflow / helper / activity authoring, executor contracts, result conventions, scheduling, and in-image worker configuration. This standard is the **routing hub** for Temporal-specific concerns; specific topics live in peer standards listed in §1.

------------------------------------------------------------------------

## §1 Routing Table — Where Temporal-related concerns are codified

For Temporal work, start here; if your concern matches a peer standard below, follow the link:

| If you're working on... | Read this |
|---|---|
| Workflow + helper authoring; three-layer architecture; semantic wrappers | §3 (this document) |
| `ACTIVITY_MAP` plan-to-callable resolution; intent-first naming | §4 (this document) |
| `ActivityResult` shape; status codes (`ok`/`changed`/`skipped`/`failed`) | §6.1 + §6.2 (this document) |
| External-API error vocabulary, `error_code` contract, retry semantics by error code | §6.3 + §6.4 (this document) |
| In-image worker configuration — `SandboxedWorkflowRunner`, `passthrough_modules`, C-extension imports | §5 (this document) |
| Worker segmentation, task queue naming, immutable images, multi-stage Dockerfiles, fail-fast dispatch, cutover discipline | [Temporal Worker Deployment Standard](./worker_deployment_standard.md) |
| Persistent state outside workflow event history (Temporal schedules, desired-state YAML, K8s resources, RBD/Ceph artifacts, GitHub deploy keys, Tailscale tags); fresh-MDC bootstrap; workflow retirement; idempotent writes; stage-coupling contracts; cleanup-on-failure | [Temporal Stateful Patterns Standard](./stateful_patterns.md) |
| Workflow dispatch from scripts / Django / scheduled triggers — `*_start.sh`, fail-fast verification, task-queue addressing | [Temporal Worker Deployment Standard §8](./worker_deployment_standard.md) |
| Execution-paths guardrails (Temporal+Ansible / +Terraform / +ArgoCD / +Python ownership) | [Architecture Standard](../../architecture/architectural_standard.md) Guardrail 4 |
| Logging from worker code | [Logging Standard](../logging/logging_standard.md) (cross-cutting; workers consume it) |
| YAML-mutating activities (writable config files) | [YAML Editing Standard](../yaml/yaml_editing_standard.md) — `ruamel.yaml` round-trip mode binding |
| Test placement for workflow / helper / activity tests | [Testing Standard](../testing/testing_standard.md) |
| Per-system error-code vocabularies (Tailscale, GitHub, Vault, etc.) | The respective per-system standard (linked from §6.4) |

**Binding rule for cross-standard consistency:** peer standards above may add Temporal-specific rules within their domain, but they MUST NOT relax universal rules from this standard's §3 Three-Layer Architecture, §6.3 Error Surfacing Contract, or the Worker Deployment Standard's §1.4 cross-worker dispatch invariant.

------------------------------------------------------------------------

## §2 Role in the Platform

**Mission:** workflows describe intent; helpers compile intent into an execution plan; activities execute.

Temporal is the **orchestration backbone** of Skyy-Command. It does not itself provide the configuration engine — it orchestrates steps. Configuration and provisioning are executed through Ansible, Terraform, Proxmox API, ArgoCD, or Python activities, depending on what is most appropriate. Per-tool ownership lives in the [Architecture Standard](../../architecture/architectural_standard.md) Guardrail 4.

### §2.1 What Temporal provides

- Durable workflow execution (survives crashes, restarts)
- Retry logic with configurable policies
- Approval gates and human-in-the-loop steps
- Cron scheduling for recurring workflows
- Audit trail of all operations (what, when, why, result)
- Workflow versioning and migration

### §2.2 Scheduling

Temporal cron is the primary scheduler for recurring platform operations (reconciliation loops, health checks, rolling updates). See [Architecture Standard Guardrail 4](../../architecture/architectural_standard.md) for guidance on choosing the right scheduler for a given task.

### §2.3 Dynamic targeting

Temporal does **not maintain static inventories**. Target hosts are injected dynamically during execution from:

- Desired state
- Customer request parameters
- Skyy-Command configuration

------------------------------------------------------------------------

## §3 Three-Layer Architecture

Temporal workflows follow a three-layer architecture that separates concerns and maximizes reusability.

**Service-deployment workflows:** if the workflow brings a platform service to its operational state, it additionally satisfies [K8s Deployment Standard §7b Service-Deployment Workflow Self-Containment](../kubernetes/k8s_deployment_standard.md) — the workflow MUST self-contain render → commit → wait-for-ArgoCD-Synced as orchestration steps BEFORE any service-specific init / handoff / configure activities. The operator dispatch is a single workflow; pre-deployment by an out-of-band operator action is forbidden.

### §3.1 Layer 1: Workflow (Orchestration)

- **Orchestration only** — describes the high-level steps and intent
- **Steps + comments + retries/timeouts** — readable, maintainable orchestration logic
- **Calls helpers and activities** — delegates to lower layers
- **No external I/O** — all I/O happens in activities
- **Deterministic** — no randomness, no direct I/O, no network calls
- **Start other workflows** using child workflow APIs (not Temporal client)
- Do NOT instantiate Temporal clients in workflow code

### §3.2 Layer 2: Helper (Compiler)

- **Pure + deterministic** — no I/O, no side effects, same input = same output
- **Validates and normalizes inputs** — ensures data is correct and consistent
- **Produces typed activity inputs and/or execution plan** — compiles intent into executable specs; for each semantic step, builds a **dedicated input model** (see §3.3 *Semantic activity input models*) and places its serialized payload on the plan
- **Encodes workflow-specific naming/IDs/defaults** — workflow-specific logic lives here
- Lives **beside the workflow** in the same module **purpose** folder (not a nested folder named after each workflow file):
  - `modules/{module}/{purpose}/{name}_helper.py`
  - Example: `modules/common/provision/genesis_helper.py` next to `genesis_workflow.py`
- **Purpose** is the folder for a slice of work (`provision/`, `reconcile/`, …). **`{name}`** is the short prefix shared by the trio `{name}_workflow.py`, `{name}_helper.py`, `{name}_activities.py` (e.g. `genesis`).
- Folders are only created when workflows are implemented (no placeholder folders)

### §3.3 Layer 3: Activities (Capabilities)

- **External I/O + side effects** — all external operations happen here
- **Two kinds of Activity definitions** (both may be registered on the worker; read **top-down** — how a run flows: workflow → wrapper → executor):

#### 3a. Semantic activity wrappers (`modules/{module}/{purpose}/{name}_activities.py`) — *first hop from the workflow*

- **Blunt clarification:** A semantic wrapper **is a real Temporal Activity definition** (a function decorated with `@activity.defn`, registered on the worker and passed to `execute_activity`). It is **not** a helper alias, not "just a string," and not only documentation — Temporal schedules and records it like any other activity.
- **Workflow-scoped thin wrappers** — co-located with the workflow they serve
- **Naming:** `{name}_activities.py` beside `{name}_workflow.py` and `{name}_helper.py`
  Example: `modules/common/provision/genesis_activities.py`
- **Purpose:** Temporal UI and history show **meaningful Activity Types**, not repeated generic names (`create_directory`, `run_ansible_playbook`, …) for unrelated steps.
- **Implementation:** each wrapper is `@activity.defn(name="semantic-intent")` and **delegates** to the generic executor (plain Python call into `activities/...`; shared logic is not duplicated).
- **Helper references wrappers** via the **`ACTIVITY_MAP` key** (see §4); the generic executor symbol is an implementation detail.
- One wrapper per **distinct intent** in that workflow (reuse the same wrapper if two steps share identical intent).
- **House rule (first-party workflows):** In **curated, first-party** workflows (Genesis, Home Assistant-related flows such as HAOS template refresh, OpenClaw bootstrap, etc.), **every planned step** that hits an activity must resolve through a **semantic wrapper** in `{name}_activities.py` and an `ACTIVITY_MAP` key — **even when** the underlying generic executor's name would already be readable (e.g. `load_mdc_config`). One wrapper per **distinct intent**; reuse the same wrapper when two steps share identical intent. Third-party or throwaway scripts are out of scope unless we choose to adopt the same pattern.

#### Semantic activity input models (one per semantic wrapper)

- **One input type per semantic activity** — e.g. `SshGenerateDesiredStateDeployKeyInput` pairs with the wrapper / `ACTIVITY_MAP` key `ssh_generate_desired_state_deploy_key` and the UI type `ssh-generate-desired-state-deploy-key`. Name the **class after the semantic activity** so similar steps never share a vague "playbook input" type and accidentally mix fields across workflows.
- **Purpose:** A single, explicit contract between **helper (compiler)** and **wrapper**. The helper owns compilation; the model is the serialized boundary. No long positional `args` tuples, no duplicated parameter lists between helper and wrapper, no field-order drift as steps evolve.
- **Helper:** When building each plan step, construct the input model (dataclass, Pydantic `BaseModel`, or `TypedDict` + factory), then attach **one JSON-serializable payload** to the step, conventionally **`"input"`** (e.g. `model_dump(mode="json")`, `dataclasses.asdict()`). Other step metadata (`retry_policy`, `timeout_seconds`, `name`, `env_from_step`, …) stays alongside `"input"`.
- **Workflow:** Resolves `ACTIVITY_MAP[step["activity"]]` and schedules **`execute_activity(activity_func, args=[step["input"]], ...)`** (one positional argument = the payload dict, or a single-element args tuple equivalent). Every planned step uses the **same invocation shape**.
- **Canonical step-dict field name (binding) — APPLIES TO STEP-DICT-PLAN WORKFLOWS ONLY:** the field that keys into `ACTIVITY_MAP` is **`"activity"`** — not `"key"`, `"name"`, or `"action"`. This is the cross-module convention that newer modules (baseline-tailnet-push, cluster-provision) follow and that the vault module pre-dates (vault uses `"key"` from PR #88-era code). Codebase normalization to `"activity"` is **touch-as-you-go** — when a vault-domain helper is next touched substantively, fold the rename in; do not dispatch a separate refactor PR solely for this. New step-dict-plan modules MUST use `"activity"`. Breaking it looks like: a new module-level helper compiling steps as `{"key": ..., "input": ..., ...}` instead of `{"activity": ..., "input": ..., ...}`.
- **Direct-dispatch master+saga orchestrations are EXEMPT from the `"activity"` step-dict convention.** Workflows that dispatch activities by direct callable (the `customer-browser`, `synaptron` reconcile, and `flux-edge` deploy/retire shapes — master workflow + per-target child + compensating activities) have **no step-dict execution plan**. There is no field keying into `ACTIVITY_MAP` because the workflow itself names the callable inline. In this shape, `ACTIVITY_MAP` (when present) is keyed by **`fn.__name__`** for **registration single-source-of-truth** — the worker's `activity_implementations=[...]` list iterates the map's values to register every wrapper, and the `fn.__name__` keys serve as readable indirection / discoverability. Standards-auditor reviews that flag missing `"activity"` step-keys on these workflows are **false-positives** — confirm the shape (helper-compiled plan vs direct callable) before flagging.
- **Wrapper — default contract:** Helpers always serialize input models to a **plain `dict`** on the plan (`model_dump(mode="json")`, `dataclasses.asdict()`, …). Wrappers accept that **`dict`** as the activity parameter (what Temporal delivers) and **reconstruct or validate** the semantic input model **at the top** of the function (`Model.model_validate(inp)`, `MyInput(**inp)`, etc.). Do **not** assume a typed model object crosses the workflow-activity boundary; the wire format is **dict**.
- **Signature** is **minimal** — one `dict` parameter (conventionally `inp` or `payload`), then **unpack** into the generic executor (`run_ansible_playbook`, `load_mdc_config`, …). The wrapper stays thin; complexity lives in the model and the helper.
- **Even "small" steps:** Prefer a dedicated input model anyway — **consistency at scale** (hundreds of workflows/activities) matters more than saving a few type lines; rare trivial steps are the exception, not the norm.

Illustrative wrapper (payload in, unpack, delegate):

```python
@activity.defn(name="ssh-generate-desired-state-deploy-key")
async def ssh_generate_desired_state_deploy_key(inp: dict) -> ActivityResult:
    m = SshGenerateDesiredStateDeployKeyInput.model_validate(inp)
    return await _delegate(
        run_ansible_playbook,
        m.playbook,
        m.extra_vars,
        m.result_fact_name,
        m.target_hosts,
    )
```

#### 3b. Generic executors (`activities/`) — *implementation library the wrapper calls*

- **Workflow-agnostic** — reusable across all workflows
- **Tool adapters** live here, one folder per backend where it makes sense, e.g.:
  - `activities/ansible/` — run playbooks (`run_playbook.py` and shared implementation)
  - `activities/terraform/` — apply plans (future)
  - `activities/argocd/` — sync apps (future)
- **Folder names MUST be valid Python identifiers (binding)** — no leading digits, no hyphens, no reserved words. Folders under `activities/` are Python packages and become import paths (`from lib.temporal.activities.<pkg> import …`); names that aren't valid identifiers cannot be imported. Use the platform-vendor product name's identifier-safe form when the vendor name itself isn't (e.g., `activities/onepassword/`, not `activities/1password/`).
- **Single technical responsibility** — one generic "call this tool with these parameters" surface
- **Idempotent / retry-safe where possible**
- **Accept fully-specified typed inputs** — no hidden workflow context (callers are usually **wrappers** that unpack a semantic input model into these parameters)

**Rule:** Keep `activities/` truly generic. Put workflow-specific **Temporal-visible Activity definitions** only in `{name}_activities.py`.

#### Generic vs semantic activity names (config loading example)

- **`load_mdc_config`** — **generic** activity: implementation in `activities/config/load_mdc_config.py`, Temporal Activity type `load_mdc_config`, reusable by any workflow.
- **`load_genesis_mdc_config`** — **Genesis semantic wrapper** in `genesis_activities.py`, Temporal UI type `load-genesis-mdc-config`, delegates to **`load_mdc_config`** (plain Python call). Genesis schedules the **wrapper**, not the generic, when following the house rule.

------------------------------------------------------------------------

### §3.4 Composition — reuse workflows as building blocks (binding principle)

The three layers above maximize reuse *within* a workflow (generic executors shared across wrappers); the **same discipline applies across workflows.** The platform's building blocks stack:

**generic activities → composable child workflows → parent workflows.**

**Do not reimplement logic that already exists as an activity or a workflow — reuse it.** A workflow that needs functionality another workflow already provides composes it as a **child workflow** (explicit `task_queue` per [Worker Deployment §1.4](../temporal/worker_deployment_standard.md)), rather than duplicating its steps. This is how the platform builds **complex higher-level workflows cheaply** — a parent gains the full behavior of its children with minimal new design or new components. The reconciler family is the exemplar: `ClusterReconcileWorkflow` composes `VmReconcileWorkflow`, which composes the canonical DAS clone path.

**Scope — situational, NOT a mandate to decompose.** Compose **where it benefits**: when proven functionality already exists to reuse. This is orchestration hygiene, not a directive to split every workflow into children — a single-purpose workflow with nothing to reuse is correctly monolithic, and manufacturing children for their own sake adds dispatch overhead for no gain. The test is *"am I about to reimplement something that already exists as a workflow/activity?"* — if yes, compose it; if there's nothing to reuse, stay monolithic.

**Breaking it looks like:** a workflow re-implementing node provisioning, VM building, clone logic, or any machinery an existing workflow already owns, instead of composing that workflow as a child — duplicated code that drifts out of sync. The binding domain application is [Container Clustering Standard §1](../platform_deployment/container_clustering_standard.md) (the reconciler composes canonical children; ZERO novel components).

------------------------------------------------------------------------

## §4 ACTIVITY_MAP Pattern

- **What it is:** A dict in the workflow module (e.g. `genesis_workflow.py`) mapping **string keys** from the helper plan to **activity callables** (wrappers or, during migration, generic executors).
- **How it works:** For each step, `activity_func = ACTIVITY_MAP.get(step["activity"])`, then pass the **compiled payload** as the only activity argument: `await workflow.execute_activity(activity_func, args=[step["input"]], ...)` (see §3.3 *Semantic activity input models*). If the key is missing - step fails with `UNKNOWN_ACTIVITY`.
- **Legacy / migration:** Older plans may still use `"args": (...)` tuples until refactored; target state is **`"input": { ... }`** per step.
- **Wrappers vs registration:** The **generic** executor (e.g. `run_ansible_playbook`) **must exist as Python code** for wrappers to call it. It **does not** have to remain a **registered** worker activity if **every** workflow path on **that** worker uses wrappers that delegate to it — then only those wrapper callables need to be registered for those paths.
- **Worker registration (source of truth):** Each worker declares the **exact list of activity callables** it registers. Include **every semantic wrapper** required by the workflows that worker runs. Include a **generic executor** only when some workflow on that worker still **calls it directly** (first argument to `execute_activity` is the generic) or during a **transitional** plan — otherwise generics stay import-only behind wrappers.

### §4.1 Semantic wrapper / `ACTIVITY_MAP` key naming (intent-first)

- The **helper** sets each plan step's `"activity"` field to a **string key**. The workflow resolves it with **`ACTIVITY_MAP[key]`** — the Python callable passed to `execute_activity`. That callable's **`@activity.defn(name="...")`** is what appears as the **Activity type** in the Temporal UI.
- Pair each key with a **dedicated input class** named after that semantic activity (PascalCase + `Input` suffix), e.g. key `ssh_generate_desired_state_deploy_key` → `SshGenerateDesiredStateDeployKeyInput` — avoids shared generic DTOs across unrelated steps.
- **Prefer intent in the key**, not the bare generic tool name, so logs and code reviews stay readable even before you open the UI:
  - `update_<what>_config_section` (not only `update_config_section`)
  - `create_<what>_directory` (not only `create_directory`)
  - For Ansible-backed steps: name by **playbook + role in this workflow**, e.g. `ssh_generate_desired_state_deploy_key` / `ssh_generate_ansible_collections_deploy_key` (or similar), not `run_ansible_playbook`
- **Repeating the workflow name** in every Activity type is optional: the run is already scoped to a workflow. Use a short **domain/purpose** prefix only if disambiguation across workflows sharing a worker matters (e.g. same key string used in two workflows — avoid duplicate keys).

------------------------------------------------------------------------

## §5 Worker Configuration

This section governs **in-image** worker configuration (sandbox, passthrough, runner). For worker *segmentation*, *images*, *task queues*, and *dispatch verification*, see the [Temporal Worker Deployment Standard](./worker_deployment_standard.md).

Each worker (`docker/images/workers/<name>/`) declares the workflows and activities it runs and constructs a Temporal `Worker` with a workflow runner. The default runner is `SandboxedWorkflowRunner`, which validates every registered workflow at worker startup by evaluating the workflow's full import chain inside a restricted Python sandbox. The sandbox rejects non-deterministic operations **and C-extension module loads** during this startup validation scan.

### §5.1 C-extension dependencies require `passthrough_modules`

The sandbox rejects C-extension imports even when those modules are only used by activities, not by workflow code directly. In practice, workflow modules transitively import activity modules (via `ACTIVITY_MAP` references, input dataclass imports, or helper-level type references), so any C-extension in the import chain of any registered workflow causes worker startup to fail with a sandbox validation error — before any workflow actually runs.

**The platform standard for this case is the Temporal Python SDK's `SandboxRestrictions.with_passthrough_modules()` mechanism.** Passthrough-listed modules are not re-evaluated by the sandbox during validation — the host Python's already-loaded copy is used instead. This is the correct layer for the fix: one config entry at the worker, not scattered lazy-import workarounds in every activity.

**Required pattern in every `Worker(...)` setup** whose registered workflows' import chains reach any C-extension module:

```python
from temporalio.worker import Worker, SandboxedWorkflowRunner
from temporalio.worker.workflow_sandbox import SandboxRestrictions

async with Worker(
    client,
    task_queue=TASK_QUEUE,
    workflow_runner=SandboxedWorkflowRunner(
        restrictions=SandboxRestrictions.default.with_passthrough_modules(
            "ruamel", "ruamel.yaml",
            # add other C-extension deps here as they enter the codebase
        ),
    ),
    workflows=[...],
    activities=[...],
):
    ...
```

### §5.2 Current MDC passthrough list

| Module | Used by | Reason |
|---|---|---|
| `ruamel`, `ruamel.yaml` | `activities/desired_state/commit_version.py` (and any future writable-YAML activity) | Comment-preserving YAML round-trip is the platform standard for writable config files; `ruamel.yaml` uses a C extension for speed. Both the namespace package `ruamel` and the submodule `ruamel.yaml` must be listed because it is a namespace-package import. |

### §5.3 Adding a new C-extension dependency

Any new activity that imports a C-extension at module level must be accompanied by a passthrough update. Common C-extension deps that will trigger sandbox rejection when introduced: `cryptography`, `lxml`, `psutil`, `numpy`, `pandas`, `pydantic` (version-dependent), `psycopg2`, `asyncpg`.

Checklist before merging an activity that adds a new dep:

1. Verify whether the dep has a C-extension component (`pip show <pkg>` for `.so` files, or check the package's build classifiers).
2. If yes, add the module name(s) to `SandboxRestrictions.with_passthrough_modules(...)` in **every** worker whose registered workflows' import chains reach the new activity.
3. Update the §5.2 *Current MDC passthrough list* table.
4. Runtime-verify the worker starts cleanly — unit tests do not catch sandbox validation failures because the validation only runs at `Worker.start()` against a real Temporal server. Restart the worker pod and confirm the logs reach "Worker started successfully" without a sandbox rejection error.

### §5.4 Why `pyyaml` for read-only, `ruamel.yaml` for writable

`pyyaml` is pure-Python and does not hit the sandbox issue, but it does not preserve comments, blank lines, or key ordering on round-trip. `ruamel.yaml` preserves all three and is the platform-mandated library for any activity that modifies a YAML file in place. The cost is the `passthrough_modules` entry above. This is a deliberate trade-off: YAML comment loss during automated edits is a correctness-class bug (hidden documentation and intent-capturing comments disappear silently), and paying one line of worker config is cheaper than re-learning that bug every time an operator reads a mangled config file. **Use `pyyaml` only for read-only parses. Use `ruamel.yaml` for any edit-and-write operation.** Full binding rules in the [YAML Editing Standard](../yaml/yaml_editing_standard.md).

------------------------------------------------------------------------

## §6 Execution Result Standard

All executor calls must return **machine-readable structured results**.

### §6.1 ActivityResult

```python
@dataclass
class ActivityResult:
    status: Literal["ok", "changed", "skipped", "failed"]
    details: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    error_code: Optional[str] = None
```

`details` is a structured dict of diagnostic fields, not a free-form string. On happy-path outcomes it carries state-relevant context (e.g., `details.key_id`, `details.existing_key_id`, `details.reason="already_registered"`). On error-path outcomes it follows the §6.3 Error Surfacing Contract.

### §6.2 Status Codes

| Status | Meaning |
|---|---|
| ok | Operation completed, no changes needed |
| changed | Operation completed, state was modified |
| skipped | State already correct, nothing to do |
| failed | Non-recoverable failure |

Structured results allow Temporal to determine retry vs failure **without parsing raw logs**.

### §6.3 Error Surfacing Contract (external APIs)

Activities that call an external API (Tailscale, GitHub, 1Password, Vault, Proxmox, ArgoCD, etc.) MUST parse the HTTP response body on error and surface the external system's actual error text. `400 Bad Request` is not an acceptable error message when the response body says something specific.

Every such activity, on non-2xx response:

1. Reads the response body and parses the external system's error field (most systems return `{"message": "..."}` or similar).
2. Constructs an `ActivityResult` with:
   - `status = "failed"`
   - `error_code` — a specific code from the external system's controlled vocabulary (e.g., `TAILSCALE_OAUTH_SCOPE_INSUFFICIENT`, `GITHUB_APP_NOT_INSTALLED`, `VAULT_SEALED`)
   - `details["<system>_message"]` — the external system's exact error string (`details.tailscale_message`, `details.github_message`, `details.vault_message`, etc.)
   - `details["http_status"]` — the numeric HTTP status code
   - `details["remediation"]` — a one-line hint pointing at the operator step or workflow preflight that would have prevented this

### §6.4 Error-code vocabulary discipline

Each external-system integration defines its own controlled error-code vocabulary in its per-system standard. Current vocabularies:

- **Tailscale** — `TAILSCALE_*` codes per [Tailscale Standard §7](../tailscale/tailscale_standard.md)
- **GitHub App** — `GITHUB_*` codes per [GitHub Automation Standard](../github-automation/github_standard.md)
- **Vault** — `VAULT_*` codes per [Vault Standard](../secrets/vault_standard.md)
- **ArgoCD** — `ARGOCD_*` codes per [ArgoCD Standard §13](../argocd/argocd_standard.md)
- **Container Clustering (reconciler)** — `CLUSTER_RECONCILE_*` codes per [Container Clustering Standard §5.7](../platform_deployment/container_clustering_standard.md)
- **seed_cluster_secret (credential-ingress LEGO)** — `SEED_*` codes per [Credential Lifecycle Standard §7.2](../secrets/credential_lifecycle.md)
- **kubectl (imperative K8s ops)** — `KUBECTL_*` codes per [Kubernetes Deployment Standard §6c](../kubernetes/k8s_deployment_standard.md)
- **Workload composer + build-step executors (snap/systemd)** — `WORKLOAD_RECONCILE_*` + `SNAP_*` + `SYSTEMD_*` codes per [VM Management Standard §5.2](../platform_deployment/vm_management_standard.md)
- **Cluster registration / kubeconfig register** — `KUBECONFIG_REGISTER_*` codes (12, all terminal) per [Container Clustering Standard §5.8](../platform_deployment/container_clustering_standard.md)

Error codes MUST be `UPPER_SNAKE_CASE` with a system prefix. Each code maps to exactly one fire-path — not overloaded across multiple triggers; vagueness creates false triage paths.

Retry semantics are encoded by error-code, not by workflow-level retry-all rules:

- **Rate-limit codes** (`*_RATE_LIMITED`): retryable with exponential backoff + jitter.
- **API-availability codes** (`*_UNAVAILABLE` / `*_5XX`): retryable with backoff. *(Suffix-based; scoped to **external-API** availability. Exception: a code expressing a **control-plane-reachability verdict** that the activity already bounded-retried in-process — e.g. `CLUSTER_RECONCILE_CONTROL_PLANE_UNAVAILABLE` ([Container Clustering §5.7](../platform_deployment/container_clustering_standard.md)) or `SEED_CLUSTER_ACCESS_UNAVAILABLE` ([Credential Lifecycle §7.2](../secrets/credential_lifecycle.md)) — is **terminal**: it halts for operator attention, since a Temporal-level retry would just re-halt. **Second exception — vendor-capability absence:** a code reporting that the external system does not expose the endpoint at all (e.g. `FIREWALL_CAPABILITY_UNAVAILABLE` — the console version has no reservation-read API) is **terminal**. Retrying cannot make a vendor endpoint exist, and the condition is a property of the deployed system version, not a transient state. The suffix reads retryable in both exceptions; the semantics govern, and an activity emitting a terminal `*_UNAVAILABLE` names the exception it falls under in its code module.)*
- **Auth / permissions / not-found codes**: terminal. Temporal's retry backoff exhausts quickly and the workflow fails at the originating step.
- **Unexpected codes** (`*_UNEXPECTED`): terminal. The raw response body MUST NOT be placed in `details` by default. External-system bodies routinely carry infrastructure detail — MAC addresses, IPs, hostnames, network topology — and `details` persists in durable Temporal event history, readable by anyone with Temporal-UI access. Surface the parsed message field in `details.<system>_message` as for every other code, and capture the raw body only in a separate `details.raw_response`, gated behind an explicit verbose/debug flag that is off in normal operation.

Bare HTTP status codes can't distinguish terminal from transient (a 404 on the wrong repo is terminal; a 404 on a race with eventual-consistency is transient). The per-system `error_code` vocabulary is the only signal that crosses the workflow boundary intact and lets the retry layer make the right call.

------------------------------------------------------------------------

## §7 Activity Design Patterns

### §7.1 Idempotency

Every activity must be idempotent:

```python
@activity.defn(name="create_folder")
async def create_folder(path: str) -> ActivityResult:
    if Path(path).exists():
        return ActivityResult(status="skipped", details="Already exists")
    # Create folder...
    return ActivityResult(status="changed", details="Created")
```

For the broader idempotency-pattern catalog (check-then-act, conditional update, compare-and-swap) and the cleanup-on-failure discipline that pairs with it, see [Stateful Patterns Standard §4](./stateful_patterns.md) and §6 of that standard.

### §7.2 Self-validation

Activities must validate their own success:

- Verify operations actually succeeded
- Check final state matches desired state
- Return "failed" if validation doesn't pass
- Never fail silently

### §7.3 Error handling

- Handle expected errors gracefully
- Return structured results (not just bool)
- Log errors with context per [Logging Standard §4.5](../logging/logging_standard.md) (`exc_info=True` mandatory)
- Use specific `error_code`s per §6.4

### §7.4 Retry policies

Define retry policies per activity:

- Network operations: many retries, exponential backoff
- Database operations: fewer retries, shorter timeout
- Idempotent operations: more retries allowed

### §7.5 Identities are explicit, never derived (binding)

**Where an explicit identity value is available — K8s namespace, destination cluster, Temporal namespace, secret namespace — code MUST use the explicit value, never derive it from a convenience source.** Two orthogonal axes with confusingly-similar names are the trap; deriving one from the other is the bug.

**Worked example (the rule's origin):** locating a worker pod MUST use the worker's explicit **K8s namespace** (e.g. `skyy-command`), never its **Temporal namespace** (e.g. `skyycommand-dev`). These are independent configuration dimensions — a Temporal namespace is a logical workflow partition; a K8s namespace is a deployment location — and one happening to resemble the other does not make it derivable. The explicit K8s-namespace config field lives in the [Worker Deployment Standard](./worker_deployment_standard.md) (`provision_worker_namespace` and peers).

**Same class, more instances:** an activity that derives a destination kubeconfig from `.spec.destination.name` instead of an explicit destination-cluster config is the same anti-pattern. State and apply the rule generally — wherever a resource is located/targeted by an identity, the identity is an explicit input, not a derivation. *(Known live instance to bring into conformance: `argocd_sync` destination-kubeconfig derivation — tracked as a conformance loose end.)*

**Breaking it looks like:** a `kubectl`/pod-location call namespaced by the Temporal namespace; a kubeconfig selected by deriving from `.spec.destination.*`; any "these names are usually the same, so derive B from A" shortcut across two orthogonal identity axes.

------------------------------------------------------------------------

## §8 Configuration Management Pattern

### §8.1 The pattern

```
Workflow Start (UI/Script) → Input: { }
         ↓
Layer 1: Workflow calls load_genesis_mdc_config (semantic wrapper)
         ↓
Layer 3: Wrapper load_genesis_mdc_config → delegates to load_mdc_config()
  - Generic reads config.yaml (reusable across workflows)
  - Returns raw config dict in ActivityResult
         ↓
Layer 1: Workflow calls helper.validate_genesis_config()
         ↓
Layer 2: Helper: validate_genesis_config(raw_config)
  - Pure function (no I/O, no side effects)
  - Validates Genesis-specific requirements
  - Returns structured Genesis config dict
         ↓
Layer 1: Workflow calls helper.compile_execution_plan()
         ↓
Layer 2: Helper: compile_execution_plan(validated_config)
  - Produces execution plan (steps/specs per phase)
  - Each step has "activity" key, "input" = serialized semantic input model, plus timeouts/retries/etc.
         ↓
Layer 1: Workflow iterates execution plan, resolves each step's string key via ACTIVITY_MAP, calls execute_activity(callable, args=[step["input"]], ...)
         ↓
Layer 3: Semantic wrappers (one payload per call, unpack → generic executor)
```

### §8.2 Key rules

- **Workflow input is minimal or empty** — just start the workflow
- **First activity in curated workflows** loads configuration from `config.yaml` via a semantic wrapper
- **Helper validates and structures config** — workflow-specific validation
- **Subsequent activities receive one structured payload per step**
- **Secrets are loaded by a separate activity** (never in workflow input/history)
- Enables both **UI start** (empty input) and **script start** (same behavior)

### §8.3 Secrets pattern

```
Secrets Activity (when needed): load_secrets()
  - Reads .env or Vault
  - Returns only what's needed
  - Never in workflow input (safe)
  - Helper can validate/transform secrets if needed
```

### §8.4 Environment separation (DEV/PROD/TEST)

| Component | How It Works |
|---|---|
| **Config Source** | `config.yaml` → `temporal.deployment_env` |
| **Namespaces** | `skyycommand-dev`, `skyycommand-prod`, `skyycommand-test` |
| **Task Queues** | `provision-dev`, `provision-prod`, `provision-test` (and per-domain equivalents per [Worker Deployment Standard §2](./worker_deployment_standard.md)) |
| **Docker Compose** | Base files + `{env}.override.yml` |

------------------------------------------------------------------------

## §9 Workflow Design Patterns

### §9.1 Three-layer pattern

Every workflow follows the §3 three-layer architecture:

```python
# GENESIS_ACTIVITY_MAP: dict[str, Callable] — string keys from helper → registered @activity.defn callables
# (Genesis imports this from genesis_activities, often aliased as ACTIVITY_MAP in the workflow module.)

@workflow.defn(name="GenesisWorkflow")
class GenesisWorkflow:
    @workflow.run
    async def run(self, input_data: dict = None) -> dict:
        # Step 1: Load raw config (Layer 3: semantic wrapper — first hop from workflow)
        config_result = await workflow.execute_activity(
            load_genesis_mdc_config,
            start_to_close_timeout=timedelta(minutes=1),
        )
        raw_config = config_result.artifacts["config"]

        # Step 2: Validate and structure (Layer 2: Helper — pure function)
        validated_config = genesis_helper.validate_genesis_config(raw_config)

        # Step 3: Compile execution plan (Layer 2: Helper — pure function)
        execution_plan = genesis_helper.compile_execution_plan(validated_config)

        # Step 4: Execute plan (Layer 1) — helper emits string keys; workflow resolves callables
        ACTIVITY_MAP = GENESIS_ACTIVITY_MAP
        for step in execution_plan["phases"]["phase0"]["steps"]:
            activity_func = ACTIVITY_MAP.get(step["activity"])
            if not activity_func:
                raise ValueError(f"UNKNOWN_ACTIVITY: {step['activity']}")

            result = await workflow.execute_activity(
                activity_func,
                args=[step["input"]],
                start_to_close_timeout=timedelta(seconds=step["timeout_seconds"]),
            )
```

**Rule:** `execute_activity`'s first argument must always be a **registered activity callable** (the object resolved from `ACTIVITY_MAP`), never the helper's string key. The **activity payload** is **one value**: `step["input"]` (dict serializable from the helper's input model). Real Genesis code adds `_execute_phase`, per-step `retry_policy`, and may record `UNKNOWN_ACTIVITY` on the step instead of raising — the snippet above is the canonical resolution pattern.

### §9.2 Helper pattern

Helpers are pure functions that compile intent into execution plans:

```python
# modules/common/provision/genesis_helper.py
import dataclasses
from dataclasses import dataclass
from typing import Any, Dict, List, Union

@dataclass
class CreateDesiredStateRepoDirectoryInput:
    path_or_paths: Union[str, List[str]]
    owner: str
    group: str
    permissions: int
    file_permissions: int

def validate_genesis_config(raw_config: dict) -> dict:
    """Pure function - validates and structures config."""
    # Validation logic...
    return structured_config

def compile_execution_plan(validated_config: dict) -> dict:
    """Pure function - compiles execution plan."""
    create_repo_inp = CreateDesiredStateRepoDirectoryInput(
        path_or_paths=path,
        owner=owner,
        group=group,
        permissions=directory_permissions,
        file_permissions=file_permissions,
    )
    return {
        "phases": {
            "phase0": {
                "steps": [
                    {
                        "name": "create_repo_folder",
                        "activity": "create_desired_state_repo_directory",
                        "input": dataclasses.asdict(create_repo_inp),
                        "timeout_seconds": 300,
                    },
                    # ... more steps, each with its own *Input model → "input" dict
                ],
            },
        },
    }
```

- **`"activity"`** is always a **string key** into `ACTIVITY_MAP`, never a Python callable.
- **`"input"`** is always the **serialized semantic input model** for that wrapper (JSON-friendly dict). Use `model_dump(mode="json")` / `asdict()` / equivalent.
- Steps may include additional fields (`retry_policy`, `scaffold_context`, `env_from_step`, …) beside `"input"`, as in `genesis_helper.py`.

### §9.3 Starting other workflows

- Use child workflow APIs from workflow code
- Do NOT instantiate Temporal clients in workflow code
- Activities don't start workflows (activities do external work only)
- Cross-worker dispatches MUST explicitly target the child's task queue per [Worker Deployment Standard §1.4](./worker_deployment_standard.md) and §6.2 of that standard

```python
# In workflow code
reconcile_handle = await workflow.start_child_workflow(
    CoreReconcileWorkflow.run,
    id="core-reconcile-1",
    task_queue="reconcile-dev",      # explicit, per Worker Deployment Standard §1.4
)
```

### §9.4 Step-execution helper parity (binding)

Workflows that use **multiple step-execution helpers** (activity steps, child-workflow steps, future executor types) MUST produce **shape-compatible failure dicts** across all helpers. The workflow's `run()` consumes failure information from every helper through a shared surfacing path; asymmetric shapes IS a bug, even when unit tests mock at the wrong level and don't catch it.

**Binding key set for failure-dict parity:** at minimum, every step-execution helper MUST propagate the following keys when a step fails:

- `error` — human-readable message
- `error_code` — controlled-vocabulary code per [§6.3](#63-error-surfacing-contract-external-apis)
- `details` — structured dict per §6.3
- `artifacts` — any artifacts the step produced before failing
- `failed_phase` — which workflow phase the step ran in (when applicable)
- `failed_step` — which specific step inside the phase

Workflow-specific extensions are permitted; the binding set is the minimum.

**When adding a new step type or modifying an existing one, audit ALL sibling step paths for parity** on the keys above. The failure surface is consumed at one place (`run()`'s failure-surfacing block); divergence between paths produces silent drops.

**Surfaced from:** PR #65's `_execute_activity_step` error_code-drop bug. The activity-step path in `lib/temporal/modules/common/provision/cluster_provision_workflow.py` was silently dropping `result.error_code` before reaching `run()`; the child-workflow step path was correct. The asymmetry was invisible to unit tests that mocked the helper output but didn't assert the failure-dict shape consumed by `run()`.

**Parity-test pattern (recommended for any workflow with multiple step types):** alongside the workflow's behavior tests, add a parity test that constructs a failing result for each helper type and asserts the consumed failure dict carries every binding key. The test mocks at the helper-return boundary, not deeper — that's the level where asymmetry actually lives.

```python
# Parity test sketch (pseudocode)
@pytest.mark.parametrize("helper", ["activity_step", "child_workflow_step"])
def test_failure_dict_parity(helper):
    failing_result = make_failing_result_for(helper)
    failure_dict = workflow._collect_failure_keys(failing_result)
    for key in ("error", "error_code", "details", "artifacts", "failed_phase", "failed_step"):
        assert key in failure_dict, f"{helper} drops {key}"
```

**Breaking it looks like:** a workflow with two helper paths (e.g., `_execute_activity_step` + `_execute_child_workflow_step`) where one path's failure dict carries `error_code` but the other path's doesn't — observable when a failure on the second path produces a workflow result with `error_code: None` despite the underlying step having returned a controlled error code. Asymmetric propagation is the bug; the fact that it doesn't surface in unit tests that mock helper-level results is the warning sign.

------------------------------------------------------------------------

## §10 Directory Structure

```
activities/                       # Domain-organized activities (reusable library)
├── config/                       # Configuration loading (FIRST activity in most workflows)
├── identity/                     # Identity & configuration management
├── networking/                   # Network configuration (Tailscale, UFW)
├── secrets/                      # Secrets management (read .env, Vault integration)
├── app_layer/                    # Application deployment (Django, migrations)
├── observability/                # Monitoring and alerting
├── provisioning/                 # Infrastructure provisioning
├── runtime/                      # VM-level operations (package install, file ops, systemd)
├── ansible/                      # Generic Ansible execution (playbooks) — Layer 3b
├── terraform/                    # Generic Terraform execution (future) — Layer 3b
├── argocd/                       # Generic Argo CD execution (future) — Layer 3b
└── docker/                       # Docker/Compose operations

modules/                          # Workflow modules (domain-organized)
├── common/                       # Common module — cross-cutting workflows (Genesis, reconcile, etc.)
│   ├── provision/                # Provisioning workflow (Day-0 → Day-1 bootstrap)
│   │   ├── genesis_workflow.py   # Workflow orchestration (Layer 1)
│   │   ├── genesis_helper.py     # Helper (compiler) — validation, execution plan, input dataclasses (Layer 2)
│   │   └── genesis_activities.py # Semantic activity wrappers for Genesis only (Layer 3a)
│   ├── reconcile/                # Reconciliation workflow (future)
│   ├── version_watch/            # Version watching workflow (future)
│   └── upgrade_orchestrator/     # Upgrade orchestration workflow (future)
├── infra/                        # Infra module — physical host and OS state (future)
├── vm/                           # VM module — virtual machine orchestration (future)
├── container/                    # Container module — container workload orchestration (future)
├── service/                      # Service module — internal services (future)
└── workload/                     # Workload module — customer workloads (future)

common/                           # Shared utilities and types
├── types/                        # Shared type definitions (ActivityResult, config types)
├── utils/                        # Shared utility functions
├── clients/                      # Wrappers for external systems (docker, vault, etc.)
└── constants.py                  # Shared constants
```

Note: Workflow folders are named by **what they do**, not by workflow type. Folders are only created when workflows are implemented.

------------------------------------------------------------------------

## §11 Creating a New Activity

### §11.1 Generic executor (reusable)

1. **Choose the domain** under `activities/` (e.g., `ansible/`, `docker/`, `runtime/`)
2. **Create the activity file** with workflow-agnostic parameters
3. **Implement with idempotency and structured `ActivityResult`**
4. **Export in domain `__init__.py`**
5. **Register in worker** (if invoked directly; otherwise only wrappers may be registered)

### §11.2 Semantic wrapper (workflow-specific UI name)

1. **Define the input model** in `{name}_helper.py` by default (**one class per semantic activity**, name aligned with the activity). Extract to `{name}_activity_inputs.py` only if the helper becomes unwieldy.
2. **Compile** instances in the helper and set **`"input": model_dump() / asdict(...)`** on each plan step.
3. **Add a thin function** to `modules/{module}/{purpose}/{name}_activities.py` with `@activity.defn(name="meaningful-kebab-case")` and a **single `dict` payload** parameter; **validate/reconstruct** the model at the start.
4. **Unpack** the model and **delegate** to the generic executor (no copy-paste of subprocess/tool logic).
5. **Add the `ACTIVITY_MAP` key** used by the helper's `"activity"` field — wrapper callable.
6. **Register the wrapper** on the worker (and drop generic registration once no plan references it).

------------------------------------------------------------------------

## §12 File Locations

| File | Purpose |
|------|---------|
| `/opt/skyy-net/skyy-command/config.yaml` | All settings (non-secrets) |
| `/opt/skyy-net/skyy-command/.env` | Secrets only |
| `activities/config/load_mdc_config.py` | Generic config loading activity — reusable; curated workflows call a `{name}_activities` wrapper that delegates here |
| `modules/{module}/{purpose}/{name}_helper.py` | Workflow helper (compiler) — validation, execution plan, and per-step input dataclasses |
| `modules/{module}/{purpose}/{name}_activity_inputs.py` | **Optional** extraction: one input type per semantic activity when the helper grows too large |
| `modules/{module}/{purpose}/{name}_activities.py` | Workflow-scoped semantic wrappers — `@activity.defn(name=...)`; one parameter (payload); unpack and delegate to `activities/` |
| `activities/secrets/load_secrets.py` | Secrets loading activity |

------------------------------------------------------------------------

## §13 Related Documents

- [Temporal Worker Deployment Standard](./worker_deployment_standard.md) — worker segmentation, images, task queues, dispatch verification
- [Temporal Stateful Patterns Standard](./stateful_patterns.md) — fresh-MDC bootstrap, workflow retirement, idempotent writes, stage-coupling, cleanup-on-failure
- [Architecture Standard](../../architecture/architectural_standard.md) — overall MDC architecture, guardrails, ownership; Guardrail 4 covers execution-paths
- [Ansible Standard](../ansible/ansible_standard.md) — Ansible role design and invocation patterns
- [SSH Key Management Standard](../remote-access/ssh_key_management.md) — deploy key conventions
- [YAML Editing Standard](../yaml/yaml_editing_standard.md) — `ruamel.yaml` round-trip mode for writable YAML
- [Logging Standard](../logging/logging_standard.md) — worker stdout conventions and AI-first diagnostic interface
