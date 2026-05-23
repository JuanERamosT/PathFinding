# ============================================================
# enemy.py — Enemigo con inteligencia evolutiva
# ============================================================
#
# COMPORTAMIENTO POR ALGORITMO:
#
#   DFS:      Exploración CIEGA con stack.
#             No sabe dónde está el jugador.
#             Se mueve nodo por nodo siguiendo la pila.
#
#   Dijkstra: Exploración CIEGA con min-heap.
#             No sabe dónde está el jugador.
#             Expande el nodo de menor costo acumulado.
#
#   A*:       Persecución INFORMADA con heurística.
#             SÍ sabe dónde está el jugador.
#             Calcula y sigue el camino óptimo.
#
# ============================================================

from constants import (
    ENEMY_SPEEDS, ASTAR_RECALC_STEPS,
    DFS_COLOR, DIJKSTRA_COLOR, ASTAR_COLOR
)
from pathfinding import astar, DFSExplorer, DijkstraExplorer


class Enemy:
    """Enemigo que busca al jugador."""

    def __init__(self, row, col, algorithm="dfs"):
        self.row = row
        self.col = col
        self.algorithm = algorithm
        self.move_timer = 0

        # Posición visual para movimiento suave
        self.visual_row = float(row)
        self.visual_col = float(col)

        # Explorador ciego (DFS / Dijkstra)
        self.explorer = None

        # Camino calculado (solo A*)
        self.path = []
        self.path_index = 0
        self.steps_taken = 0

        # Para visualización
        self.explored = []
        self.last_result = None

    def set_algorithm(self, algorithm):
        self.algorithm = algorithm
        self.explorer = None
        self.path = []
        self.path_index = 0
        self.steps_taken = 0

    def get_color(self):
        colors = {"dfs": DFS_COLOR, "dijkstra": DIJKSTRA_COLOR, "astar": ASTAR_COLOR}
        return colors.get(self.algorithm, DFS_COLOR)

    def get_move_delay(self):
        return ENEMY_SPEEDS.get(self.algorithm, 200)

    def get_algorithm_name(self):
        names = {"dfs": "DFS", "dijkstra": "Dijkstra", "astar": "A*"}
        return names.get(self.algorithm, "???")

    # ---- Inicialización del explorador ciego ----

    def _init_explorer(self, grid):
        """Crea un explorador nuevo desde la posición actual."""
        start = (self.row, self.col)
        if self.algorithm == "dfs":
            self.explorer = DFSExplorer(grid, start)
        elif self.algorithm == "dijkstra":
            self.explorer = DijkstraExplorer(grid, start)

    # ---- A*: persecución informada ----

    def _needs_recalculate_astar(self):
        if not self.path:
            return True
        if self.path_index >= len(self.path) - 1:
            return True
        if self.steps_taken >= ASTAR_RECALC_STEPS:
            return True
        return False

    # ---- Actualización principal ----

    def update(self, grid, player_pos, dt, occupied=None):
        """
        Mueve al enemigo un paso.
        - DFS/Dijkstra: exploración ciega (no conocen player_pos).
        - A*: persecución informada hacia player_pos.
        - occupied: set de celdas ocupadas por otros enemigos.
        """
        self.move_timer -= dt
        if self.move_timer > 0:
            return

        if occupied is None:
            occupied = set()

        if self.algorithm in ("dfs", "dijkstra"):
            self._update_blind(grid, occupied)
        else:
            self._update_astar(grid, player_pos, occupied)

        self.move_timer = self.get_move_delay()

    def _update_blind(self, grid, occupied):
        """Exploración ciega paso a paso (DFS o Dijkstra)."""
        # Crear explorador si no existe o terminó
        if self.explorer is None or self.explorer.finished:
            self._init_explorer(grid)

        next_cell = self.explorer.step()

        if next_cell is not None:
            # Anti-superposición: solo moverse si la celda está libre
            if next_cell not in occupied:
                self.row, self.col = next_cell
            # Actualizar historial de exploración para visualización
            self.explored = list(self.explorer.explored)
        else:
            # Se agotó la exploración → reiniciar desde posición actual
            self._init_explorer(grid)

    def _update_astar(self, grid, player_pos, occupied):
        """Persecución informada con A* (SÍ conoce player_pos)."""
        if self._needs_recalculate_astar():
            start = (self.row, self.col)
            result = astar(grid, start, player_pos)

            self.last_result = result
            self.path = result.path
            self.explored = result.explored
            self.path_index = 0
            self.steps_taken = 0

        # Avanzar un paso por el camino
        if self.path and self.path_index < len(self.path) - 1:
            next_index = self.path_index + 1
            next_cell = self.path[next_index]

            # Anti-superposición
            if next_cell not in occupied:
                self.path_index = next_index
                self.row = next_cell[0]
                self.col = next_cell[1]

        self.steps_taken += 1

    def get_pos(self):
        return (self.row, self.col)

    def update_visual(self, dt):
        """Interpola la posición visual hacia la posición lógica."""
        lerp_speed = 15.0
        t = min(1.0, lerp_speed * dt / 1000.0)
        self.visual_row += (self.row - self.visual_row) * t
        self.visual_col += (self.col - self.visual_col) * t
