from pathlib import Path

import pygame as pg
from pygame.sprite import Sprite


# 飞船类,继承Sprite 类
class Ship(Sprite):
    # ai_game为实例对象,它包含了AlienInvasion实例的所有资源
    def __init__(self, ai_game):
        super().__init__()
        self.screen = ai_game.screen
        self.screen_rect = ai_game.screen.get_rect()
        self.settings = ai_game.settings

        # 获取当前 ship.py 文件所在的真实绝对路径
        current_dir = Path(__file__).parent
        self.image = pg.image.load(str(current_dir / "images/ship.png"))

        # 使用 smoothscale 将图片缩小到 60x60 像素（你可以根据喜好调整这两个数字）
        self.image = pg.transform.smoothscale(self.image, (60, 60))

        self.rect = self.image.get_rect()
        self.center_ship()

        # 给飞船设置移动标志位
        self.moving_right = False
        self.moving_left = False
        self.moving_up = False
        self.moving_down = False

    def update(self):
        """根据移动标志位移动飞船"""
        if self.moving_right and self.rect.right < self.screen_rect.right:
            self.rect.right += self.settings.ship_speed  # 持续向右移动
        if self.moving_left and self.rect.left > 0:
            self.rect.left -= self.settings.ship_speed  # 持续向左移动

        if self.moving_up and self.rect.top > 0:
            self.rect.top -= self.settings.ship_speed  # 持续向上移动
        if self.moving_down and self.rect.bottom < self.screen_rect.bottom:
            self.rect.bottom += self.settings.ship_speed

    def center_ship(self):
        """让飞船在屏幕底部居中"""
        self.rect.midbottom = self.screen_rect.midbottom

    def blitme(self):
        """在指定位置绘制飞船"""
        self.screen.blit(self.image, self.rect)
