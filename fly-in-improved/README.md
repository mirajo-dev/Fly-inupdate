*This project has been created as part of the 42 curriculum by [YOUR_NAME].*

# Fly-in Drones

## Description

Fly-in Drones is a Python 3.10+ routing and simulation project. A fleet of drones
must travel from a unique start zone to a unique end zone on a bidirectional graph.

The implementation is split into four responsibilities:

- **Parser:** validates the map format and metadata.
- **Pathfinding:** computes weighted routes with A* without `networkx`, `graphlib`,
  or another graph library.
- **Simulation:** executes movements in discrete turns while respecting zone and
  connection capacities.
- **Visualization:** displays the graph, zone types, capacities, routes, drones,
  turn number, and recent movements with pygame.

## Instructions

Install dependencies:

```bash
make install
```

Run the default map:

```bash
make run
```

Run another map:

```bash
python3 main.py parsing/maps/hard/01_maze_nightmare.txt
```

Controls:

- `SPACE`: pause/resume
- `N`: execute exactly one simulation turn
- `R`: reset
- `UP`: faster
- `DOWN`: slower

## Algorithm

A* is used with a cost based on the destination zone:

- normal: 1 turn
- priority: 1 turn, with deterministic preference in route selection
- restricted: 2 turns
- blocked: inaccessible

The planner generates several alternative routes by temporarily forbidding internal
zones of already-found routes. Drones are then distributed across these candidates
with a simple load-aware score. This is not a proof of global optimality; it is a
practical throughput-oriented heuristic.

The simulation is discrete. A normal/priority move completes in one turn. A move
into a restricted zone occupies the connection for two turns and cannot wait in
transit. Zone capacity and link capacity are checked before a movement is scheduled.

## Visualization

The pygame interface intentionally exposes the information needed during peer review:

- zone type through node color;
- zone capacity beside constrained zones;
- link capacity beside each connection;
- all routes used by the planner;
- drone identifiers and positions;
- current turn;
- delivered drone count;
- latest movements;
- pause, single-step, reset, and speed controls.

This makes it possible to compare the visual state with the discrete simulation
history instead of hiding the algorithm behind an animation.

## Testing

Run:

```bash
make test
```

The tests cover parsing of the provided maps, weighted pathfinding, and completion
of a reference simulation.

## Linting and type checking

Run:

```bash
make lint
```

The project uses type hints throughout and is designed around the mandatory flake8
and mypy workflow.

## Resources and AI usage

Classic references include Python's official documentation, pygame documentation,
and general A* algorithm documentation.

AI was used as a review and refactoring assistant: to identify bugs in the original
visualization, suggest a separation between parsing/pathfinding/simulation/display,
and propose tests. The resulting code must be understood, tested, and defended by
the project author during peer review.

## Important limitations

The route planner is heuristic rather than a mathematically guaranteed minimum-turn
multi-commodity flow solver. Evaluation maps may therefore still require further
optimization. The simulation engine is the authoritative source for turn counting;
the pygame animation is only its visualization.
