*This project has been created as part of the 42 curriculum by mirajora.*

# Fly-in

A collision-free, capacity-aware drone traffic simulator: drones travel from a
start zone to an end zone through a network of zones and connections, each
with its own capacity, while a scheduler makes sure no zone or connection is
ever over-booked at any given turn.

## Description

**Goal.** Given a small text-based description of a network — zones placed on
a 2D grid, connections between them, and a number of drones — compute a
turn-by-turn schedule that moves every drone from the `start` zone to the
`end` zone without ever violating:

- the maximum number of drones a zone can hold at the same time
  (`max_drones`),
- the maximum number of drones that can use a connection during the same
  turn (`max_link_capacity`),
- the fact that a `blocked` zone can never be entered, and that a
  `restricted` zone takes two turns to enter instead of one.

The schedule can either be printed as plain text in the terminal, or replayed
as an animation in a `pygame` window where drones visibly move across the
network, zone by zone, turn by turn.

**Overview of the pipeline.**

```
map file (.txt)  ──►  parsing  ──►  Network  ──►  candidate paths  ──►  schedule  ──►  terminal / pygame
```

1. **Parsing** (`read_config.py`, `parse_nb_drone.py`, `parse_hub_config.py`,
   `parse_connexion.py`, `metadata.py`, `network.py`) reads the map file line
   by line, validates every directive, and builds a `Network` object.
2. **Path finding** (`algo_A_star.py`) enumerates a set of candidate simple
   paths from `start` to `end`.
3. **Scheduling** (`display_tools.py`, class `DroneManager`) turns those
   candidate paths into an actual, collision-free, turn-by-turn plan for
   every drone, respecting all capacities.
4. **Rendering** (`display.py`, `display_tools.py`, `camera.py`) either
   prints the plan or animates it with `pygame`.

## Instructions

### Requirements

- Python 3.10+ (the code uses the `X | None` and `tuple[int, str]` typing
  syntax).
