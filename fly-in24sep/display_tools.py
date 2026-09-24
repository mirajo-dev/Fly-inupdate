import os, sys

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
try:
    import pygame
    from pygame import Color, Surface, Vector2
except ImportError:
    print("[Error] Missing 'pygame' module.")
    print(" Required inst Required installation: 'pip install pygame'")
    sys.exit(1)
from collections import deque
from network import Network
from parse_nb_drone import Drone
from parse_hub_config import Zone
from parse_connexion import Connection
from camera import Camera

MARGIN_ZONE = 180
DRONE_SPEED = 200
NODE_LABEL_MARGINE = 8
ARRIVAL_THRESHOLD = 5
DEPARTURE_INTERVAL = 1.0

PathStep = tuple[int, str, str, int]
ScheduleEntry = tuple[str, str, str, str, bool]


class ZoneReservationTable:
    """Space-time reservation table for zones and connections.

    Counts, for each ``(resource, turn)`` pair, how many drones have
    already reserved that resource at that turn.
    """

    def __init__(self) -> None:
        """Initializes an empty reservation table."""
        self._counts: dict[tuple[str, int], int] = {}

    def occupancy(self, zone: str, t: int) -> int:
        """Returns the number of reservations of a resource at a given turn.

        Args:
            zone: Name of the zone, or key of the connection, to look up.
            t: Turn number.

        Returns:
            Number of drones that have reserved the resource at turn ``t``
            (0 if there is none).
        """
        return self._counts.get((zone, t), 0)

    def try_acquire(self, zone: str, t: int, capacity: int) -> bool:
        """Reserves one slot of a resource at a given turn if possible.

        Args:
            zone: Name of the zone, or key of the connection, to reserve.
            t: Turn number.
            capacity: Maximum number of simultaneous reservations allowed.

        Returns:
            ``True`` if the slot was reserved, ``False`` if the resource
            was already at full capacity at turn ``t``.
        """
        current = self._counts.get((zone, t), 0)
        if current >= capacity:
            return False
        self._counts[(zone, t)] = current + 1
        return True


