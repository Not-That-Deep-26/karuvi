# KARUVI ARCHITECTURE RECONSTRUCTION ENGINE

## Complete Implementation Specification for Claude Code

**Project:** Karuvi  
**Language:** Python  
**Primary goal:** Extend the existing deterministic code analysis system into a graph-based architecture reconstruction and beginner-friendly codebase exploration system.

---

# TABLE OF CONTENTS

1. Mission and Product Definition
2. Core Design Philosophy
3. Non-Goals
4. Existing Repository Reconnaissance
5. Required Deliverables
6. High-Level System Architecture
7. Existing Pipeline Integration
8. Data Contracts
9. Symbol Graph Requirements
10. Module Graph Construction
11. Relationship Preservation
12. Module Metadata
13. Structural Boundary Detection
14. Graph Community Detection
15. Component Reconstruction
16. Component Confidence
17. Component Graph Construction
18. Structural Role Detection
19. Entry Point Detection
20. Architectural Flow Detection
21. Architecture Model
22. Deterministic Explanation Layer
23. JSON Serialization
24. Frontend / HTML Architecture View
25. Progressive Disclosure UX
26. CLI Integration
27. Test Fixtures
28. Unit Tests
29. Integration Tests
30. Performance Constraints
31. Error Handling
32. Logging and Debugging
33. Implementation Order
34. Git Commit Plan
35. MVP Acceptance Criteria
36. Explicit Non-Goals
37. Future Extensions

---

# 1. MISSION

Karuvi currently analyzes source code and constructs deterministic representations of program structure and relationships.

The objective of this implementation is to add a new layer:

```text
SOURCE CODE
    ↓
TREE-SITTER PARSING
    ↓
DECLARATIONS + REFERENCES
    ↓
SYMBOL RESOLUTION
    ↓
RESOLVED SYMBOL GRAPH
    ↓
MODULE GRAPH
    ↓
COMPONENT DISCOVERY
    ↓
COMPONENT GRAPH
    ↓
ARCHITECTURE MODEL
    ↓
BEGINNER-FRIENDLY EXPLORATION
```

The important conceptual distinction is:

> The graph is evidence. The architecture model is the product.

Karuvi must not simply display a giant dependency graph.

Karuvi must progressively transform low-level program relationships into increasingly understandable representations.

The user should be able to navigate:

```text
Repository
    ↓
Architecture
    ↓
Component
    ↓
Module
    ↓
Symbol
    ↓
Source Code
```

---

# 2. PRODUCT DEFINITION

The system being implemented is a deterministic architecture reconstruction engine.

Given an unfamiliar Python repository, Karuvi should answer structurally grounded questions such as:

```text
What are the major groups of code in this repository?

Which files are strongly related?

Which groups of files form architectural components?

How do those components depend on one another?

Where are likely structural entry points?

Which modules act as bridges between different parts of the system?

What are the major dependency flows?

How can I progressively navigate from the whole repository
to the exact symbols implementing a behaviour?
```

The system should NOT claim perfect semantic understanding.

It should make claims proportional to available structural evidence.

For example:

Good:

```text
These modules form a tightly connected dependency community.
```

Good:

```text
This module structurally connects several otherwise
separate regions of the repository.
```

Bad:

```text
This module is definitely responsible for user authentication.
```

unless such a conclusion is supported by explicit deterministic evidence.

---

# 3. CORE DESIGN PHILOSOPHY

## Principle 1: Do not replace the existing analysis pipeline

The existing Karuvi parser, declaration extractor, pointer/reference resolver, UUID system, and graph construction logic must be preserved.

The architecture engine consumes their output.

Do not rewrite working parsing logic.

The architecture engine begins at:

```text
RESOLVED SYMBOL GRAPH
```

---

## Principle 2: Architecture is derived by abstraction

The system should repeatedly aggregate the graph.

```text
Symbols
    ↓
Modules
    ↓
Components
    ↓
Architecture
```

Each level must remain traceable to the level below it.

This means the following mappings must always be recoverable:

```text
Component
    ↓
Modules

Module
    ↓
Symbols

Symbol
    ↓
Source location
```

No abstraction should become disconnected from its evidence.

---

## Principle 3: Folder structure is evidence, not truth

This is important.

The following assumption is prohibited:

```text
folder == architecture component
```

Instead:

```text
folder == initial structural hypothesis
```

Graph relationships can:

```text
support the hypothesis
split the hypothesis
merge hypotheses
contradict the hypothesis
```

---

## Principle 4: Deterministic first

The architecture model must not require:

```text
LLMs
embeddings
semantic similarity models
external APIs
cloud services
```

The initial prototype should operate completely from deterministic repository evidence.

---

## Principle 5: Beginner complexity should be progressively disclosed

Do not expose:

```text
10,000 graph nodes
```

as the first user experience.

Instead:

```text
Architecture

→ Component

→ Module

→ Symbol
```

The system should begin with the simplest useful abstraction and allow the user to drill down.

---

# 4. PHASE ZERO — REPOSITORY RECONNAISSANCE