- [`pygame`](https://www.pygame.org/) — required even for the text-only
  mode, since the window/event modules are imported unconditionally.

### Installation

A `Makefile` is provided to set up an isolated virtual environment:

```sh
make install
```

This creates a `venv/` folder and installs `pygame`, `flake8` and `mypy`
inside it.

### Running the simulation

```sh
make run                 # prints the schedule as text in the terminal
make run-visual          # opens the pygame window and animates the drones
```

Both targets run `display.py` on `maps/easy/01_linear_path.txt` by default.
To use a different map, call the script directly:

```sh
venv/bin/python display.py maps/<difficulty>/<map_file>.txt            # text output
venv/bin/python display.py maps/<difficulty>/<map_file>.txt --visuel   # pygame window
```

The `maps/` directory ships with four difficulty tiers (`easy`, `medium`,
`hard`, `challenger`) — see [`maps/README.md`](maps/README.md) for the full
list and what each one is designed to test.

### Controls (pygame window)

| Key | Effect |
|---|---|
| `Esc` / closing the window | Quit |
| `Space` or `p` | Pause / resume the animation |
| `r` | Restart the simulation from turn 0 |
| Arrow keys | Pan the camera |
| `w` / `s` | Zoom in / out |

### Linting and type-checking

```sh
make lint          # flake8 + mypy (permissive on untyped third-party stubs)
make lint-strict    # flake8 + mypy --strict
```

### Cleaning up

```sh
make clean
```

## Algorithm Choices and Implementation Strategy

The project is split into two clearly separate algorithmic concerns: finding
*candidate routes* through the network, and turning them into a
*collision-free schedule*. Keeping them separate makes each of them much
simpler than solving both problems at once.

### 1. Candidate path enumeration — `find_all_paths` (`algo_A_star.py`)

Despite the file's name, this function does **not** implement A\*. It runs a
plain **Breadth-First Search (BFS)** over the tree of simple paths starting
from `start`:

- A FIFO queue (`collections.deque`, using `append`/`popleft`) stores
  `(zone, path_so_far)` states.
- Because the queue is FIFO, states are dequeued in strictly non-decreasing
  order of path length (number of zones). This can be proven by induction:
  the queue always contains only states of depth `k` and `k+1` for some `k`,
  in that order, so every state of depth `k` is processed before any state
  of depth `k+1`. This is the defining property of a breadth-first
  traversal, and it is what guarantees that the *first* path reaching `end`
  is one of the shortest ones in number of hops.
- `blocked` zones are excluded from the neighbor list before the search even
  starts (`_is_blocked` / `get_valid_neighbors`), a `restricted` zone still
  counts as a normal 1-hop neighbor at this stage (its 2-turn entry cost is
  only relevant later, during scheduling).
- Once a first path is found, its length becomes a reference: any partial
  path more than 3 zones longer is pruned (`len(path) > len(paths[0]) + 3`).
  This keeps the search from enumerating every simple path of a densely
  connected graph, while still collecting a useful set of alternatives for
  the scheduler to choose from.
- `calculate_euclidean` (a straight-line distance, ignoring the graph
  structure) is **not** used to guide the search — it is only used
  afterwards, in `path_cost`, to sort the already-found candidate paths:
  first by number of zones, then by total length, as a tie-breaker.

**Why BFS and not Dijkstra/A\*?** The project needs *several* candidate
routes, not a single optimal one — `DroneManager` later picks whichever
route lets each drone avoid congestion. BFS naturally explores in order of
increasing path length, which is exactly what the pruning rule needs to
stay cheap, without requiring a priority queue or an admissible heuristic.

**Complexity.** Let `n`/`m` be the number of zones/connections, `L` the
length of the shortest path, and `b` the average branching factor. Each
`get_valid_neighbors` call is `O(m)` (it scans every connection). Thanks to
the pruning, the search tree's depth is bounded by `L + 3`, so the number of
states explored is `O(b^(L+3))` in the worst case (a densely connected
network with many alternative routes), and the total search is:

```
O(b^(L+3) · (m + L))
```

In the best case (a network shaped like a tree, with a single possible
route), this degrades gracefully to a classic `O(n + m)` BFS, since there is
then nothing extra to enumerate. Sorting the `P` collected paths afterwards
costs `O(P · L · log P)`.

### 2. Collision-free scheduling — `DroneManager.compute_schedule` (`display_tools.py`)

This is a **space-time, capacity-aware search**, applied to each drone in
turn (a technique commonly known as *prioritized planning* / *cooperative
pathfinding* in multi-agent path-finding literature):

1. `ZoneReservationTable` records, for every `(resource, turn)` pair, how
   many drones have already reserved that zone or that connection. Zones and
   connections use two separate tables, because they are two independent
   capacity constraints.
2. Drones are processed one after another, in queue order (`deque` of
   `Drone` objects). For each drone, a BFS is run again — but this time over
   `(zone, turn)` states rather than plain zones, so that *when* a drone
   reaches a zone matters just as much as *which* zone it reaches.
   - Moving into a `restricted` zone costs 2 turns instead of 1
     (`_zone_cost`).
   - A move is only allowed if the destination zone still has a free slot
     at the turn of arrival, **and** the connection used has a free slot
     for every turn the crossing takes.
   - A drone may also choose to wait one turn in its current zone, if that
     zone stays free.
   - Neighbors are explored in an order that favors `priority` zones first,
     then zones closer to `end` (`neighbor_sort_key`), which tends to find
     short, sensible routes faster without changing correctness.
3. As soon as a full route is found for a drone, its zones and connections
   are immediately reserved in the tables, **before** searching a route for
   the next drone. This is what turns a set of independent single-drone
   searches into a genuinely collision-free multi-drone schedule: every
   later drone is forced to route around the reservations left by the
   earlier ones (wait, or take an alternate path). A drone for which no
   route can be found within the search horizon is skipped and reported
   with a warning, rather than blocking the whole simulation.
4. Finally, every drone's list of `(turn, from, to, cost)` steps is expanded
   into one schedule entry per turn (a multi-turn move, such as entering a
   `restricted` zone, produces one entry per turn it spans), producing the
   turn-indexed `schedule` used by both the terminal printer and the
   `pygame` renderer.

This design keeps the two hardest constraints of the problem — *zone
capacity* and *connection capacity* — as two independent, composable
lookups (`ZoneReservationTable`) rather than special-cased conditions
scattered through the search, which is what makes it practical to reason
about and to extend (e.g. adding a new zone type only requires touching
`_zone_type` / `_zone_cost`).

## Visual Representation

The `pygame` renderer (`Renderer` in `display_tools.py`, driven by
`Interface` in `display.py`) turns the abstract schedule into something you
can actually watch happen:

- **Zones** are drawn as icons (a distinct image for `start`, `end`, and
  regular hubs), tinted with the `color` declared in the map file, with
  their name labelled above them. This makes it immediately obvious which
  zone is which, and lets map authors visually distinguish zone roles.
- **Connections** are drawn as lines between zones, so the overall topology
  of the network — dead ends, loops, alternate routes — is visible at a
  glance instead of having to be reconstructed mentally from the config
  file.
- **Drones** are drawn as small icons that smoothly interpolate between
  their origin and destination zone over the course of a turn (including
  multi-turn moves, such as entering a `restricted` zone, which are
  interpolated smoothly across all the turns they span instead of jumping).
  This makes bottlenecks and waiting drones easy to spot: a drone that is
  stuck because a zone is full will visibly sit still while others move
  past it.
- **A turn counter and the current turn's moves** are overlaid in a corner
  of the screen, so the animation can be directly cross-checked against the
  text output produced by `print_schedule`.
- **A pausable, steppable view**: `Space`/`p` pauses the animation to
  inspect a specific moment, `r` restarts it from scratch, and the camera
  (arrow keys to pan, `w`/`s` to zoom) lets you navigate large maps —
  useful on the bigger `hard`/`challenger` maps, where the whole network
  does not fit on screen at once.

Together, this turns an otherwise abstract list of `(drone, zone, turn)`
tuples into a direct, checkable visualization of *why* a schedule looks the
way it does — for instance, seeing two drones stack up outside a
`max_drones=2` zone communicates the capacity constraint far more directly
than reading two lines of text.

## Example

Given the map [`maps/easy/03_basic_capacity.txt`](maps/easy/03_basic_capacity.txt):

```
# Easy Level 3: Basic capacity management
nb_drones: 4

start_hub: start 0 0 [color=green]
hub: bottleneck 1 0 [color=orange max_drones=2]
hub: wide_area 2 0 [color=blue max_drones=3]
end_hub: goal 3 0 [color=red]

connection: start-bottleneck [max_link_capacity=4]
connection: bottleneck-wide_area [max_link_capacity=4]
connection: wide_area-goal [max_link_capacity=4]
```

Running:

```sh
venv/bin/python display.py maps/easy/03_basic_capacity.txt
```

produces:

```
D1-bottleneck D2-bottleneck
D1-wide_area D2-wide_area D3-bottleneck D4-bottleneck
D1-goal D2-goal D3-wide_area D4-wide_area
D3-goal D4-goal
```

Each line is one turn; each `D<id>-<zone>` entry is a drone that actually
moved this turn, written as the zone it just reached. A drone that stays
where it is (for example `D3` and `D4`, waiting one extra turn before
`bottleneck` has a free slot) is simply omitted from that line rather than
being repeated — notice that even though the connections all allow up to 4
drones per turn, `bottleneck` only has `max_drones=2`, so only `D1` and `D2`
are let in on turn 1. Once a drone reaches `goal`, it is dropped from the
schedule and never appears on a later line.

**Restricted zones** take two turns to enter instead of one. On the first of
those two turns the drone has not reached the zone yet, so it is printed as
`D<id>-<connection>` (the name of the connection it is currently crossing)
instead of the zone name; on the second turn it is printed as `D<id>-<zone>`
as usual. For example, on
[`maps/medium/02_circular_loop.txt`](maps/medium/02_circular_loop.txt),
where `exit_point` is `restricted`, drone `D1`'s approach looks like:

```
D1-loop_b-exit_point
D1-exit_point
```

`D1-loop_b-exit_point` (turn N) means "in flight, crossing the
`loop_b-exit_point` connection"; `D1-exit_point` (turn N+1) means "has now
arrived in `exit_point`".

Running the same map with `--visuel` opens a `pygame` window animating this
same sequence: `D1` and `D2` glide from `start` to `bottleneck` first, `D3`
and `D4` visibly stay put for one turn, then follow once a slot frees up.

## Resources

### Classic references

- [Breadth-First Search — Wikipedia](https://en.wikipedia.org/wiki/Breadth-first_search)
- [A\* search algorithm — Wikipedia](https://en.wikipedia.org/wiki/A*_search_algorithm)
- Silver, D. (2005). *Cooperative Pathfinding* — the space-time reservation
  / prioritized-planning technique used by the scheduler is a simplified
  instance of this family of multi-agent path-finding algorithms.
- [`pygame` documentation](https://www.pygame.org/docs/)
- [Python `collections.deque` documentation](https://docs.python.org/3/library/collections.html#collections.deque)
- [`mypy` — strict mode documentation](https://mypy.readthedocs.io/en/stable/getting_started.html#strict-mode-and-configuration)
- [`flake8` documentation](https://flake8.pycqa.org/en/latest/)

### AI usage

An AI assistant (Claude, Anthropic) was used to help explain and document
parts of the existing code (in particular the pathfinding and scheduling
logic), to assist with minor refactoring for readability, and to help draft
this `README.md`. The core algorithm design and implementation remain the
author's own work.