class DroneManager:
    """Manages drone state, collision-free scheduling and animation.

    At construction the manager keeps only the valid paths it is given,
    creates the drones, places them on the start zone and computes the
    full schedule.

    Attributes:
        network: Network in which the drones move.
        paths: Valid simple paths from the start to the end zone that
            were given at construction.
        drones: Drones of the simulation.
        connections: Connections of the network.
        drone_positions: Current world position of each drone, by
            drone identifier.
        schedule: Turn-by-turn list of moves; each turn is a list of
            ``ScheduleEntry`` tuples.
        current_round: Index of the turn currently being animated.
        round_progress: Progress of the current turn, between 0.0 and
            1.0.
        round_duration: Duration of one turn, in seconds.
    """

    def __init__(self, network: Network, paths: list[list[str]]) -> None:
        """Initializes the manager and computes the schedule.

        Only paths that start at the start zone, end at the end zone, contain
        at least two zones and never repeat a zone are kept.

        Args:
            network: Network in which the drones move.
            paths: Candidate paths, as returned by ``find_all_paths``.
        """
        self.network = network

        valid_paths = []
        if paths:
            raw_paths = [paths] if isinstance(paths[0], str) else paths
            for p in raw_paths:
                net_end = p[-1] == self.network.end
                if len(p) > 1 and p[0] == self.network.start and net_end:
                    if len(p) == len(set(p)):
                        valid_paths.append(p)

        self.paths: list[list[str]] = valid_paths
        self.drones: list[Drone] = network.get_drones()
        self.connections: list[Connection] = network.connections
        self._connection_lookup = self._build_connection_lookup()

        self._zone_positions: dict[str, Vector2] = {
            name: Vector2(z.x * MARGIN_ZONE, z.y * MARGIN_ZONE)
            for name, z in self.network.zones.items()
        }

        self.drone_positions: dict[str, Vector2] = {}
        self.schedule: list[list[ScheduleEntry]] = []
        self.current_round: int = 0
        self.round_progress: float = 0.0
        self.round_duration: float = MARGIN_ZONE / DRONE_SPEED

        self.start_simulation()

    def _build_connection_lookup(self) -> dict[tuple[str, str], Connection]:
        """Builds a lookup table of connections by endpoints.

        Returns:
            Dictionary mapping ``(zone_a, zone_b)`` and ``(zone_b, zone_a)``
            to the same ``Connection`` object.
        """
        lookup: dict[tuple[str, str], Connection] = {}
        for conn in self.connections:
            lookup[(conn.zone_a, conn.zone_b)] = conn
            lookup[(conn.zone_b, conn.zone_a)] = conn
        return lookup

    def _zone_type(self, zone_name: str) -> str:
        """Returns the type of a zone.

        Args:
            zone_name: Name of the zone.

        Returns:
            Zone type (``normal``, ``blocked``, ``restricted`` or
            ``priority``), or ``"normal"`` if none can be determined.

        Raises:
            ValueError: If the zone does not exist in the network.
        """
        zone = self.network.get_zone(zone_name)
        for attr in ("zone_type", "type", "zone"):
            val = getattr(zone, attr, None)
            if val:
                return str(val)
        return "normal"

    def _is_blocked(self, zone_name: str) -> bool:
        """Tells whether a zone is blocked.

        Args:
            zone_name: Name of the zone.

        Returns:
            ``True`` if the zone type is ``blocked``.
        """
        return self._zone_type(zone_name) == "blocked"

    def _zone_cost(self, zone_name: str) -> int:
        """Returns the number of turns needed to enter a zone.

        Args:
            zone_name: Name of the destination zone.

        Returns:
            2 for a ``restricted`` zone, 1 otherwise.
        """
        return 2 if self._zone_type(zone_name) == "restricted" else 1

    def _zone_capacity(self, zone_name: str) -> int:
        """Returns the maximum number of drones a zone can hold.

        The start and end zones are considered unlimited.

        Args:
            zone_name: Name of the zone.

        Returns:
            Capacity of the zone (999999 for the start and end zones, 1 if no
            valid capacity is defined).
        """
        if zone_name in (self.network.start, self.network.end):
            return 999999
        zone = self.network.get_zone(zone_name)

        cap = getattr(
            zone, "max_drones", getattr(
                zone, "max_drone", getattr(
                    zone, "capacity", None)))
        if cap is None and hasattr(
                zone, "attributes") and isinstance(
                zone.attributes, dict):
            cap = zone.attributes.get(
                "max_drones", zone.attributes.get("max_drone"))
        if cap is None and hasattr(
                zone, "params") and isinstance(
                zone.params, dict):
            cap = zone.params.get("max_drones", zone.params.get("max_drone"))

        if cap is not None:
            try:
                return int(cap)
            except (ValueError, TypeError):
                pass
        return 1

    def _edge_capacity(self, zone_a: str, zone_b: str) -> int:
        """Returns the capacity of the connection between two zones.

        Args:
            zone_a: Name of the first zone.
            zone_b: Name of the second zone.

        Returns:
            ``max_link_capacity`` of the connection, 1 if the two zones are
            not connected, or 999999 (unlimited) if the connection does not
            define a valid capacity.
        """
        conn = self._connection_lookup.get((zone_a, zone_b))
        if not conn:
            return 1
        cap = getattr(
            conn, "max_link_capacity", getattr(
                conn, "max_capacity", getattr(
                    conn, "capacity", None)))
        if cap is None and hasattr(
                conn, "attributes") and isinstance(
                conn.attributes, dict):
            cap = conn.attributes.get(
                "max_link_capacity",
                conn.attributes.get("max_capacity"))
        if cap is not None:
            try:
                return int(cap)
            except (ValueError, TypeError):
                pass
        return 999999

    def start_simulation(self) -> None:
        """Resets the simulation to its initial state.

        Places every drone on the start zone, recomputes the schedule and
        rewinds the animation to the first turn.
        """
        start_pos = self._zone_positions[self.network.start]
        for drone in self.drones:
            self.drone_positions[drone.id_drone] = Vector2(start_pos)

        self.schedule = self.compute_schedule()
        self.current_round = 0
        self.round_progress = 0.0

    def _format_cap(self, cap: int) -> str:
        """Formats a capacity for display.

        The "unlimited" value 999999 is replaced by the total number of
        drones.

        Args:
            cap: Capacity to format.

        Returns:
            Text representation of the capacity.
        """
        if cap >= 999999:
            return str(len(self.drones))
        return str(cap)

    def print_schedule(self) -> None:
        """Prints the schedule in the terminal.

        Prints one line per turn. Each move of the turn is written as
        ``<drone_id>-<destination>`` and moves are separated by spaces.
        """
        for round_moves in self.schedule:
            line = " ".join(f"{move[0]}-{move[2]}" for move in round_moves)
            print(f"{line}")

    def format_round(self, round_idx: int,
                     drone_positions: dict[str, str]) -> str:
        """Formats one turn with zone and connection occupancy details.

        Kept in reserve in case the detailed output format is required. The
        ``drone_positions`` mapping is updated in place with the destination
        of every move of the turn.

        Args:
            round_idx: Index of the turn to format.
            drone_positions: Current zone name of each drone, by drone
                identifier. It is modified by this method.

        Returns:
            Text describing the moves of the turn, or an empty string if
            ``round_idx`` is out of range.
        """
        if round_idx < 0 or round_idx >= len(self.schedule):
            return ""

        round_moves = self.schedule[round_idx]
        start_zone = self.network.start

        for id_drone, _, z_to, _, _ in round_moves:
            drone_positions[id_drone] = z_to

        zone_counts: dict[str, int] = {}
        for pos in drone_positions.values():
            zone_counts[pos] = zone_counts.get(pos, 0) + 1

        link_counts: dict[str, int] = {}
        for _, _, _, link_name, _ in round_moves:
            link_counts[link_name] = link_counts.get(link_name, 0) + 1

        move_strings = []
        for id_drone, z_from, z_to, link_name, is_link in round_moves:
            if z_from == start_zone and z_to == start_zone:
                continue

            occ_zone = zone_counts[z_to]
            max_zone_str = self._format_cap(self._zone_capacity(z_to))

            occ_link = link_counts[link_name]
            max_link = self._edge_capacity(z_from, z_to) if is_link else 1
            max_link_str = self._format_cap(max_link)
            link = f"{link_name}: {occ_link}/{max_link_str}"
            zone_j = f"{z_to} : {occ_zone}/{max_zone_str}"
            move_str = f"{id_drone}-{z_to} Zone {zone_j} | {link}"
            move_strings.append(move_str)

        return " ;".join(move_strings)

    def is_finished(self) -> bool:
        """Tells whether the whole schedule has been played.

        Returns:
            ``True`` if every turn of the schedule has been animated.
        """
        return self.current_round >= len(self.schedule)

    def update_drones(self, dt: float) -> None:
        """Advances the animation and updates the drone positions.

        Positions are interpolated between the origin and destination zones
        of each move. A move that spans several consecutive turns (for
        example towards a restricted zone) is interpolated over all of them.
        When the current turn is complete, drones are placed exactly on their
        destination and the next turn starts.

        Args:
            dt: Time elapsed since the last update, in seconds.
        """
        if self.is_finished() or not self.schedule:
            return

        self.round_progress += dt / self.round_duration
        t = min(self.round_progress, 1.0)

        for move in self.schedule[self.current_round]:
            id_drone, zone_from, zone_to = move[0], move[1], move[2]
            start_pos = self._zone_positions[zone_from]
            end_pos = self._zone_positions[zone_to]

            def same_move(m: ScheduleEntry) -> bool:
                """Tells whether a schedule entry is the move being animated.

                Args:
                    m: Schedule entry to compare.

                Returns:
                    ``True`` if the entry concerns the same drone, origin and
                    destination.
                """
                return (m[0] == id_drone and m[1] == zone_from
                        and m[2] == zone_to)

            first_round = self.current_round
            while first_round > 0 and any(
                    same_move(m) for m in self.schedule[first_round - 1]):
                first_round -= 1

            last_round = self.current_round
            while last_round < len(self.schedule) - 1 and any(
                    same_move(m) for m in self.schedule[last_round + 1]):
                last_round += 1

            total_turns = (last_round - first_round) + 1
            current_turn_offset = self.current_round - first_round

            global_t = (current_turn_offset + t) / total_turns
            self.drone_positions[id_drone] = start_pos.lerp(end_pos, global_t)

        if self.round_progress >= 1.0:
            for move in self.schedule[self.current_round]:
                id_drone, zone_to = move[0], move[2]
                self.drone_positions[id_drone] = Vector2(
                    self._zone_positions[zone_to])
            self.current_round += 1
            self.round_progress = 0.0

    def compute_schedule(self) -> list[list[ScheduleEntry]]:
        """Computes the turn-by-turn schedule of every drone.

        Drones are handled one after the other. For each of them, a
        breadth-first search is run in space and time from the start zone
        and finds a route to the end zone that respects the zone and
        connection capacities already reserved by the previous drones.
        Blocked zones are never entered, moving into a restricted zone takes
        two turns, and a drone may wait in place. Priority zones and zones
        closer to the end zone are explored first. Once a route is found, its
        zones and connections are reserved. Drones for which no route is
        found within the search horizon are skipped and reported by a
        warning message.

        Returns:
            List of turns; each turn is a list of ``ScheduleEntry`` tuples
            ``(drone_id, zone_from, zone_to, link_name, is_link)``. Trailing
            empty turns are removed.
        """
        adj: dict[str, list[str]] = {name: [] for name in self.network.zones}
        for conn in self.connections:
            if not self._is_blocked(conn.zone_b):
                adj[conn.zone_a].append(conn.zone_b)
            if not self._is_blocked(conn.zone_a):
                adj[conn.zone_b].append(conn.zone_a)

        end_pos = self._zone_positions[self.network.end]

        def neighbor_sort_key(nxt: str) -> tuple[int, float]:
            """Computes the exploration order key of a neighbor zone.

            Args:
                nxt: Name of the neighbor zone.

            Returns:
                Tuple ``(0 if the zone is a priority zone else 1, distance to
                the end zone)``.
            """
            is_priority = self._zone_type(nxt) == "priority"
            return (0 if is_priority else 1,
                    self._zone_positions[nxt].distance_to(end_pos))

        for u in adj:
            adj[u].sort(key=neighbor_sort_key)

        node_table = ZoneReservationTable()
        edge_table = ZoneReservationTable()

        def edge_key(u: str, v: str) -> str:
            """Builds an order-independent key for a connection.

            Args:
                u: Name of the first zone.
                v: Name of the second zone.

            Returns:
                Key that is identical for ``(u, v)`` and ``(v, u)``.
            """
            return "|".join(sorted([u, v]))

        def is_node_free(zone: str, t: int) -> bool:
            """Tells whether a zone can accept one more drone at a given turn.

            The start and end zones are always free.

            Args:
                zone: Name of the zone.
                t: Turn number.

            Returns:
                ``True`` if the number of reservations is below the capacity of
                the zone.
            """
            if zone in (self.network.start, self.network.end):
                return True
            return node_table.occupancy(zone, t) < self._zone_capacity(zone)

        drone_paths: dict[str, list[PathStep]] = {}
        max_t = 0
        drone_queue = deque(self.drones)
        skipped: list[Drone] = []

        while drone_queue:
            drone = drone_queue.popleft()
            d_id = drone.id_drone

            queue: deque[tuple[int, str, set[str], list[PathStep]]] = deque(
                [(0, self.network.start, {self.network.start}, [])])
            visited_time_space = {(self.network.start, 0)}
            found: list[PathStep] | None = None

            while queue:
                t, curr, spatial_visited, path = queue.popleft()
                if curr == self.network.end:
                    found = path
                    break
                if t > 3000:
                    break

                for nxt in adj.get(curr, []):
                    if nxt in spatial_visited:
                        continue

                    cost = self._zone_cost(nxt)
                    arrival_t = t + cost
                    e_cap = self._edge_capacity(curr, nxt)
                    ekey = edge_key(curr, nxt)

                    edge_free = all(
                        edge_table.occupancy(
                            ekey, t + k) < e_cap for k in range(cost))
                    nxt_free = is_node_free(nxt, arrival_t)

                    if edge_free and nxt_free:
                        if (nxt, arrival_t) not in visited_time_space:
                            visited_time_space.add((nxt, arrival_t))
                            queue.append(
                                (arrival_t, nxt, spatial_visited | {nxt},
                                 path + [(t, curr, nxt, cost)])
                            )

                if is_node_free(curr, t + 1):
                    if (curr, t + 1) not in visited_time_space:
                        visited_time_space.add((curr, t + 1))
                        queue.append((t + 1, curr, spatial_visited,
                                     path + [(t, curr, curr, 1)]))

            if not found:
                skipped.append(drone)
                continue

            drone_paths[d_id] = found

            for step_t, u, v, cost in found:
                if u != v:
                    ekey = edge_key(u, v)
                    e_cap = self._edge_capacity(u, v)

                    for k in range(cost):
                        edge_table.try_acquire(ekey, step_t + k, e_cap)

                    end_t = step_t + cost
                    if v not in (self.network.start, self.network.end):
                        node_table.try_acquire(
                            v, end_t, self._zone_capacity(v))
                else:
                    end_t = step_t + 1
                    if u not in (self.network.start, self.network.end):
                        node_table.try_acquire(
                            u, end_t, self._zone_capacity(u))

                if end_t > max_t:
                    max_t = end_t

        if skipped:
            names = ", ".join(d.id_drone for d in skipped)
            print(
                "[AVERTISSEMENT] Drones sans chemin trouvé "
                f"(capacité saturée) : {names}")

        schedule: list[list[ScheduleEntry]] = [[] for _ in range(max_t)]

        for d_id, moves in drone_paths.items():
            for step_t, u, v, cost in moves:
                if u != v:
                    for k in range(cost):
                        if k == 0:
                            link_name = f"{u}-{v}"
                            is_link = True
                        else:
                            link_name = f"{u}-{u}"
                            is_link = False
                        schedule[step_t +
                                 k].append((d_id, u, v, link_name, is_link))
                else:
                    link_name = f"{u}-{u}"
                    schedule[step_t].append((d_id, u, v, link_name, False))

        while schedule and not schedule[-1]:
            schedule.pop()

        return schedule