Before writing implementation code, inspect the existing repository.

Do not assume file names, graph formats, node metadata, or architecture.

Perform the following reconnaissance.

---

## 4.1 Inspect repository structure

Identify:

```text
Parser modules
Tree-sitter integration
Declaration extraction
Reference extraction
Pointer resolution
UUID generation
Import resolution
Graph construction
Existing output formats
Existing CLI entry points
Existing HTML/tree visualizer
Tests
Dependencies
```

Produce an internal implementation map.

Example:

```text
Existing parser:
    karuvi/parser/...

Symbol extraction:
    karuvi/returns.py

Reference resolution:
    karuvi/pointers.py

Graph generation:
    karuvi/get_tree.py

Visualizer:
    ...

CLI:
    ...
```

The exact structure must be discovered from the repository rather than assumed.

---

## 4.2 Inspect graph format

Determine:

```text
Which graph library is used?

Is the graph directed?

What is a node ID?

Are UUIDs node IDs?

What attributes exist on nodes?

How are file paths represented?

How are edge types represented?

How are imports represented?

How are calls represented?

How are unresolved references represented?
```

Document the existing graph contract internally.

Example desired understanding:

```python
graph.nodes[node_id] == {
    "uuid": "...",
    "name": "authenticate",
    "file": "services/auth.py",
    "kind": "function"
}
```

But do not assume this exact structure.

Adapt all implementation to the actual repository.

---

## 4.3 Determine architecture integration point

Find the point where Karuvi has a graph containing resolved relationships.

The architecture pipeline must begin immediately after that point.

The intended integration should conceptually be:

```python
symbol_graph = existing_analysis(repository)

architecture_model = ArchitectureAnalyzer(
    repository_root=repository_root
).analyze(symbol_graph)
```

Do not create a second parser.

Do not parse source files again if existing Karuvi data already contains the required information.

---

# 5. REQUIRED NEW PACKAGE

Create a new package unless the existing project architecture strongly suggests a better location.

Preferred structure:

```text
karuvi/
├── architecture/
│   ├── __init__.py
│   │
│   ├── models.py
│   ├── analyzer.py
│   ├── module_graph.py
│   ├── boundaries.py
│   ├── communities.py
│   ├── components.py
│   ├── component_graph.py
│   ├── roles.py
│   ├── entrypoints.py
│   ├── flows.py
│   ├── metrics.py
│   ├── documentation.py
│   ├── serialization.py
│   └── exceptions.py
│
└── tests/
    ├── architecture/
    │   ├── test_module_graph.py
    │   ├── test_boundaries.py
    │   ├── test_communities.py
    │   ├── test_components.py
    │   ├── test_component_graph.py
    │   ├── test_roles.py
    │   ├── test_entrypoints.py
    │   ├── test_flows.py
    │   └── test_integration.py
    │
    └── fixtures/
        ├── simple_layered/
        ├── split_utils/
        ├── merged_components/
        └── cycles/
```

Do not blindly force this structure if the repository already has a coherent package convention.

Follow existing conventions where reasonable.

---

# 6. DATA MODELS

Use Python dataclasses.

Do not pass arbitrary dictionaries throughout the architecture layer.

Create explicit models.

---

## 6.1 Module model

```python
@dataclass
class Module:
    id: str
    path: str

    symbols: list[str]

    symbol_count: int

    incoming_modules: list[str]
    outgoing_modules: list[str]

    incoming_weight: int
    outgoing_weight: int

    metadata: dict[str, Any] = field(default_factory=dict)
```

The `id` should be deterministic.

Recommended:

```text
normalized repository-relative path
```

Example:

```text
services/auth.py
```

Do not generate random UUIDs for architecture entities unless the existing project convention requires UUIDs.

Architecture analysis should be reproducible.

---

## 6.2 Component model

```python
@dataclass
class Component:
    id: str
    name: str

    modules: list[str]

    discovery_methods: list[str]

    confidence: float

    metadata: dict[str, Any] = field(default_factory=dict)
```

Possible discovery methods:

```text
STRUCTURAL_BOUNDARY
GRAPH_COMMUNITY
BOUNDARY_AND_COMMUNITY
SINGLETON
```

---

## 6.3 Architecture relationship

Create an explicit representation if useful.

```python
@dataclass
class ArchitectureRelationship:
    source: str
    target: str

    weight: int

    relationship_types: dict[str, int]

    evidence: dict[str, Any]
```

Example:

```python
ArchitectureRelationship(
    source="api",
    target="services",
    weight=47,
    relationship_types={
        "CALL": 31,
        "IMPORT": 16
    }
)
```

---

## 6.4 Architecture model

```python
@dataclass
class ArchitectureModel:

    repository_root: str

    modules: dict[str, Module]

    components: dict[str, Component]

    module_graph: Any

    component_graph: Any

    entry_points: list[str]

    roles: dict[str, str]

    flows: list[Any]

    metadata: dict[str, Any]
```

---

# 7. MODULE GRAPH CONSTRUCTION

This is the first mandatory implementation milestone.

