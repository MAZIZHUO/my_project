class Settings:
    def __init__(self):
        self.screen_width = 1000
        self.screen_height = 500
        self.bg_color = (230, 230, 230)

        # 飞船的配置
        # self.ship_speed = 8
        self.ship_limit = 3

        # 子弹的配置
        # self.bullet_speed = 8
        self.bullet_width = 3
        self.bullet_height = 15
        self.bullet_color = (60, 60, 60)
        self.bullets_allowed = 3

        # 外星人的配置
        # self.alien_speed = 3
        self.fleet_drop_speed = 10  # 外星人群向下移动的速度10像素
        # self.fleet_direction = 1  # 1表示向右移动，-1表示向左移动

        self.initialize_dynamic_settings()  # 初始化动态设置

        self.speedup_scale = 1.1
        self.score_scale = 1.5

    # 初始值
    def initialize_dynamic_settings(self):
        """初始化随游戏进行而变化的设置"""
        self.ship_speed = 8
        self.bullet_speed = 8
        self.alien_speed = 3

        self.fleet_direction = 1

        self.alien_points = 10

    # 加速
    def increase_speed(self):
        """提高速度设置"""
        self.ship_speed *= self.speedup_scale
        self.bullet_speed *= self.speedup_scale
        self.alien_speed *= self.speedup_scale

        self.alien_points = int(self.alien_points * self.score_scale)