class Renderer:
    """Draws the network and the drones with pygame.

    Attributes:
        screen: Surface on which everything is drawn.
        camera: Camera used to convert world positions to screen
            positions.
        network: Network to draw.
        drone_manager: Manager providing drone positions and the
            schedule.
        zones: Zones of the network.
        font: Font used for labels.
        start_img: Image of the start zone.
        end_img: Image of the end zone.
        drone_img: Image of a drone.
        hub_img: Image of a regular zone.
    """

    def __init__(
            self,
            screen: Surface,
            camera: Camera,
            network: Network,
            drone_manager: DroneManager,
            font: pygame.font.Font) -> None:
        """Initializes the renderer and loads the images.

        The images are loaded from the ``image/`` directory, relative to the
        current working directory.

        Args:
            screen: Surface on which everything is drawn.
            camera: Camera used to convert world positions to screen
                positions.
            network: Network to draw.
            drone_manager: Manager providing drone positions and the
                schedule.
            font: Font used for labels.

        Raises:
            FileNotFoundError: If an image file cannot be found.
        """
        self.screen = screen
        self.camera = camera
        self.network = network
        self.drone_manager = drone_manager
        self.zones: list[Zone] = list(network.zones.values())
        self.font = font

        self.start_img = pygame.transform.scale(
            pygame.image.load("image/start.png").convert_alpha(), (64, 64))
        self.end_img = pygame.transform.scale(
            pygame.image.load("image/end.png").convert_alpha(), (64, 64))
        self.drone_img = pygame.transform.scale(
            pygame.image.load("image/drone.png"), (32, 32))
        self.hub_img = pygame.transform.scale(
            pygame.image.load("image/hub.png").convert_alpha(), (64, 64))

    def draw_drone(self) -> None:
        """Draws every drone at its current position."""
        for drone in self.drone_manager.drones:
            world_pos = self.drone_manager.drone_positions[drone.id_drone]
            screen_pos = self.camera.apply(world_pos)
            rect_img = self.drone_img.get_rect(center=screen_pos)
            self.screen.blit(self.drone_img, rect_img)

    def draw_connection(self) -> None:
        """Draws a line for every connection of the network."""
        for conn in self.network.connections:
            zone_a = self.network.get_zone(conn.zone_a)
            zone_b = self.network.get_zone(conn.zone_b)
            pos_a = self.camera.apply(
                Vector2(
                    zone_a.x *
                    MARGIN_ZONE,
                    zone_a.y *
                    MARGIN_ZONE))
            pos_b = self.camera.apply(
                Vector2(
                    zone_b.x *
                    MARGIN_ZONE,
                    zone_b.y *
                    MARGIN_ZONE))
            pygame.draw.line(self.screen, Color(0, 200, 210), pos_a, pos_b, 2)

    def draw_nodes(self) -> None:
        """Draws every zone with its label.

        The zone image is tinted with the color of the zone; red is used
        when the color is missing or not recognized.
        """
        for zone in self.zones:
            if zone.name == self.network.start:
                image = self.start_img
            elif zone.name == self.network.end:
                image = self.end_img
            else:
                image = self.hub_img

            try:
                tint_color = Color(zone.color if zone.color else "Red")
            except ValueError:
                tint_color = Color("Red")

            tint = image.copy()
            tint.fill(tint_color, special_flags=pygame.BLEND_RGBA_MULT)

            pos = Vector2(zone.x * MARGIN_ZONE, zone.y * MARGIN_ZONE)
            screen_pos = self.camera.apply(pos)

            img_rect = tint.get_rect(center=screen_pos)
            self.screen.blit(tint, img_rect)

            label_name = self.font.render(zone.name, True, Color("yellow"))
            bg_rect = label_name.get_rect(
                center=(
                    screen_pos.x,
                    img_rect.top -
                    NODE_LABEL_MARGINE))

            padding_rect = bg_rect.inflate(6, 4)
            pygame.draw.rect(
                self.screen,
                Color(
                    10,
                    10,
                    15,
                    220),
                padding_rect,
                border_radius=3)
            self.screen.blit(label_name, bg_rect)

    def draw_turn_info(self) -> None:
        """Draws the turn counter and the moves of the current turn."""
        total_turns = len(self.drone_manager.schedule)
        current_turn = min(
            self.drone_manager.current_round + 1,
            total_turns) if total_turns > 0 else 0

        turn_text = f"Tour : {current_turn} / {total_turns}"
        label = self.font.render(turn_text, True, Color("cyan"))

        rect = label.get_rect(topleft=(20, 20))
        bg_rect = rect.inflate(12, 8)
        pygame.draw.rect(
            self.screen,
            Color(
                10,
                10,
                15,
                220),
            bg_rect,
            border_radius=4)
        self.screen.blit(label, rect)

        if 0 <= self.drone_manager.current_round < total_turns:
            round_idx = self.drone_manager.current_round
            moves = self.drone_manager.schedule[round_idx]
            moves_str = " | ".join(
                f"{d}-{z_to}" for d, _, z_to, _, _ in moves)
            moves_label = self.font.render(
                f"Mouvements : {moves_str}", True, Color("white"))

            moves_rect = moves_label.get_rect(topleft=(20, 55))
            moves_bg = moves_rect.inflate(12, 8)
            pygame.draw.rect(
                self.screen,
                Color(
                    10,
                    10,
                    15,
                    220),
                moves_bg,
                border_radius=4)
            self.screen.blit(moves_label, moves_rect)


