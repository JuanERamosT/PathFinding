# ============================================================
# enemy.py - Enemigo con inteligencia evolutiva
# ============================================================
#
# COMPORTAMIENTO POR ALGORITMO:
#
#   DFS:      Exploracion ciega ciclica con stack.
#             No sabe donde esta el jugador.
#
#   Dijkstra: Exploracion ciega ciclica con min-heap.
#             No sabe donde esta el jugador.
#
#   A*:       Persecucion informada con heuristica.
#             Si sabe donde esta el jugador y calcula el camino optimo.
#
# ============================================================

import heapq

from constants import (
    ASTAR_COLOR,
    ASTAR_RECALC_STEPS,
    DFS_COLOR,
    DIJKSTRA_COLOR,
    ENEMY_SPEEDS,
    ENTITY_LERP_SPEED,
    MIN_ENEMY_DELAY,
    PLAYER_SIZE,
)
from pathfinding import (
    astar,
    dfs_next_step,
    greedy_next_step,
    local_dijkstra_scan,
    get_valid_moves,
)


VISION_RADIUS = 4

MOVE_DIRECTIONS = [
    (-1, 0, "arriba"),
    (0, 1, "derecha"),
    (1, 0, "abajo"),
    (0, -1, "izquierda"),
]


class Enemy:
    """Enemigo que busca o persigue segun el algoritmo seleccionado."""

    def __init__(self, row, col, algorithm="dfs"):
        self.row = row
        self.col = col
        self.algorithm = algorithm
        self.speed_multiplier = 1.0
        self.move_timer = 0

        self.visual_row = float(row)
        self.visual_col = float(col)

        # DFS y Dijkstra son ciegos: solo escanean una zona local.
        self.scan_cells = []
        self.visited = {(row, col)}
        self.backtrack_stack = []
        self.previous_pos = None
        self.recent_positions = []
        self.last_direction = "inicio"
        self.last_decision = "Escanea periferia"

        # Camino calculado solo para A*.
        self.path = []
        self.path_index = 0
        self.steps_taken = 0

        self.is_alerted = False
        self.explored = [(row, col)]
        self.last_result = None

    def set_algorithm(self, algorithm):
        self.algorithm = algorithm
        self.path = []
        self.path_index = 0
        self.steps_taken = 0
        self.is_alerted = False
        self.explored = [(self.row, self.col)]
        self.scan_cells = []
        self.visited = {(self.row, self.col)}
        self.backtrack_stack = []
        self.previous_pos = None
        self.recent_positions = []
        self.last_direction = "inicio"
        self.last_decision = "Escanea periferia"
        self.last_result = None

    def get_color(self):
        colors = {"dfs": DFS_COLOR, "dijkstra": DIJKSTRA_COLOR, "astar": ASTAR_COLOR}
        return colors.get(self.algorithm, DFS_COLOR)

    def get_move_delay(self):
        base_delay = ENEMY_SPEEDS.get(self.algorithm, 200)
        return max(MIN_ENEMY_DELAY, int(base_delay / self.speed_multiplier))

    def get_algorithm_name(self):
        names = {"dfs": "DFS", "dijkstra": "Dijkstra", "astar": "A*"}
        return names.get(self.algorithm, "???")

    def _needs_recalculate_astar(self):
        if not self.path:
            return True
        if self.path_index >= len(self.path) - 1:
            return True
        if self.steps_taken >= ASTAR_RECALC_STEPS:
            return True
        return False

    def update(self, grid, player_pos, dt, occupied=None):
        """
        Mueve al enemigo un paso.
        DFS/Dijkstra son ciegos: no reciben player_pos para decidir el camino.
        A* sigue siendo informado porque su gracia es usar una meta.
        """
        self.move_timer -= dt
        if self.move_timer > 0:
            return

        if occupied is None:
            occupied = set()

        if self.algorithm in ("dfs", "dijkstra"):
            self.is_alerted = False
            self.path = []
            self.path_index = 0
            self.steps_taken = 0
            self._update_blind(grid, player_pos, occupied)
        else:
            self.is_alerted = True
            self._update_astar(grid, player_pos, occupied)

        self.move_timer = self.get_move_delay()

    def _update_blind(self, grid, player_pos, occupied):
        """Exploracion ciega local: escanea radio 4, luego avanza 1 paso."""
        self.scan_cells = self._scan_periphery(grid)
        player_cells = set(grid.entity_cells(*player_pos, PLAYER_SIZE))
        player_visible = bool(player_cells.intersection(self.scan_cells))
        self.is_alerted = player_visible

        if player_visible:
            if self.algorithm == "dijkstra":
                next_cell, direction = self._choose_dijkstra_step(grid, occupied, player_cells)
            else:
                next_cell, direction, msg = greedy_next_step(self.get_pos(), player_cells, getattr(self, "previous_pos", None), grid, occupied)
                self.last_decision = msg
        elif self.algorithm == "dfs":
            next_cell, direction, msg = dfs_next_step(self.get_pos(), self.visited, self.backtrack_stack, grid, occupied)
            self.last_decision = msg
        else:
            next_cell, direction = self._choose_dijkstra_step(grid, occupied, player_cells)

        self._move_one_cell(next_cell, direction)

    def _scan_periphery(self, grid):
        return [cell for cell in self._local_area(grid) if cell != self.get_pos()]

    def _choose_dijkstra_step(self, grid, occupied, player_cells=None):
        result = local_dijkstra_scan(self.get_pos(), VISION_RADIUS, grid, occupied)
        self.scan_cells = result["explored"]
        
        if player_cells:
            reachable_player = [cell for cell in player_cells if cell in result["distances"]]
            if reachable_player:
                target = min(reachable_player, key=lambda c: result["distances"][c])
                path = self._reconstruct_route(result["parents"], target)
                if len(path) > 1:
                    self.last_decision = "Dijkstra encontro jugador"
                    next_cell = path[1]
                    return next_cell, self._direction_to(next_cell)
        
        local_area = self._local_area(grid)
        border = self._local_border(local_area)
        reachable_border = [cell for cell in border if cell in result["distances"] and cell != self.get_pos()]
        
        if reachable_border:
            reachable_border.sort(key=self._blind_target_rank)
            
            # Preferir un objetivo que no implique retroceder a previous_pos inmediatamente
            best_path = None
            prev = getattr(self, "previous_pos", None)
            
            for target in reachable_border:
                path = self._reconstruct_route(result["parents"], target)
                if len(path) > 1 and path[1] != prev:
                    best_path = path
                    break
            
            # Si todos los caminos obligan a retroceder (ej. un callejón sin salida), tomamos el mejor
            if not best_path:
                best_path = self._reconstruct_route(result["parents"], reachable_border[0])
                
            if best_path and len(best_path) > 1:
                self.last_decision = "Dijkstra explora frontera 4"
                next_cell = best_path[1]
                return next_cell, self._direction_to(next_cell)

        self.last_decision = "Dijkstra sin destino"
        return self._fallback_dijkstra_neighbor(grid, occupied, None)

    def _local_area(self, grid):
        area = set()
        for row in range(self.row - VISION_RADIUS, self.row + VISION_RADIUS + 1):
            for col in range(self.col - VISION_RADIUS, self.col + VISION_RADIUS + 1):
                if (
                    abs(row - self.row) <= VISION_RADIUS
                    and abs(col - self.col) <= VISION_RADIUS
                    and grid.can_place_entity(row, col, 1)
                ):
                    area.add((row, col))
        return area

    def _local_border(self, local_area):
        return [
            cell for cell in local_area
            if abs(cell[0] - self.row) == VISION_RADIUS
            or abs(cell[1] - self.col) == VISION_RADIUS
        ]

    def _reconstruct_route(self, parents, target):
        route = []
        current = target
        while current is not None:
            route.append(current)
            current = parents.get(current)
        route.reverse()
        if not route or route[0] != self.get_pos():
            return []
        return route

    def _distance_from_start(self, cell):
        return abs(cell[0] - self.row) + abs(cell[1] - self.col)

    def _distance_to_player(self, cell, player_cells):
        if not player_cells:
            return 0
        return min(abs(cell[0] - row) + abs(cell[1] - col) for row, col in player_cells)

    def _blind_target_rank(self, cell):
        return (
            cell in self.explored,
            self._distance_from_start(cell),
            self._direction_priority_to(cell),
            cell[0],
            cell[1],
        )

    def _direction_priority_to(self, cell):
        dr = cell[0] - self.row
        dc = cell[1] - self.col
        if abs(dr) >= abs(dc):
            primary = (1 if dr > 0 else -1, 0)
        else:
            primary = (0, 1 if dc > 0 else -1)
        for index, (move_dr, move_dc, _) in enumerate(MOVE_DIRECTIONS):
            if primary == (move_dr, move_dc):
                return index
        return len(MOVE_DIRECTIONS)

    def _fallback_dijkstra_neighbor(self, grid, occupied, avoid):
        moves = get_valid_moves(self.get_pos(), grid, occupied)
        if avoid:
            moves = [m for m in moves if m[1] not in avoid]
        if not moves:
            return None, "quieto"
        _, pos, name = min(moves, key=lambda m: self._blind_target_rank(m[1]))
        return pos, name

    def _move_one_cell(self, next_cell, direction):
        if next_cell is None or next_cell == self.get_pos():
            self.last_direction = direction
            return

        row_delta = abs(next_cell[0] - self.row)
        col_delta = abs(next_cell[1] - self.col)
        if row_delta + col_delta != 1:
            self.last_direction = "bloqueado"
            return

        self.previous_pos = self.get_pos()
        self.recent_positions.append(next_cell)
        if len(self.recent_positions) > 8:
            self.recent_positions.pop(0)
        self.row, self.col = next_cell
        self.visited.add(next_cell)
        self.last_direction = direction
        self._record_footstep()

    def _detect_cycle(self):
        """Detecta si el enemigo esta en un ciclo repetitivo de posiciones."""
        n = len(self.recent_positions)
        if n < 4:
            return False
        p = self.recent_positions
        # Ciclo de 2: A-B-A-B
        if p[-1] == p[-3] and p[-2] == p[-4]:
            return True
        # Ciclo de 3: A-B-C-A-B-C
        if n >= 6 and p[-1] == p[-4] and p[-2] == p[-5] and p[-3] == p[-6]:
            return True
        return False

    def _direction_to(self, target):
        dr = target[0] - self.row
        dc = target[1] - self.col
        for move_dr, move_dc, name in MOVE_DIRECTIONS:
            if (dr, dc) == (move_dr, move_dc):
                return name
        return "quieto"

    def _record_footstep(self):
        pos = self.get_pos()
        if pos not in self.explored:
            self.explored.append(pos)

    def _update_astar(self, grid, player_pos, occupied):
        """Persecucion informada con A*."""
        if self._needs_recalculate_astar():
            start = (self.row, self.col)
            player_cells = set(grid.entity_cells(*player_pos, PLAYER_SIZE))
            result = astar(grid, start, player_cells)

            self.last_result = result
            self.path = result.path
            self.path_index = 0
            self.steps_taken = 0

        if self.path and self.path_index < len(self.path) - 1:
            next_index = self.path_index + 1
            next_cell = self.path[next_index]

            if next_cell not in occupied:
                direction = self._direction_to(next_cell)
                self.path_index = next_index
                self.row = next_cell[0]
                self.col = next_cell[1]
                self.last_direction = direction
                self.last_decision = "A* persigue objetivo"
                self._record_footstep()

        self.steps_taken += 1

    def get_pos(self):
        return (self.row, self.col)

    def update_visual(self, dt):
        amount = min(1.0, ENTITY_LERP_SPEED * dt / 1000.0)
        self.visual_row += (self.row - self.visual_row) * amount
        self.visual_col += (self.col - self.visual_col) * amount
