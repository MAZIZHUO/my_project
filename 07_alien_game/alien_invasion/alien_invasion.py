import sys

import pygame as pg


class AlienInvasion:
    def __init__(self):
        """初始化游戏并创建游戏资源"""
        pg.init()  # 初始化游戏
        self.screen = pg.display.set_mode((1000, 500))  # 创建一个1000x500的窗口
        pg.display.set_caption("Alien Invasion")  # 设置窗口标题
        self.clock = pg.time.Clock()  # 创建一个时钟对象来控制游戏帧率

    def run_game(self):
        """开始游戏主循环"""
        while True:
            for event in pg.event.get():  # 检查事件
                if event.type == pg.QUIT:  # 检查是否点击了退出按钮
                    sys.exit()  # 退出游戏,sys.exit()函数会引发SystemExit异常，除非被捕获，否则会导致Python解释器退出。
            self.screen.fill((230, 230, 230))  # 设置背景色
            pg.display.flip()  # 更新屏幕
            self.clock.tick(60)  # 控制游戏帧率为60


if __name__ == "__main__":
    ai = AlienInvasion()
    ai.run_game()