class InputHandler:
    """Handles the keyboard input that controls the camera.

    Attributes:
        camera: Camera controlled by the keyboard.
    """

    def __init__(self, camera: Camera) -> None:
        """Initializes the handler.

        Args:
            camera: Camera to control.
        """
        self.camera = camera

    def get_direction(self) -> Vector2:
        """Reads the arrow keys and returns the requested direction.

        Returns:
            Direction vector built from the arrow keys currently pressed.
            It is not normalized and is the zero vector if no arrow key is
            pressed.
        """
        keys = pygame.key.get_pressed()
        direction = Vector2(0, 0)

        if keys[pygame.K_UP]:
            direction.y -= 1
        if keys[pygame.K_DOWN]:
            direction.y += 1
        if keys[pygame.K_LEFT]:
            direction.x -= 1
        if keys[pygame.K_RIGHT]:
            direction.x += 1
        return direction

    def handle_input(self) -> None:
        """Applies the zoom keys to the camera.

        The ``w`` key zooms in and the ``s`` key zooms out, by steps of
        0.05, with the zoom factor kept between 0.25 and 1.0.
        """
        keys = pygame.key.get_pressed()
        max_zoom = 1.0
        min_zoom = 0.25
        step = 0.05

        if keys[pygame.K_w]:
            new_zoom = min(max_zoom, self.camera.get_zoom() + step)
            self.camera.set_zoom(new_zoom)
        elif keys[pygame.K_s]:
            new_zoom = max(min_zoom, self.camera.get_zoom() - step)
            self.camera.set_zoom(new_zoom)

