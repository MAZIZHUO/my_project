from pathlib import Path

import pygame as pg
from pygame.sprite import Sprite


class Alien(Sprite):
    def __init__(self, ai_game, x_pos=0, y_pos=0):
        super().__init__()
        self.screen = ai_game.screen
        self.screen_rect = ai_game.screen.get_rect()
        self.settings = ai_game.settings

        # 外星人图片+尺寸位置（rect对象）
        current_dir = Path(__file__).parent
        self.image = pg.image.load(str(current_dir / "images/alien.png"))
        self.image = pg.transform.smoothscale(self.image, (60, 60))
        self.rect = self.image.get_rect()

        # 定位
        self.rect.x = x_pos
        self.rect.y = y_pos

    # 移动外星人
    def update(self, is_move_down=True):
        if is_move_down:
            self.rect.y += self.settings.fleet_drop_speed
        self.rect.x += self.settings.alien_speed * self.settings.fleet_direction

    # 判断外星人是否碰到屏幕边缘
    def check_edges(self):
        return (self.rect.left < 0) or (self.rect.right > self.screen_rect.right)