The input is the existing resolved symbol graph.

The output is a weighted directed module graph.

---

## 7.1 Definition

Given:

```text
Symbol A in file X
        ↓
Symbol B in file Y
```

construct:

```text
File X
    ↓
File Y
```

---

## 7.2 Example

Input:

```text
api/login.py::login()
        │ CALL
        ▼
services/auth.py::authenticate()
        │ CALL
        ▼
repositories/users.py::get_user()
```

Output:

```text
api/login.py
        │
        ▼
services/auth.py
        │
        ▼
repositories/users.py
```

---

## 7.3 Node construction

Every source file represented by at least one symbol should become a module node.

For every symbol node:

1. Extract repository-relative file path.
2. Normalize path.
3. Create module node if absent.
4. Associate symbol ID with module.

Example metadata:

```python
{
    "path": "services/auth.py",
    "symbols": [
        "uuid-a",
        "uuid-b",
        "uuid-c"
    ],
    "symbol_count": 3
}
```

---

## 7.4 Edge construction

For every symbol edge:

```text
source_symbol → target_symbol
```

determine:

```text
source_module
target_module
```

If:

```text
source_module != target_module
```

add or aggregate:

```text
source_module → target_module
```

---

## 7.5 Edge aggregation

Multiple symbol relationships between the same two modules must aggregate.

Example:

```text
login()
validate()
logout()

all reference:

db.py
```

Output:

```text
auth.py
    │
    │ weight = 3
    ▼
db.py
```

Do not create three duplicate graph edges.

Use edge metadata.

Example:

```python
{
    "weight": 3,

    "relationship_types": {
        "CALL": 2,
        "IMPORT": 1
    },

    "symbol_edges": [
        {
            "source": "...",
            "target": "...",
            "type": "CALL"
        }
    ]
}
```

For large repositories, storing every symbol edge may become expensive.

For the MVP, preserve sufficient evidence to drill down.

If necessary, store symbol edge references rather than copies.

---

## 7.6 Intra-module relationships

Do not create module graph edges for:

```text
symbol A → symbol B
```

when both belong to:

```text
same module
```

Instead track them as internal connectivity metadata.

Example:

```python
module_metadata["internal_relationship_count"] += 1
```

This is useful later.

---

## 7.7 Required function

Implement a clean public function.

Conceptually:

```python
def build_module_graph(
    symbol_graph: nx.DiGraph,
    repository_root: Path
) -> nx.DiGraph:
    ...
```

Adapt graph type if the existing graph implementation differs.

---

# 8. PATH NORMALIZATION

Path normalization is critical.

Architecture nodes must not accidentally duplicate because of:

```text
src/auth.py

./src/auth.py

/home/user/project/src/auth.py
```

Create one normalization function.

Conceptually:

```python
def normalize_module_path(
    file_path: str | Path,
    repository_root: Path
) -> str:
```

Requirements:

1. Resolve relative/absolute paths.
2. Convert to repository-relative path when possible.
3. Normalize separators.
4. Avoid platform-specific backslash inconsistencies.
5. Return deterministic strings.

Example:

```text
/home/tarun/project/src/auth.py
```

becomes:

```text
src/auth.py
```

Every architecture module identifier must use this normalization function.

---

# 9. MODULE GRAPH METADATA

After graph construction calculate:

```text
symbol_count

internal_relationship_count

external_relationship_count

in_degree

out_degree

weighted_in_degree

weighted_out_degree
```

Do not calculate expensive global graph metrics here.

Keep basic module metadata separate from global analysis.

---

# 10. STRUCTURAL BOUNDARY DETECTION

Create:

```text
boundaries.py
```

The goal is to derive initial component candidates from repository structure.

---

## 10.1 Input

```text
src/api/users.py
src/api/auth.py

src/services/users.py
src/services/auth.py
```

---

## 10.2 Initial result

```text
api
services
```

These are not final components.

They are structural candidates.

---

## 10.3 Ignore generic directories

Support a configurable ignore set.

Initial defaults:

```python
IGNORED_BOUNDARIES = {
    "src",
    "lib",
    "tests",
    "test",
    "__pycache__",
    "build",
    "dist"
}
```

Be conservative.

Do not assume every repository follows the same convention.

---

## 10.4 Boundary algorithm

For every module:

1. Get repository-relative path.
2. Remove filename.
3. Inspect parent directories.
4. Remove generic root directories.
5. Select the first meaningful package boundary.

Example:

```text
src/backend/auth/login.py
```

Potential candidates:

```text
backend
backend/auth
```

For MVP, support hierarchical boundaries.

Do not flatten every deep package into one name.

Represent:

```text
backend/auth
```

as a possible boundary.

---

# 11. GRAPH COMMUNITY DETECTION

Use graph connectivity as the second evidence source.

Recommended dependency:

```text
python-louvain
```

The implementation should handle the possibility that the dependency is unavailable.

Fail with a useful message or gracefully disable community analysis.

---

## 11.1 Convert graph

The module graph is directed.

Louvain operates on weighted undirected community structure.

