# ============================================================
# pathfinding.py - Algoritmos de busqueda en grafos
# ============================================================
#
# Reglas implementadas:
# - explored son nodos visitados por la busqueda.
# - path es SOLO el camino reconstruido con parent al llegar a la meta.
# - Los movimientos son solo 4 direcciones.
# - Cada movimiento cuesta 10.
# - A* usa heuristica Manhattan.
# ============================================================

import heapq
import time as _time

MOVE_DIRECTIONS = [
    (-1, 0, "arriba"),
    (0, 1, "derecha"),
    (1, 0, "abajo"),
    (0, -1, "izquierda"),
]


STRAIGHT_COST = 10


def _timer():
    return _time.perf_counter_ns()


def _elapsed_ms(start_ns):
    return (_time.perf_counter_ns() - start_ns) / 1_000_000


class PathResult:
    """Resultado estandarizado de cualquier algoritmo."""

    def __init__(self):
        self.path = []
        self.explored = []
        self.nodes_explored = 0
        self.time_ms = 0.0
        self.total_cost = 0


def _reconstruct_path(parent, goal):
    """Reconstruye el camino desde goal hasta inicio usando parent."""
    path = []
    current = goal
    while current is not None:
        path.append(current)
        current = parent[current]
    path.reverse()
    return path


def _move_cost(a, b):
    return STRAIGHT_COST


def _path_cost(path):
    return sum(_move_cost(a, b) for a, b in zip(path, path[1:]))


def _finish(result, parent, goal, cost=None):
    result.path = _reconstruct_path(parent, goal)
    result.total_cost = _path_cost(result.path) if cost is None else cost


def _as_goals(goal):
    if isinstance(goal, tuple) and len(goal) == 2 and all(isinstance(value, int) for value in goal):
        return {goal}
    return set(goal)



def heuristic(a, b):
    """Heuristica Manhattan para movimiento en 4 direcciones."""
    dy = abs(a[0] - b[0])
    dx = abs(a[1] - b[1])
    return STRAIGHT_COST * (dx + dy)


def _heuristic_to_goals(node, goals):
    return min(heuristic(node, goal) for goal in goals)


def _dfs_neighbors(grid, start, current, size):
    def sweep_rank(node):
        row, col = node
        if row < start[0]:
            return grid.rows * grid.cols + (start[0] - row) * grid.cols + col
        row_delta = row - start[0]
        going_right = row_delta % 2 == 0
        if row_delta == 0:
            if col >= start[1]:
                return col - start[1]
            return grid.cols + col
        if going_right:
            return row_delta * grid.cols + col
        return row_delta * grid.cols + (grid.cols - 1 - col)

    neighbors = grid.get_neighbors(*current, size)
    return sorted(neighbors, key=sweep_rank)


# ============================================================
# NIVEL 1: DFS (Depth-First Search)
# ============================================================

def dfs(grid, start, goal, size=1):
    """
    DFS real:
    - usa stack
    - marca visitado al meter en la pila
    - guarda parent
    - reconstruye el camino final solo al encontrar la meta
    """
    result = PathResult()
    t0 = _timer()

    goals = _as_goals(goal)
    if not grid.can_place_entity(*start, size) or not any(grid.can_place_entity(*node, size) for node in goals):
        result.time_ms = _elapsed_ms(t0)
        return result

    stack = [start]
    visited = {start}
    parent = {start: None}
    found = False

    while stack:
        current = stack.pop()
        result.explored.append(current)

        if current in goals:
            found = True
            goal = current
            break

        # Stack = LIFO, por eso se empuja en reversa.
        for neighbor in reversed(_dfs_neighbors(grid, start, current, size)):
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                stack.append(neighbor)

    if found:
        _finish(result, parent, goal)

    result.time_ms = _elapsed_ms(t0)
    result.nodes_explored = len(result.explored)
    return result


# ============================================================
# NIVEL 2: Dijkstra
# ============================================================

def dijkstra(grid, start, goal, size=1):
    """Dijkstra con min-heap, distancias y parent map."""
    result = PathResult()
    t0 = _timer()

    goals = _as_goals(goal)
    if not grid.can_place_entity(*start, size) or not any(grid.can_place_entity(*node, size) for node in goals):
        result.time_ms = _elapsed_ms(t0)
        return result

    distances = {start: 0}
    parent = {start: None}
    visited = set()
    heap = [(0, 0, start)]
    tie_breaker = 1
    found = False

    while heap:
        current_distance, _, current = heapq.heappop(heap)

        if current in visited:
            continue
        if current_distance != distances.get(current, float("inf")):
            continue

        visited.add(current)
        result.explored.append(current)

        if current in goals:
            found = True
            goal = current
            break

        for neighbor in grid.get_neighbors(*current, size):
            new_distance = current_distance + _move_cost(current, neighbor)
            if new_distance < distances.get(neighbor, float("inf")):
                distances[neighbor] = new_distance
                parent[neighbor] = current
                heapq.heappush(heap, (new_distance, tie_breaker, neighbor))
                tie_breaker += 1

    if found:
        _finish(result, parent, goal, distances[goal])

    result.time_ms = _elapsed_ms(t0)
    result.nodes_explored = len(result.explored)
    return result


