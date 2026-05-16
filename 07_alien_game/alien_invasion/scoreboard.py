import pygame as pg
from ship import Ship


class Scoreboard:
    """显示得分信息的类"""

    def __init__(self, ai_game):
        """初始化显示得分的属性"""
        self.ai_game = ai_game  # 游戏实例,它包含了AlienInvasion实例的所有资源
        self.screen = ai_game.screen
        self.screen_rect = self.screen.get_rect()
        self.settings = ai_game.settings
        self.stats = ai_game.stats

        # 显示得分信息时使用的字体设置
        self.text_color = (30, 30, 30)
        self.font = pg.font.SysFont(None, 48)

        # 准备图像
        self.prep_score()
        self.prep_high_score()
        self.prep_level()
        self.prep_ships()

    # 显示得分
    def prep_score(self):
        """将得分转换为一幅渲染的图像"""
        rounded_score = int(
            round(self.stats.score, -1)
        )  # 将得分四舍五入到最近的10的倍数
        score_str = "{:,}".format(rounded_score)  # 将得分转换为字符串，并在其中添加逗号

        # 1. 创建一个用于显示得分的图像
        self.score_image = self.font.render(
            score_str, True, self.text_color, self.settings.bg_color
        )

        # 2. 图片的位置
        self.score_rect = self.score_image.get_rect()

        # 3. 定位
        self.score_rect.right = self.screen_rect.right - 20
        self.score_rect.top = 20

    # 显示最高得分
    def prep_high_score(self):
        """将最高得分转换成一幅渲染的图像"""
        high_score = int(
            round(self.stats.high_score, -1)
        )  # 将得分四舍五入到最近的10的倍数,并转换为整数
        high_score_str = "{:,}".format(high_score)

        # 1. 创建一个用于显示最高得分的图像
        self.high_score_image = self.font.render(
            high_score_str, True, self.text_color, self.settings.bg_color
        )

        # 2. 图片的位置
        self.high_score_rect = self.high_score_image.get_rect()

        # 3. 定位
        self.high_score_rect.centerx = self.screen_rect.centerx  # 居中
        self.high_score_rect.top = self.score_rect.top  # 与得分的top对齐

    # 显示等级
    def prep_level(self):
        """将等级转换为一幅渲染的图像"""
        level = self.stats.level
        level_str = str(level)
        # 1. 创建一个用于显示等级的图像
        self.level_image = self.font.render(
            level_str, True, self.text_color, self.settings.bg_color
        )
        # 2. 图片的位置
        self.level_rect = self.level_image.get_rect()
        # 3. 定位
        self.level_rect.right = self.score_rect.right  # 与得分的right对齐
        self.level_rect.top = self.score_rect.bottom + 10  # 在得分的下方10像素处

    # 准备飞船组
    def prep_ships(self):
        """显示还余下多少艘飞船"""
        self.ships = pg.sprite.Group()
        for ship_number in range(self.stats.ships_left):
            ship = Ship(self.ai_game)
            ship.rect.x = 10 + ship_number * ship.rect.width
            ship.rect.y = 10
            self.ships.add(ship)

    # 画到屏幕上
    def show_score(self):
        """在屏幕上显示得分"""
        self.screen.blit(self.score_image, self.score_rect)
        self.screen.blit(self.high_score_image, self.high_score_rect)
        self.screen.blit(self.level_image, self.level_rect)
        self.ships.draw(self.screen)