Convert:

```python
undirected = module_graph.to_undirected()
```

However, preserve edge weight.

---

## 11.2 Parallel directed edges

If both:

```text
A → B
```

and:

```text
B → A
```

exist, ensure the undirected edge represents combined or otherwise deterministic weight.

Do not silently lose structural evidence.

Document the chosen aggregation.

Recommended:

```text
undirected_weight = forward_weight + reverse_weight
```

---

## 11.3 Community function

Conceptually:

```python
def detect_communities(
    module_graph: nx.DiGraph
) -> dict[str, int]:
```

Expected output:

```python
{
    "services/auth.py": 0,
    "services/token.py": 0,

    "db/users.py": 1
}
```

---

## 11.4 Small graphs

Community detection may behave poorly for tiny graphs.

Handle:

```text
0 nodes
1 node
2 nodes
```

explicitly.

Do not allow exceptions to crash analysis.

---

# 12. COMPONENT RECONSTRUCTION

This is the core inference layer.

Inputs:

```text
Module graph

Structural boundaries

Graph communities
```

Output:

```text
Components
```

---

## 12.1 Component evidence

For every module determine:

```python
module_to_boundary[module]
module_to_community[module]
```

Example:

```text
auth.py

boundary:
services

community:
0
```

---

## 12.2 Agreement

If multiple modules share:

```text
same structural boundary
+
same graph community
```

create a high-confidence component candidate.

Example:

```text
services/auth.py
services/token.py
services/session.py
```

Boundary:

```text
services
```

Community:

```text
community 0
```

Result:

```text
Component:
services

Discovery:
BOUNDARY_AND_COMMUNITY
```

---

## 12.3 Folder splitting

Example:

```text
utils/
    auth.py
    date.py
    db.py
```

Suppose communities are:

```text
community 0:
auth.py
db.py

community 1:
date.py
```

Do not force all modules into:

```text
utils component
```

Allow:

```text
Component 0:
auth.py
db.py

Component 1:
date.py
```

The graph is allowed to split a structural boundary.

---

## 12.4 Cross-folder merging

Example:

```text
auth/
    login.py

sessions/
    token.py
    refresh.py
```

Suppose all modules form one strong graph community.

Allow:

```text
Component:
authentication/session
```

However, do not invent a semantic name.

For the MVP, use deterministic naming.

Example:

```text
auth + sessions
```

or:

```text
community-0
```

The UI can later provide a prettier display name.

---

# 13. COMPONENT NAMING

Do not use an LLM.

Initial naming strategy:

Priority order:

```text
1. Shared meaningful boundary name
2. Shared path prefix
3. Combined boundary names
4. community-N
```

Example:

```text
src/services/auth.py
src/services/token.py
```

becomes:

```text
services
```

If:

```text
auth/login.py
sessions/token.py
```

are merged:

```text
auth-sessions
```

is acceptable.

The name is less important than the structure.

---

# 14. COMPONENT CONFIDENCE

Confidence must be deterministic.

Do not pretend confidence is mathematically precise.

Use it as an evidence score.

---

## 14.1 Factors

Calculate:

```text
Structural Cohesion

Graph Cohesion

Boundary-Community Agreement
```

---

## 14.2 Structural cohesion

A candidate whose modules mostly share a meaningful boundary receives higher structural evidence.

---

## 14.3 Graph cohesion

Calculate:

```text
internal edge weight
/
total edge weight involving component modules
```

Conceptually:

```python
cohesion = internal_weight / (
    internal_weight + external_weight
)
```

Handle division by zero.

---

## 14.4 Agreement

If boundary grouping and community grouping strongly overlap, increase confidence.

Use a deterministic overlap measure.

A simple MVP approach:

```text
1.0 = complete agreement

0.5 = partial agreement

0.0 = no agreement
```

---

## 14.5 Final score

Initial formula:

```text
confidence =
    0.4 * structural_cohesion
  + 0.4 * graph_cohesion
  + 0.2 * agreement
```

Clamp:

```text
0.0 ≤ confidence ≤ 1.0
```

Document that this is a heuristic evidence score.

---

# 15. COMPONENT GRAPH

After assigning every module to a component, collapse the module graph.

Input:

```text
module A
    ↓
module B
```

Assignments:

```text
module A → API

module B → SERVICES
```

Output:

```text
API
 ↓
SERVICES
```

---

## 15.1 Algorithm

For every module graph edge:

```text
source_module → target_module
```

retrieve:

```text
source_component
target_component
```

If they differ:

```text
source_component → target_component
```

Aggregate weight.

---

## 15.2 Internal component edges

If:

```text
source_component == target_component
```

do not create a component graph self-edge.

Instead accumulate:

```text
internal_weight
```

inside component metadata.

---

## 15.3 Component edge metadata

Preserve:

```text
total_weight

relationship type counts

module relationship count
```

Example:

```python
{
    "weight": 37,

    "relationship_types": {
        "CALL": 29,
        "IMPORT": 8
    }
}
```

---

# 16. GRAPH METRICS

Create:

