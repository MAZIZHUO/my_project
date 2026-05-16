import sys

import pygame as pg
from alien import Alien
from bullet import Bullet
from button import Button
from game_stats import GameStats
from scoreboard import Scoreboard
from settings import Settings
from ship import Ship


class AlienInvasion:
    def __init__(self):
        """初始化游戏并创建游戏资源"""
        pg.init()  # 初始化游戏
        self.settings = Settings()  # 创建一个Settings对象
        self.screen = pg.display.set_mode(
            (self.settings.screen_width, self.settings.screen_height)
        )  # 创建一个窗口
        pg.display.set_caption("Alien Invasion")  # 设置窗口标题
        self.clock = pg.time.Clock()  # 创建一个时钟对象来控制游戏帧率
        self.ship = Ship(self)  # 创建一个飞船对象
        self.bullets = pg.sprite.Group()  # 创建一个子弹精灵组
        self.aliens = pg.sprite.Group()  # 创建一个外星人精灵组
        self._create_fleet()  # 创建外星人群
        self.stats = GameStats(self)  # 创建一个游戏状态对象
        self.game_active = False  # 游戏是否处于活动状态
        self.play_button = Button(self, "Play")  # 创建一个按钮对象
        self.scoreboard = Scoreboard(self)  # 创建一个得分板对象

    # 创建外星人群方法
    def _create_fleet(self):
        """创建外星人群"""
        alien = Alien(self)  # 创建一个外星人
        alien_width, alien_height = alien.rect.size  # 获取外星人的宽度和高度

        current_x, current_y = alien_width, alien_height  # 获取外星人的初始位置

        while current_y < self.settings.screen_height - 4 * alien_height:
            while current_x < self.settings.screen_width - 2 * alien_width:
                new_alien = Alien(self, current_x, current_y)  # 创建一个新的外星人
                self.aliens.add(new_alien)  # 将新的外星人添加到外星人精灵组中
                current_x += alien_width * 2  # 更新下一个外星人的x坐标

            current_x = alien_width  # 重置x坐标
            current_y += alien_height * 2  # 更新y坐标

    # 检查外星人是否碰到屏幕边缘方法
    def _check_fleet_edges(self):
        """有外星人到达边缘时采取相应的措施"""
        for alien in self.aliens.sprites():  # 遍历所有外星人
            if alien.check_edges():  # 检查外星人是否到达边缘
                return True
        return False

    # 让整个外星人舰队进行移动更新
    def _update_fleet(self):
        """检查是否到达边缘，并更新整群外星人的位置"""
        is_out_of_bounds = self._check_fleet_edges()  # 检查外星人是否到达边缘
        if is_out_of_bounds:
            self.settings.fleet_direction *= -1  # 将外星人群的移动方向向左或向右改变
        self.aliens.update(
            is_out_of_bounds
        )  # 更新外星人位置，is_out_of_bounds参数决定是否让外星人向下移动

        # 检查飞船和外星人之间的碰撞
        if pg.sprite.spritecollideany(
            self.ship, self.aliens
        ):  # 检查飞船是否被外星人撞到
            print("Ship hit!!!")  # 打印提示信息
            self._reset_game()  # 重置游戏

        # 检查是否有外星人到达了屏幕底部
        self._check_aliens_bottom()

    # 检查是否有外星人到达了屏幕底部方法
    def _check_aliens_bottom(self):
        """检查是否有外星人到达了屏幕底部"""
        screen_rect = self.screen.get_rect()  # 获取屏幕的矩形对象
        for alien in self.aliens.sprites():  # 遍历所有外星人
            if alien.rect.bottom >= screen_rect.bottom:  # 检查外星人是否到达了屏幕底部
                print("Alien hit the bottom!!!")
                self._reset_game()  # 重置游戏
                break

    # 重置游戏方法
    def _reset_game(self):
        """重置游戏"""
        self.stats.ships_left -= 1  # 飞船数量减1
        if self.stats.ships_left > 0:  # 如果飞船数量大于0
            self.aliens.empty()  # 清空外星人精灵组
            self.bullets.empty()  # 清空子弹精灵组

            self._create_fleet()  # 创建外星人群
            self.ship.center_ship()  # 让飞船在屏幕底部居中

            pg.time.wait(500)  # 暂停500毫秒
        else:
            self.game_active = False
            pg.mouse.set_visible(True)  # 显示光标

    # 提取-处理键盘按下事件方法
    def _check_keydown_events(self, event):
        """响应按键"""
        if event.key == pg.K_RIGHT:  # 如果按下右箭头键
            self.ship.moving_right = True  # 移动飞船向右
        elif event.key == pg.K_LEFT:  # 如果按下左箭头键
            self.ship.moving_left = True  # 移动飞船向左
        elif event.key == pg.K_UP:  # 如果按下上箭头键
            self.ship.moving_up = True  # 移动飞船向上
        elif event.key == pg.K_DOWN:  # 如果按下下箭头键
            self.ship.moving_down = True
        elif event.key == pg.K_q:  # 如果按下 Q 键
            sys.exit()  # 退出游戏
        elif event.key == pg.K_SPACE:  # 如果按下空格键
            self._fire_bullet()  # 发射子弹

    # 提取-发射子弹方法
    def _fire_bullet(self):
        """创建一颗子弹，并将其加入到编组bullets中"""
        if len(self.bullets) < self.settings.bullets_allowed:  # 限制屏幕上子弹数量
            bullet = Bullet(self)
            self.bullets.add(bullet)

    # 提取-更新子弹位置方法
    def _update_bullets(self):
        """更新子弹的位置，并删除已消失的子弹"""
        self.bullets.update()  # 更新子弹位置

        # 删除已消失的子弹
        for bullet in self.bullets.copy():
            if bullet.rect.bottom <= 0:
                self.bullets.remove(bullet)

        # 检查子弹和外星人之间的碰撞
        self._check_bullet_alien_collisions()

    # 检查子弹和外星人之间的碰撞方法
    def _check_bullet_alien_collisions(self):
        """响应子弹和外星人的碰撞"""
        # 检查是否有子弹击中了外星人
        # 如果是这样，就删除相应的子弹和外星人
        collisions = pg.sprite.groupcollide(
            self.bullets, self.aliens, True, True
        )  # 检查是否有子弹击中了外星人,collisions是一个字典

        if collisions:  # 如果有子弹击中了外星人
            for aliens in collisions.values():  # 遍历字典的值
                self.stats.score += self.settings.alien_points * len(aliens)
            self.scoreboard.prep_score()  # 更新得分
            self.scoreboard.prep_high_score()  # 更新最高得分

        if not self.aliens:  # 如果外星人群已清空
            self.bullets.empty()  # 清空子弹
            self._create_fleet()  # 创建一个新的外星人群
            self.ship.center_ship()  # 让飞船在屏幕底部居中
            self.settings.increase_speed()  # 提高游戏速度
            self.stats.level += 1  # 提高等级
            self.scoreboard.prep_level()  # 更新等级显示

    # 提取-处理键盘松开事件方法
    def _check_keyup_events(self, event):
        """响应松开"""
        if event.key == pg.K_RIGHT:  # 如果松开右箭头键
            self.ship.moving_right = False  # 停止飞船向右移动
        elif event.key == pg.K_LEFT:  # 如果松开左箭头键
            self.ship.moving_left = False  # 停止飞船向左移动
        elif event.key == pg.K_UP:  # 如果松开上箭头键
            self.ship.moving_up = False  # 停止飞船向上移动
        elif event.key == pg.K_DOWN:  # 如果松开下箭头键
            self.ship.moving_down = False
        elif event.key == pg.K_SPACE:  # 如果松开空格键
            pass  # 目前不需要对松开空格键做任何处理

    # 提取-事件处理方法
    def _check_events(self):
        """响应按键和鼠标事件"""
        for event in pg.event.get():  # 检查事件
            if event.type == pg.QUIT:  # 检查是否点击了退出按钮
                sys.exit()  # 退出游戏,sys.exit()函数会引发SystemExit异常，除非被捕获，否则会导致Python解释器退出。

            elif event.type == pg.KEYDOWN:  # 检查按键是否被按下
                self._check_keydown_events(event)  # 响应按键事件

            elif event.type == pg.KEYUP:  # 检查按键是否被松开
                self._check_keyup_events(event)  # 响应松开事件

            elif event.type == pg.MOUSEBUTTONDOWN:  # 检查鼠标是否被点击
                mouse_pos = pg.mouse.get_pos()  # 获取鼠标位置
                self._check_play_button(mouse_pos)  # 检查按钮点击

    # 检查按钮点击方法
    def _check_play_button(self, mouse_pos):
        """在玩家单击Play按钮时开始新游戏"""
        # 检查鼠标位置是否在Play按钮的rect内
        button_clicked = self.play_button.rect.collidepoint(
            mouse_pos
        )  # 检查鼠标位置是否在Play按钮的rect内
        if (
            button_clicked and not self.game_active
        ):  # 如果鼠标点击了Play按钮且游戏处于非活动状态
            self.stats.reset_stats()  # 重置游戏统计信息
            self.game_active = True  # 将游戏状态设置为活动状态

            # 清空外星人列表和子弹列表
            self.aliens.empty()
            self.bullets.empty()

            # 创建一群新的外星人，并让飞船在屏幕底部居中
            self._create_fleet()
            self.ship.center_ship()

            # 隐藏光标
            pg.mouse.set_visible(False)

            # 恢复速度
            self.settings.initialize_dynamic_settings()

            # 更新得分
            self.scoreboard.prep_score()
            self.scoreboard.prep_level()

    # 提取-绘制游戏窗口方法
    def _update_screen(self):
        """更新屏幕上的图像，并切换到新屏幕"""
        self.screen.fill(self.settings.bg_color)  # 填充背景色
        for bullet in self.bullets.sprites():  # 在屏幕上绘制所有子弹
            bullet.draw_bullet()
        self.ship.blitme()  # 在指定位置绘制飞船
        self.aliens.draw(self.screen)  # 在屏幕上绘制所有外星人
        if not self.game_active:  # 如果游戏处于非活动状态
            self.play_button.draw_button()  # 绘制Play按钮

        self.scoreboard.show_score()  # 显示得分
        pg.display.flip()  # 更新屏幕

    # 游戏主循环方法
    def run_game(self):
        """开始游戏主循环"""
        while True:
            # 第一部分：处理事件
            self._check_events()  # 响应事件

            # 第二部分：更新游戏状态，包括飞船位置和子弹位置
            if self.game_active:  # 只有当游戏处于活动状态时才更新游戏状态
                self.ship.update()  # 更新飞船位置
                self._update_bullets()  # 更新子弹位置
                self._update_fleet()  # 更新外星人位置

            # 第三部分：更新屏幕上的图像，并切换到新屏幕
            self._update_screen()  # 更新屏幕
            self.clock.tick(60)  # 控制游戏帧率为60


if __name__ == "__main__":
    ai = AlienInvasion()
    ai.run_game()