# ============================================================
# NIVEL 3: A* (A-Star)
# ============================================================

def astar(grid, start, goal, size=1):
    """A* con f(n)=g(n)+h(n), heuristica Manhattan y control de duplicados."""
    result = PathResult()
    t0 = _timer()

    goals = _as_goals(goal)
    if not grid.can_place_entity(*start, size) or not any(grid.can_place_entity(*node, size) for node in goals):
        result.time_ms = _elapsed_ms(t0)
        return result

    g_score = {start: 0}
    parent = {start: None}
    visited = set()
    start_h = _heuristic_to_goals(start, goals)
    heap = [(start_h, start_h, 0, 0, start)]
    tie_breaker = 1
    found = False

    while heap:
        current_f, current_h, current_g, _, current = heapq.heappop(heap)

        if current in visited:
            continue
        if current_g != g_score.get(current, float("inf")):
            continue

        visited.add(current)
        result.explored.append(current)

        if current in goals:
            found = True
            goal = current
            break

        for neighbor in grid.get_neighbors(*current, size):
            tentative_g = current_g + _move_cost(current, neighbor)
            if tentative_g < g_score.get(neighbor, float("inf")):
                parent[neighbor] = current
                g_score[neighbor] = tentative_g
                h_score = _heuristic_to_goals(neighbor, goals)
                f_score = tentative_g + h_score
                heapq.heappush(heap, (f_score, h_score, tentative_g, tie_breaker, neighbor))
                tie_breaker += 1

    if found:
        _finish(result, parent, goal, g_score[goal])

    result.time_ms = _elapsed_ms(t0)
    result.nodes_explored = len(result.explored)
    return result


# ============================================================
# LOGICA DE AGENTES FISICOS (PASO A PASO)
# ============================================================

def get_valid_moves(current, grid, occupied):
    """Devuelve los movimientos validos desde una posicion (indice, pos, nombre)."""
    moves = []
    for index, (dr, dc, name) in enumerate(MOVE_DIRECTIONS):
        row = current[0] + dr
        col = current[1] + dc
        pos = (row, col)
        if grid.can_move_entity(current[0], current[1], dr, dc, 1) and pos not in occupied:
            moves.append((index, pos, name))
    return moves

def dfs_next_step(current_pos, visited, backtrack_stack, grid, occupied):
    """
    Toma una decision pura de DFS para un agente fisico.
    Retorna (next_pos, direction_name, status_message).
    """
    moves = get_valid_moves(current_pos, grid, occupied)
    unvisited = [(i, pos, name) for i, pos, name in moves if pos not in visited]

    if unvisited:
        _, pos, name = unvisited[0]
        backtrack_stack.append(current_pos)
        return pos, name, "DFS explora periferia"

    while backtrack_stack:
        back_pos = backtrack_stack.pop()
        for _, pos, name in moves:
            if pos == back_pos:
                return pos, name, "DFS retrocede"

    if moves:
        return None, "quieto", "Fin exploracion DFS"

    return None, "quieto", "Sin salida"

def greedy_next_step(current_pos, player_cells, previous_pos, grid, occupied):
    """
    Persecucion voraz (Greedy Descent) para alcanzar al jugador.
    Retorna (next_pos, direction_name, status_message).
    """
    moves = get_valid_moves(current_pos, grid, occupied)
    if not moves:
        return None, "quieto", "quieto"

    def distance_to_player(pos):
        return min(abs(pos[0] - pr) + abs(pos[1] - pc) for pr, pc in player_cells)

    # Evita la posicion anterior para rodear paredes (suaviza oscilaciones voraces)
    def move_score(item):
        pos = item[1]
        dist = distance_to_player(pos)
        penalty = 1000 if pos == previous_pos else 0
        return dist + penalty

    _, pos, name = min(moves, key=lambda item: (move_score(item), item[0]))
    return pos, name, "Jugador en periferia"

def local_dijkstra_scan(start, radius, grid, occupied):
    """
    Hace una espiral de Dijkstra sin un objetivo, evaluando todo el radio visible.
    Retorna el arbol de exploracion (espiral), parents y distancias.
    """
    distances = {start: 0}
    parent = {start: None}
    explored = []
    visited = set()
    heap = [(0, 0, start)]
    tie_breaker = 1

    while heap:
        current_cost, _, current = heapq.heappop(heap)
        if current in visited:
            continue
        if current_cost != distances.get(current, float("inf")):
            continue

        visited.add(current)
        explored.append(current)

        row, col = current
        for dr, dc, _ in MOVE_DIRECTIONS:
            neighbor = (row + dr, col + dc)
            
            # Limitar la busqueda al radio de vision local
            if abs(neighbor[0] - start[0]) > radius or abs(neighbor[1] - start[1]) > radius:
                continue
            if neighbor in occupied and neighbor != start:
                continue
            if not grid.can_move_entity(row, col, dr, dc, 1):
                continue

            new_cost = current_cost + STRAIGHT_COST
            if new_cost < distances.get(neighbor, float("inf")):
                distances[neighbor] = new_cost
                parent[neighbor] = current
                heapq.heappush(heap, (new_cost, tie_breaker, neighbor))
                tie_breaker += 1

    return {
        "explored": explored,
        "parents": parent,
        "distances": distances
    }