```text
metrics.py
```

Calculate global graph metrics once.

---

## 16.1 Required module metrics

```text
in_degree

out_degree

weighted_in_degree

weighted_out_degree

betweenness_centrality

pagerank

reachable_descendant_count
```

---

## 16.2 Strongly connected components

Calculate:

```python
nx.strongly_connected_components(module_graph)
```

Cycles are important architectural information.

Example:

```text
A → B → C → A
```

This should not crash entry-point or flow detection.

Record cycles as:

```text
strongly connected regions
```

---

# 17. STRUCTURAL ROLE DETECTION

Create:

```text
roles.py
```

Roles are structural labels.

Do not claim semantic roles such as:

```text
authentication service
payment service
database layer
```

unless explicitly supported by naming.

---

## 17.1 Required roles

Initial roles:

```text
ENTRY_CANDIDATE

INTERMEDIARY

LEAF

BRIDGE

HUB

ISOLATED

CYCLE_MEMBER
```

---

## 17.2 ENTRY_CANDIDATE

Characteristics:

```text
low incoming dependency
high downstream reach
```

---

## 17.3 LEAF

Characteristics:

```text
high incoming relationships
low outgoing relationships
```

This is a structural downstream dependency.

---

## 17.4 INTERMEDIARY

Characteristics:

```text
meaningful incoming relationships
+
meaningful outgoing relationships
```

---

## 17.5 BRIDGE

High betweenness centrality relative to graph distribution.

Do not use hard-coded universal thresholds.

Use percentile-based classification where possible.

Example:

```text
top 10% betweenness
```

for sufficiently large graphs.

---

## 17.6 HUB

High weighted degree or PageRank.

Again use relative distribution rather than absolute numbers.

---

## 17.7 ISOLATED

```text
in_degree == 0
and
out_degree == 0
```

---

# 18. ENTRY POINT DETECTION

Create:

```text
entrypoints.py
```

The objective is to identify good structural starting points for exploration.

Do not claim these are necessarily runtime application entry points.

Call them:

```text
Structural Entry Points
```

---

## 18.1 Candidate heuristic

Calculate:

```text
incoming dependency score

outgoing reach

descendant count
```

A basic candidate may satisfy:

```text
low incoming dependencies
+
high reachable descendant count
```

---

## 18.2 Scoring

Recommended normalized score:

```text
entry_score =
    low_incoming_score
    *
    reach_score
```

Where:

```text
low incoming score increases as incoming degree decreases
```

and:

```text
reach score increases as reachable descendants increase
```

Return ranked candidates.

---

## 18.3 Evidence

Every result must contain evidence.

Example:

```json
{
    "module": "api/main.py",
    "entry_score": 0.91,

    "evidence": {
        "incoming_dependencies": 0,
        "reachable_modules": 24,
        "reachable_components": 6
    }
}
```

---

# 19. ARCHITECTURAL FLOW DETECTION

Create:

```text
flows.py
```

The objective is to produce understandable high-level paths.

Example:

```text
API
 ↓
SERVICES
 ↓
PERSISTENCE
```

---

## 19.1 Do not enumerate all paths

This can explode exponentially.

Never run unrestricted:

```text
all_simple_paths
```

over arbitrary repository graphs.

---

## 19.2 MVP flow strategy

For every structural entry candidate:

1. Determine reachable components.
2. Identify representative downstream components.
3. Compute shortest paths.
4. Limit maximum number of flows.
5. Deduplicate similar paths.

---

## 19.3 Cycle handling

Condense strongly connected components before generating high-level flows if necessary.

NetworkX provides:

```text
condensation
```

Conceptually:

```python
dag = nx.condensation(component_graph)
```

This transforms cycles into nodes in a DAG.

Use this for stable flow exploration.

---

## 19.4 Flow model

```python
@dataclass
class ArchitectureFlow:
    source: str
    target: str
    path: list[str]

    evidence: dict[str, Any]
```

---

# 20. MAIN ARCHITECTURE ANALYZER

Create:

```text
analyzer.py
```

Public API:

```python
class ArchitectureAnalyzer:

    def __init__(
        self,
        repository_root: Path,
        config: ArchitectureConfig | None = None
    ):
        ...

    def analyze(
        self,
        symbol_graph
    ) -> ArchitectureModel:
        ...
```

---

## 20.1 Required pipeline

The analyzer should execute:

```text
1. Validate symbol graph

2. Normalize paths

3. Build module graph

4. Calculate module metadata

5. Detect structural boundaries

6. Detect graph communities

7. Build components

8. Calculate component confidence

9. Build component graph

10. Calculate metrics

11. Detect structural roles

12. Detect structural entry points

13. Detect representative flows

14. Build ArchitectureModel

15. Return model
```

---

## 20.2 Pseudocode

