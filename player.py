# ============================================================
# player.py — Entidad del jugador
# ============================================================

import pygame
from constants import PLAYER_MOVE_DELAY


class Player:
    """
    El jugador se mueve con WASD o flechas.
    Solo puede moverse a celdas caminables.
    """

    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.move_timer = 0  # Tiempo restante antes del próximo movimiento

    def handle_input(self, keys, grid, dt):
        """
        Lee el teclado y mueve al jugador si es posible.
        dt = tiempo transcurrido en milisegundos.
        """
        # Esperar antes de permitir otro movimiento
        self.move_timer -= dt
        if self.move_timer > 0:
            return

        moved = False

        # Arriba
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            if grid.is_walkable(self.row - 1, self.col):
                self.row -= 1
                moved = True

        # Abajo
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            if grid.is_walkable(self.row + 1, self.col):
                self.row += 1
                moved = True

        # Izquierda
        elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
            if grid.is_walkable(self.row, self.col - 1):
                self.col -= 1
                moved = True

        # Derecha
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            if grid.is_walkable(self.row, self.col + 1):
                self.col += 1
                moved = True

        if moved:
            self.move_timer = PLAYER_MOVE_DELAY

    def get_pos(self):
        """Retorna la posición actual como tupla (row, col)."""
        return (self.row, self.col)
