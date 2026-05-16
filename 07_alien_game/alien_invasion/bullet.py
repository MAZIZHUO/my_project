import pygame as pg
from pygame.sprite import Sprite


class Bullet(Sprite):
    """一个对飞船发射的子弹进行管理的类"""

    def __init__(self, ai_game):
        """在飞船所处的位置创建一个子弹对象"""
        super().__init__()

        self.screen = ai_game.screen
        self.settings = ai_game.settings
        self.color = self.settings.bullet_color

        # 在(0,0)处创建一个表示子弹的矩形，再设置正确的位置
        self.rect = pg.Rect(
            0, 0, self.settings.bullet_width, self.settings.bullet_height
        )
        self.rect.midtop = ai_game.ship.rect.midtop

    def draw_bullet(self):
        """在屏幕上绘制子弹"""
        pg.draw.rect(self.screen, self.color, self.rect)

    def update(self):
        """向上移动子弹"""
        # 更新表示子弹位置的小数值
        self.rect.bottom -= self.settings.bullet_speed
        if self.rect.bottom < 0:
            self.kill()