```python
def analyze(symbol_graph):

    validate(symbol_graph)

    module_graph = build_module_graph(
        symbol_graph,
        repository_root
    )

    calculate_module_metadata(
        module_graph
    )

    boundaries = detect_boundaries(
        module_graph,
        repository_root
    )

    communities = detect_communities(
        module_graph
    )

    components = build_components(
        module_graph,
        boundaries,
        communities
    )

    calculate_component_confidence(
        module_graph,
        components
    )

    component_graph = build_component_graph(
        module_graph,
        components
    )

    metrics = calculate_metrics(
        module_graph
    )

    roles = detect_roles(
        module_graph,
        metrics
    )

    entry_points = detect_entry_points(
        module_graph,
        metrics
    )

    flows = detect_flows(
        component_graph,
        entry_points
    )

    return ArchitectureModel(...)
```

Every stage should be independently testable.

---

# 21. DETERMINISTIC DOCUMENTATION

Create:

```text
documentation.py
```

The documentation layer converts architecture data into human-readable explanations.

It must not perform semantic inference beyond available evidence.

---

## 21.1 Repository overview

Generate:

```markdown
# Repository Architecture

Karuvi analyzed:

- 42 modules
- 614 symbols
- 1,247 resolved relationships
- 7 candidate architectural components

## Structural Entry Points

- api/main.py
- api/users.py
```

All values must be derived from the model.

---

## 21.2 Component explanation

Template:

```markdown
## Component: Services

Contains 8 modules.

Discovery evidence:
- Modules share a structural package boundary.
- Modules form a graph dependency community.
- Internal connectivity is high relative to external connectivity.

Depends on:
- Persistence

Used by:
- API

Structural role:
- Intermediary
```

---

## 21.3 Beginner-friendly language

Convert:

```text
high betweenness centrality
```

into:

```text
This module connects multiple parts of the repository.
```

Convert:

```text
high descendant count
```

into:

```text
A large portion of the repository can be reached from here.
```

Do not expose mathematical terminology by default.

Advanced information can be included in a collapsible or secondary section.

---

# 22. JSON SERIALIZATION

Create:

```text
serialization.py
```

The architecture model must serialize cleanly.

Do not attempt to directly serialize NetworkX objects.

Convert graphs explicitly.

---

## 22.1 Graph JSON

Example:

```json
{
    "nodes": [
        {
            "id": "services",
            "type": "component",
            "module_count": 8
        }
    ],

    "edges": [
        {
            "source": "api",
            "target": "services",
            "weight": 47
        }
    ]
}
```

---

## 22.2 Full architecture output

```json
{
    "repository": "...",

    "statistics": {
        "symbols": 614,
        "modules": 42,
        "components": 7
    },

    "components": [],

    "module_graph": {},

    "component_graph": {},

    "entry_points": [],

    "roles": {},

    "flows": []
}
```

This JSON should become the contract between backend analysis and frontend visualisation.

---

# 23. FRONTEND GOAL

The frontend should not expose a raw graph as the default view.

The primary interaction is progressive exploration.

---

## Level 1: Repository Overview

Show:

```text
Repository

42 modules
7 architectural components

[ Explore Architecture ]

[ Find a Starting Point ]

[ Browse Code ]
```

---

## Level 2: Architecture

Show component-level graph.

Example:

```text
┌─────────────┐
│     API     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  SERVICES   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ PERSISTENCE │
└─────────────┘
```

Few nodes.

No symbol-level spaghetti.

---

## Level 3: Component

Click:

```text
SERVICES
```

Reveal:

```text
Services

Contains:

auth.py
users.py
payments.py

Depends on:

Persistence

Used by:

API
```

---

## Level 4: Module

Click:

```text
auth.py
```

Reveal:

```text
auth.py

Functions:

authenticate()
validate_token()
refresh_session()

Structural role:

Bridge
```

---

## Level 5: Symbol

Click:

```text
authenticate()
```

Reveal existing Karuvi symbol relationship visualization and source information.

---

# 24. FRONTEND IMPLEMENTATION RULE

Do not redesign or replace working frontend infrastructure unnecessarily.

Inspect the existing HTML/tree output.

Reuse:

```text
existing rendering
existing graph data
existing event handling
existing CSS patterns
```

where possible.

Add an architecture mode.

---

# 25. PROGRESSIVE DISCLOSURE

The UI should follow:

```text
LOW COMPLEXITY
      ↓
MORE DETAIL
      ↓
FULL IMPLEMENTATION DETAIL
```

Never default to maximum detail.

A beginner should be able to answer:

```text
What are the major parts?
```

before being exposed to:

```text
function-level dependency graphs
```

---

# 26. CLI INTEGRATION

The CLI should support architecture analysis.

Conceptually:

```bash
karuvi analyze <repository> --architecture
```

Optional output:

```bash
karuvi analyze <repository> --architecture --json
```

Do not break existing commands.

Architecture analysis should be additive.

---

# 27. TEST FIXTURE 1 — LAYERED REPOSITORY

Create:

```text
fixtures/simple_layered/

api/
    main.py

services/
    auth.py
    users.py

repositories/
    users.py
```

Dependencies:

```text
api
 ↓
services
 ↓
repositories
```

Expected component graph:

```text
api
 ↓
services
 ↓
repositories
```

Expected entry candidate:

