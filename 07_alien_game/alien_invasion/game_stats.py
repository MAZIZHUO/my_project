# 游戏信息统计
class GameStats:
    """跟踪游戏的统计信息"""

    def __init__(self, ai_game):
        """初始化统计信息"""
        self.ai_game = ai_game  # 游戏实例,它包含了AlienInvasion实例的所有资源
        self.settings = ai_game.settings
        self.__ships_left = 0  # 剩余飞船数
        self.reset_stats()
        self.__high_score = 0  # 最高得分

    def reset_stats(self):
        """初始化在游戏运行期间可能变化的统计信息"""
        self.ships_left = self.settings.ship_limit
        self.__score = 0  # 得分
        self.level = 1  # 等级

    @property  # 当在外部访问 ships_left 属性时,会调用这个方法
    def ships_left(self):
        return self.__ships_left

    @ships_left.setter  # 当给 ships_left 属性赋值时,会调用这个方法
    def ships_left(self, value):
        self.__ships_left = value

        try:
            self.ai_game.scoreboard.prep_ships()  # 更新飞船数量显示
        except AttributeError:
            pass  # 如果scoreboard还没有初始化，则忽略

    @property
    def high_score(self):
        return self.__high_score

    @property
    def score(self):
        return self.__score

    @score.setter
    def score(self, value):
        self.__score = value

        if value > self.__high_score:
            self.__high_score = value