```text
api/main.py
```

---

# 28. TEST FIXTURE 2 — SPLIT UTILS

Create:

```text
fixtures/split_utils/

utils/
    auth.py
    database.py
    dates.py

api/
    main.py
```

Dependencies should make:

```text
auth.py
database.py
```

strongly connected.

While:

```text
dates.py
```

remains mostly isolated.

Expected:

```text
utils boundary should not necessarily become
one single component.
```

---

# 29. TEST FIXTURE 3 — CYCLE

Create:

```text
fixtures/cycles/

a.py → b.py → c.py → a.py
```

Expected:

```text
no crash

cycle recorded

flow analysis remains bounded
```

---

# 30. TEST FIXTURE 4 — MERGED BOUNDARIES

Create:

```text
fixtures/merged_components/

auth/
    login.py

sessions/
    token.py
    refresh.py
```

Create strong cross-boundary relationships.

Expected:

```text
graph evidence can merge the boundaries
into one component candidate.
```

---

# 31. UNIT TEST REQUIREMENTS

Write tests for:

```text
path normalization

module node creation

symbol-to-module edge collapse

edge weight aggregation

relationship type preservation

intra-module relationship exclusion

boundary detection

community detection

component creation

component confidence

component graph aggregation

role detection

entry point detection

cycle handling

flow limits

JSON serialization
```

---

# 32. INTEGRATION TEST

The integration test should:

```text
1. Run existing Karuvi analysis on fixture repository.

2. Obtain the resolved symbol graph.

3. Run ArchitectureAnalyzer.

4. Verify module graph exists.

5. Verify component graph exists.

6. Verify at least one architecture component.

7. Verify drill-down mappings.

8. Serialize result to JSON.

9. Confirm JSON is valid.
```

This test is critical because it validates integration with the actual existing Karuvi pipeline.

---

# 33. ERROR HANDLING

The architecture layer must tolerate imperfect code analysis.

Possible situations:

```text
symbol without file

edge to unresolved target

external dependency

missing path

empty repository

single-module repository

disconnected repository
```

Do not crash.

---

## 33.1 Missing file metadata

Skip architecture edge construction when source or target module cannot be determined.

Record diagnostic information.

---

## 33.2 Empty graph

Return:

```text
ArchitectureModel
with zero modules
zero components
zero flows
```

Do not throw unless the caller explicitly requests strict validation.

---

## 33.3 Missing Louvain dependency

Prefer graceful handling.

Options:

```text
clear installation error
```

or:

```text
architecture analysis continues using structural boundaries only
```

The second is preferred for the product.

Record:

```text
community_detection_available = false
```

in metadata.

---

# 34. PERFORMANCE CONSTRAINTS

Do not repeatedly calculate expensive graph metrics.

Avoid:

```text
betweenness centrality inside loops

all_simple_paths without limits

repeated graph conversion
```

Cache results inside one analysis run.

---

# 35. LOGGING

Add useful analysis logs.

Example:

```text
[architecture] Building module graph...
[architecture] 42 modules discovered.
[architecture] 127 inter-module relationships discovered.

[architecture] Detecting structural boundaries...
[architecture] 6 boundary candidates discovered.

[architecture] Running community detection...
[architecture] 7 graph communities discovered.

[architecture] Building component model...
[architecture] 7 candidate components created.

[architecture] Detecting structural entry points...
[architecture] 3 entry candidates identified.

[architecture] Architecture analysis complete.
```

Avoid noisy per-node logging by default.

---

# 36. IMPLEMENTATION ORDER

Follow this order exactly unless existing repository constraints require adjustment.

---

## Milestone 0 — Reconnaissance

Do not implement architecture logic yet.

Inspect:

```text
existing graph
node metadata
edge metadata
CLI
visualizer
tests
```

Document integration assumptions in code comments or implementation notes.

---

## Milestone 1 — Architecture models

Implement:

```text
models.py
exceptions.py
```

Add tests.

---

## Milestone 2 — Module graph

Implement:

```text
module_graph.py
```

Required demonstration:

```text
symbol graph
    ↓
weighted module graph
```

Stop and test.

---

## Milestone 3 — Boundaries

Implement:

```text
boundaries.py
```

Required demonstration:

```text
modules
    ↓
structural boundary candidates
```

---

## Milestone 4 — Communities

Implement:

```text
communities.py
```

Required demonstration:

```text
module graph
    ↓
graph communities
```

---

## Milestone 5 — Components

Implement:

```text
components.py
```

Required demonstration:

```text
boundaries
+
communities
    ↓
candidate components
```

---

## Milestone 6 — Component graph

Implement:

```text
component_graph.py
```

Required demonstration:

```text
module graph
    ↓
component graph
```

---

## Milestone 7 — Metrics and roles

Implement:

```text
metrics.py
roles.py
```

---

## Milestone 8 — Entry points

Implement:

```text
entrypoints.py
```

---

## Milestone 9 — Flows

Implement:

```text
flows.py
```

Ensure bounded complexity.

---

## Milestone 10 — Analyzer

Connect everything.

---

## Milestone 11 — Serialization

Generate JSON.

---

## Milestone 12 — Documentation

Generate deterministic Markdown.

---

## Milestone 13 — CLI

Expose architecture mode.

---

## Milestone 14 — Frontend

Only after backend architecture output works.

---

# 37. GIT COMMIT PLAN

Use small commits.

Suggested:

```text
feat(architecture): add architecture data models

feat(architecture): construct weighted module graph

feat(architecture): add structural boundary detection

feat(architecture): add graph community detection

feat(architecture): reconstruct architecture components

feat(architecture): build component dependency graph

feat(architecture): add structural graph metrics

feat(architecture): detect structural entry points

feat(architecture): detect representative flows

feat(architecture): add architecture analyzer

feat(architecture): add JSON serialization

feat(architecture): add deterministic documentation

feat(cli): expose architecture analysis

feat(ui): add progressive architecture explorer
```

Do not produce one giant commit.

---

# 38. MVP ACCEPTANCE CRITERIA

The implementation is complete when the following is demonstrably true.

Given a Python repository:

```text
[✓] Existing Karuvi analysis produces resolved symbol relationships.

[✓] Karuvi converts those relationships into a weighted module graph.

[✓] Module paths are normalized.

[✓] Multiple symbol relationships aggregate into weighted module edges.

[✓] Relationship evidence is preserved.

[✓] Repository structure produces component candidates.

[✓] Graph community detection produces structural communities.

[✓] Structural and graph evidence produce components.

[✓] Components are assigned deterministic IDs.

[✓] Components have confidence/evidence metadata.

[✓] Karuvi constructs a component-level graph.

[✓] Structural entry points are detected.

[✓] Major graph roles are identified.

[✓] Representative architecture flows are generated.

[✓] The complete architecture model serializes to JSON.

[✓] Components can be drilled down into modules.

[✓] Modules can be drilled down into symbols.

[✓] Existing Karuvi functionality remains working.
```

---

# 39. DEFINITION OF A SUCCESSFUL DEMO

A successful prototype should be able to analyze a repository and demonstrate:

### First

```text
REPOSITORY

42 Modules
614 Symbols
7 Structural Components
```

### Then

```text
ARCHITECTURE

API
 ↓
SERVICES
 ↓
PERSISTENCE
```

### Then click:

```text
SERVICES
```

### And reveal:

```text
auth.py
users.py
payments.py
```

### Then click:

```text
auth.py
```

### And reveal:

```text
authenticate()
validate_token()
refresh_session()
```

### Then click a symbol

and return to the existing Karuvi-level implementation graph.

This is the complete product journey:

```text
I HAVE NO IDEA WHAT THIS REPOSITORY DOES

        ↓

I CAN SEE ITS MAJOR STRUCTURE

        ↓

I CAN SEE WHICH PART I WANT

        ↓

I CAN SEE WHICH FILES IMPLEMENT IT

        ↓

I CAN SEE WHICH FUNCTIONS CONNECT IT

        ↓

I CAN SEE THE ACTUAL CODE
```

---

# 40. FINAL ENGINEERING PRINCIPLE

Do not implement an “architecture AI.”

Do not implement a static folder visualizer.

Do not implement a prettier dependency graph.

Implement a deterministic abstraction pipeline:

```text
SOURCE CODE
     ↓
SYNTAX FACTS
     ↓
RESOLVED SYMBOL RELATIONSHIPS
     ↓
SYMBOL GRAPH
     ↓
GRAPH COARSENING
     ↓
MODULE GRAPH
     ↓
STRUCTURAL + GRAPH EVIDENCE
     ↓
COMPONENT MODEL
     ↓
COMPONENT GRAPH
     ↓
ARCHITECTURE MODEL
```

The most important invariant throughout the implementation is:

```text
Every high-level architectural claim
must be traceable downward.
```

For every:

```text
COMPONENT
```

Karuvi must know:

```text
which modules produced it
```

For every:

```text
MODULE RELATIONSHIP
```

Karuvi must know:

```text
which symbol relationships produced it
```

For every:

```text
SYMBOL
```

Karuvi must already know:

```text
where it came from in source code
```

This traceability is the foundation of the system.

---

# FINAL INSTRUCTION TO IMPLEMENTING AGENT

Before making large changes:

1. Inspect the existing Karuvi repository.
2. Understand the current graph and data model.
3. Reuse existing analysis structures.
4. Do not duplicate parsing.
5. Implement the architecture layer incrementally.
6. Add tests at every layer.
7. Run existing tests after every milestone.
8. Do not break current symbol resolution functionality.
9. Prefer simple deterministic heuristics over speculative complexity.
10. Ensure every abstraction preserves drill-down evidence.

The first goal is not to perfectly understand software architecture.

The first goal is to prove that Karuvi can reliably perform this transformation:

```text
RESOLVED SYMBOL GRAPH
        ↓
WEIGHTED MODULE GRAPH
        ↓
STRUCTURAL COMPONENT GRAPH
```

Everything else builds on that foundation.