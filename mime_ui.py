# -*- coding:utf-8 -*-

from kivy.config import Config

# 不可更改窗口大小
# Config.set('graphics','resizable',0)
# Config.set('graphics','position','custom')
# Config.set('graphics','fullscreen','0')
Config.set('input', 'mouse', 'mouse,disable_multitouch')
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.app import App
from kivy.graphics import Color, Rectangle
from kivy.graphics.instructions import InstructionGroup
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.animation import Animation
from enum import Enum
import random
import os
import sys
import pickle
import time
import pdb

from mime_game import MimeCore


class MimeSweeper(App):
    def build(self):
        self.title = '扫雷'
        return Ground()


class StatusBar(Widget):
    def __init__(self, pos, size):
        super(StatusBar, self).__init__()
        self.size = size
        self.pos = pos
        image_size = (20, 20)

        self.btn_change_color = Button(size=image_size)

        self.btn_change_difficulty = Button(text='简单', size=(22, 20), font_name='simhei', font_size=10)
        self.btn_change_difficulty.background_color = [0.92, .92, .92, 1]
        self.btn_change_difficulty.background_normal = ''
        self.btn_change_difficulty.color = [0.2, 0.2, 0.2, 1]

        self.image_time = Image(source=resource_path("images/clock.png"), size=image_size)
        self.label_time = Label(text='0', font_size=16, size=(30, 20))
        self.label_time.color = [0.1, 0.1, 0.1, 1]

        self.image_mime = Image(source=resource_path("images/mime.png"), size=image_size)
        self.label_mime = Label(text='0', font_size=16, size=(30, 20))
        self.label_mime.color = [0.1, 0.1, 0.1, 1]

        self.update_background()
        self.updata_widget()
        self.add_widget(self.image_mime)
        self.add_widget(self.label_mime)
        self.add_widget(self.image_time)
        self.add_widget(self.label_time)
        self.add_widget(self.btn_change_difficulty)
        self.add_widget(self.btn_change_color)

    def update_background(self):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            Rectangle(size=self.size, pos=self.pos)
        pass

    def updata_widget(self):
        x = 20
        y = 10 + self.y
        self.image_time.pos = (x, y)
        self.label_time.pos = (x + self.image_time.width + 5, y)

        x = self.width / 2
        self.image_mime.pos = (x, y)
        self.label_mime.pos = (x + self.image_mime.width, y)

        x = self.width - self.btn_change_color.width - 5
        self.btn_change_color.pos = (x, y)

        x = self.btn_change_color.pos[0] - self.btn_change_difficulty.width - 5
        self.btn_change_difficulty.pos = (x, y)

    def update_content(self, time=None, mimes=None, button_text=None):
        if time is not None:
            self.label_time.text = str(time)
        if mimes is not None:
            self.label_mime.text = str(mimes)
        if button_text is not None:
            self.btn_change_difficulty.text = button_text


class SCREENS(Enum):
    GAME = 1
    LEVEL_CHOOSE = 2
    COLOR_CHOOSE = 3
    GAME_WIN = 4
    GAME_OVER = 5


class Ground(Widget):
    BLOCK_WIDTH = 20
    WIDTH = 0
    HEIGHT = 0
    LONG_CLICK_THRESHOLD = 1  # 1秒

    FONT_NAME = 'simhei'

    land = InstructionGroup()
    level_choose_dialog = InstructionGroup()
    failed_dialog = InstructionGroup()
    win_dialog = InstructionGroup()
    color_choose_dialog = InstructionGroup()
    animation_layer = InstructionGroup()

    TEXTURES = {}
    BUTTON_TEXTURES = []

    # 当前显示的界面
    CURRENT_SCREEN = SCREENS.LEVEL_CHOOSE
    LEVEL_TEXTS = ['简单', '一般', '困难', '高手', '大师', '传说']
    COLORFUL_BLOCKS = []
    COLORFUL_FLAGS = []
    COLORS = ['red', 'yellow', 'green', 'blue', 'purple', 'pink', 'normal', 'random']
    CURRENT_COLOR = random.randrange(0, 6)

    _GAME_PLAYED_TIMES = 0
    _WIN_TIMES = 0
    DETECTED_POSITIONS = []

    TACHED_BLOCKS = {}

    # 使用动画效果
    USE_ANIMATION = True
    REFRESH_RATE = 1 / 10
    ANIMATED_BLOCKS = {}

    millis_on_touch_down = 0
    touch_down_pos = None
    touch_down_instance = None
    core = MimeCore()

    # chect code
    CHECT_CODE = []

    def __init__(self, **kwargs):
        super(Ground, self).__init__(**kwargs)
        self.load_texture()
        self.WIDTH = 200
        self.HEIGHT = 200
        size = (self.WIDTH, 40)

        self.size = (self.WIDTH, self.HEIGHT)
        Window.size = (self.WIDTH, self.HEIGHT + 40)

        pos = (0, self.height)
        self.status_bar = StatusBar(pos, size)
        self.add_widget(self.status_bar)
        source_name = resource_path('images/block_%s.png' % self.COLORS[self.CURRENT_COLOR])
        self.status_bar.btn_change_color.background_normal = source_name

        self.bind(on_touch_down=self._on_touch_down)
        self.bind(on_touch_up=self._on_touch_up)
        Window.bind(on_key_down=self._on_key_down)
        Window.bind(on_close=self.save_game)
        self.bind(size=self._on_size)
        Clock.schedule_interval(self.update_board, 1 / 5)
        # Clock.schedule_interval(self.update_animation, self.ANIMATION_REFRESH_RATE)
        Window.set_icon(resource_path('images/flag_normal.png'))
        self.canvas.after.add(self.animation_layer)

        self._build_level_choose_dialog()
        if self.has_saved_data():
            self.load_game()
        else:
            self.choose_level()

    def _on_size(self, instance, size):
        if size[0] == self.WIDTH and size[1] == self.HEIGHT:
            return
        if not size[0] == self.WIDTH or not size[1] == self.HEIGHT + self.status_bar.size[1]:
            # calculate..
            usable_height = size[1] - self.status_bar.size[1]
            fixed_block_width = usable_height / self.core.MAP_HEIGHT
            content_width = self.core.MAP_WIDTH * fixed_block_width
            if content_width <= size[0]:  # fill y
                self.BLOCK_WIDTH = fixed_block_width
            else:  # fill x
                self.BLOCK_WIDTH = size[0] / self.core.MAP_WIDTH
            self.update_window_size()
            if len(self.core.MAP) > 0:
                self.refresh_block(None)

    def update_board(self, obj):
        if self.core.GAME_OVER:
            self._show_mimes()
            return
        if self.CURRENT_SCREEN == SCREENS.GAME_WIN:
            return
        now = time.time()
        duration = int(now - self.core.GAME_START_MILLIS)
        self.status_bar.update_content(time=duration)

    def update_animation(self, obj):
        for m in self.MOTIONS:
            pass
        pass

    def update_window_size(self):
        self.WIDTH = self.BLOCK_WIDTH * self.core.MAP_WIDTH
        self.HEIGHT = self.BLOCK_WIDTH * self.core.MAP_HEIGHT

        Window.size = (self.WIDTH, self.HEIGHT + 40)
        self.size = (self.WIDTH, self.HEIGHT)

        self.status_bar.pos = (0, self.HEIGHT)
        self.status_bar.size = (self.WIDTH, 40)
        self.status_bar.update_background()
        self.status_bar.updata_widget()
        self.rebuild_dialogs()

    def load_texture(self):
        for i in range(1, 10):
            image = Image(source=resource_path("images/num_%d.png" % i))
            self.TEXTURES[i] = image.texture
        self.TEXTURES[self.core.AREA] = Image(source=resource_path("images/block_normal.png")).texture
        self.TEXTURES[self.core.FLAG] = Image(source=resource_path("images/flag_normal.png")).texture
        self.TEXTURES[self.core.MIME] = Image(source=resource_path("images/mime.png")).texture
        self.TEXTURES[self.core.EMPTY] = Image(source=resource_path("images/empty.png")).texture
        self.TEXTURES['heart'] = Image(source=resource_path("images/heart.png")).texture

        # new game button
        self.BUTTON_TEXTURES.append(Image(source=resource_path("images/btn_new_game.png")).texture)
        self.BUTTON_TEXTURES.append(Image(source=resource_path("images/btn_new_game_upon.png")).texture)
        self.BUTTON_TEXTURES.append(Image(source=resource_path("images/btn_new_game_pressed.png")).texture)

        # colorful blocks
        for color in self.COLORS:
            block = Image(source=resource_path('images/block_%s.png' % color)).texture
            self.COLORFUL_BLOCKS.append(block)

        length = len(self.COLORS) - 1
        for i in range(length):
            color = self.COLORS[i]
            flag = Image(source=resource_path('images/flag_%s.png' % color)).texture
            self.COLORFUL_FLAGS.append(flag)

    def new_game(self):
        self.CURRENT_SCREEN = SCREENS.GAME
        self.core.new_game(self.core.DIFFICULTY)
        self.canvas.remove(self.failed_dialog)
        self.canvas.remove(self.level_choose_dialog)
        self.fill_blocks()
        self.core.GAME_START_MILLIS = time.time()
        self.status_bar.update_content(button_text=self.LEVEL_TEXTS[self.core.DIFFICULTY])

        mime_left = len(self.core.MIMES) - self.core.FLAG_COUNT
        self.status_bar.update_content(mimes=mime_left)

        # self.BLOCK_WIDTH = 20       # restore to default
        self.size = (self.WIDTH, self.HEIGHT)
        Window.size = (self.WIDTH, self.HEIGHT + 40)
        self.update_window_size()

    def rebuild_dialogs(self):
        self._build_failed_dialog()
        self._build_level_choose_dialog()
        self._build_color_choose_dialog()

    def fill_blocks(self):
        self.land.clear()
        self.land.add(Color(1, 1, 1, 1))
        map_height = range(self.core.MAP_HEIGHT)
        map_width = range(self.core.MAP_WIDTH)
        size = (self.BLOCK_WIDTH, self.BLOCK_WIDTH)

        solid_texture = None
        if self.CURRENT_COLOR < len(self.COLORS) - 1:
            solid_texture = self.pick_colorful_block(self.CURRENT_COLOR)
        self.TACHED_BLOCKS.clear()
        for y in map_height:
            for x in map_width:
                pos = (x * self.BLOCK_WIDTH, y * self.BLOCK_WIDTH)
                block = Rectangle(pos=pos, size=size)
                if solid_texture:
                    block.texture = solid_texture
                else:
                    block.texture = self.pick_colorful_block(self.CURRENT_COLOR)
                block.group = 'block'
                self.land.add(block)

                # cached blocks
                idx = y * self.core.MAP_WIDTH + x
                self.TACHED_BLOCKS[idx] = block
        self.canvas.add(self.land)

    def _on_touch_down(self, instance, event):
        self.millis_on_touch_down = time.time()
        self.touch_down_pos = event.pos
        return True

    def _on_touch_up(self, instance, event):
        x = self.touch_down_pos[0]
        y = self.touch_down_pos[1]
        button = event.button
        if abs(event.pos[0] - x) > self.BLOCK_WIDTH or \
                        abs(event.pos[1] - y) > self.BLOCK_WIDTH:
            # 位移大于一个方格，取消操作
            return True

        press_time = time.time() - self.millis_on_touch_down

        # 长按
        if press_time > self.LONG_CLICK_THRESHOLD:
            if self.CURRENT_SCREEN == SCREENS.GAME:
                if button == 'middle':
                    self.do_chect(1)
        else:
            # 重定向点击事件
            if self.CURRENT_SCREEN == SCREENS.GAME:
                if self.core.GAME_OVER:
                    return
                if y < self.HEIGHT:
                    if button == 'left':
                        self.drag(x, y)
                    elif button == 'right':
                        self.place_a_flag(x, y)
                    elif button == 'middle':
                        self.detect(x, y)
                        pass
                else:
                    if self.is_item_clicked(self.status_bar.btn_change_difficulty, x, y):
                        self.choose_level()
                    elif self.is_item_clicked(self.status_bar.btn_change_color, x, y):
                        self.show_color_choose_dialog()

            elif self.CURRENT_SCREEN == SCREENS.LEVEL_CHOOSE:
                buttons = self.level_choose_dialog.get_group('level_choose')
                for i in range(len(buttons)):
                    button = buttons[i]
                    if self.is_item_clicked(button, x, y):
                        self.core.DIFFICULTY = i
                        if len(self.core.MAP) > 0:  # 开始新的游戏，而不是第一次开始
                            self.BLOCK_WIDTH = 20
                        self.new_game()

            elif self.CURRENT_SCREEN == SCREENS.GAME_WIN:
                self.canvas.remove(self.win_dialog)
                self.choose_level()

            elif self.CURRENT_SCREEN == SCREENS.GAME_OVER:
                button = self.failed_dialog.get_group('failed')[-1]
                if self.is_item_clicked(button, x, y):
                    self.new_game()

            elif self.CURRENT_SCREEN == SCREENS.COLOR_CHOOSE:
                blocks = self.color_choose_dialog.get_group('color')
                for i in range(len(blocks)):
                    block = blocks[i]
                    if self.is_item_clicked(block, x, y):
                        self.CURRENT_COLOR = i
                        self.change_color(i)
                        self.canvas.remove(self.color_choose_dialog)

        return True

    def _on_key_down(self, keycode, ascii, code, char, obj2):
        self.CHECT_CODE.append(char)
        try:
            code = self.CHECT_CODE[-6:]
            word = ''.join(code).lower()
            if word == 'xsstjm':
                self.do_chect(1)
            elif word == 'lovexm':
                self.do_chect(2)
            elif word == 'lovess':
                self.do_chect(3)
            elif word == 'anioff':
                self.USE_ANIMATION = False
            code = self.CHECT_CODE[-5:]
            word = ''.join(code)
            if word.lower() == 'anion':
                self.USE_ANIMATION = True

        except Exception as e:
            pass

    # 坐标转换为 数据映射下标
    def pos_to_index(self, x, y):
        index_x = int(x // self.BLOCK_WIDTH)
        index_y = int(y // self.BLOCK_WIDTH)
        return (index_x, index_y)

    def drag(self, x, y):
        pos_in_map = self.pos_to_index(x, y)
        idx_x = pos_in_map[0]
        idx_y = pos_in_map[1]
        # 已翻转，不可点击
        if self.core.MAP[idx_y][idx_x] > 0:
            return
        result = self.core.drag(idx_x, idx_y)
        if result is None:
            self.get_block(idx_x, idx_y).texture = self.TEXTURES[self.core.MIME]
            Clock.schedule_once(self.game_over, 1)
            pass
        else:
            if self.USE_ANIMATION:
                self.clear_animation(None)
                self.animation_layer.add(Color(1, 1, 1, 1))
            for pos in result:
                x = pos[0]
                y = pos[1]
                num = self.core.MAP[y][x]
                texture = self.TEXTURES[num]
                block = self.get_block(x, y)
                ori_texture = block.texture

                if num == self.core.FLAG:
                    texture = self.pick_colorful_flag(self.CURRENT_COLOR)
                elif self.USE_ANIMATION:
                    if ori_texture in self.COLORFUL_BLOCKS:
                        fake_block = Rectangle(pos=block.pos, size=block.size)
                        fake_block.texture = ori_texture
                        fake_block.group = 'break_block'
                        self.animation_layer.add(fake_block)
                block.texture = texture
            if self.USE_ANIMATION:
                self.play_block_animation()
                self.LAST_ANIMATION_MILLIS = time.time()

    def place_a_flag(self, x, y):
        indexs = self.pos_to_index(x, y)
        num = self.core.MAP[int(indexs[1])][int(indexs[0])]
        block = self.get_block(indexs[0], indexs[1])
        if num == self.core.FLAG:
            block.texture = self.pick_colorful_block(self.CURRENT_COLOR)
            self.core.MAP[int(indexs[1])][int(indexs[0])] = self.core.AREA
            self.core.FLAG_COUNT -= 1
        elif num == self.core.AREA:
            mime_left = len(self.core.MIMES) - self.core.FLAG_COUNT
            if mime_left > 0:
                block.texture = self.pick_colorful_flag(self.CURRENT_COLOR)
                self.core.MAP[int(indexs[1])][int(indexs[0])] = self.core.FLAG
                self.core.FLAG_COUNT += 1
                if self.core.check_state():
                    self.game_win()

        mime_left = len(self.core.MIMES) - self.core.FLAG_COUNT
        self.status_bar.update_content(mimes=mime_left)

    def clear_animation(self, obj):
        blocks = self.animation_layer.get_group('break_block')
        for block in blocks:
            Animation.cancel_all(block)
        self.animation_layer.clear()

    def get_block(self, x, y):
        index = int(y * self.core.MAP_WIDTH + x)
        return self.TACHED_BLOCKS[index]

    def choose_level(self):
        self.canvas.add(self.level_choose_dialog)
        self.CURRENT_SCREEN = SCREENS.LEVEL_CHOOSE

    def is_item_clicked(self, item, x, y):
        pos = item.pos
        size = item.size
        if x > pos[0] and x < pos[0] + size[0] and \
                        y > pos[1] and y < pos[1] + size[1]:
            return True
        return False

    def _build_failed_dialog(self):
        self.failed_dialog.clear()
        self.failed_dialog.add(Color(1, 1, 1, 0.8))
        width = self.WIDTH
        height = self.BLOCK_WIDTH * 4
        y = (self.HEIGHT - height) / 2
        border = Rectangle(size=(width, height), pos=(0, y))
        border.group = 'failed'

        text = Rectangle(size=(self.BLOCK_WIDTH * 4, self.BLOCK_WIDTH * 0.8))
        text.pos = ((width - text.size[0]) / 2, y + 2.5 * self.BLOCK_WIDTH)
        text.group = 'failed'

        button = Rectangle()
        button.pos = ((width - text.size[0]) / 2, y + 0.5 * self.BLOCK_WIDTH)
        button.size = (self.BLOCK_WIDTH * 4, self.BLOCK_WIDTH * 1.2)
        button.texture = self.BUTTON_TEXTURES[0]
        button.group = 'failed'

        label = CoreLabel(text='游戏结束!', font_size=24, font_name='simhei')
        label.color = Color(1, 0, 1, 1)
        label.refresh()
        text.texture = label.texture
        self.failed_dialog.add(border)
        self.failed_dialog.add(Color(0, 0., 0, 0.9))
        self.failed_dialog.add(text)
        self.failed_dialog.add(Color(1, 1, 1, 1))
        self.failed_dialog.add(button)

    def _build_level_choose_dialog(self):
        self.level_choose_dialog.clear()
        size = (80, 25)
        gap = 5
        x = (self.width - size[0]) / 2
        total_height = gap * 5 + size[1] * 6
        top = (self.HEIGHT + total_height - self.status_bar.height) / 2

        border = Rectangle(size=(150, self.HEIGHT))
        border.pos = ((self.WIDTH - border.size[0]) / 2, 0)
        self.level_choose_dialog.add(Color(0, 0, 0, .4))
        self.level_choose_dialog.add(border)
        self.level_choose_dialog.add(Color(1, 1, 1, 1))
        for i in range(6):
            y = top - i * 30
            btn = Rectangle(size=size, pos=(x, y))
            image = Image(source=resource_path('images/btn_level_%d.png' % (i + 1)))
            btn.texture = image.texture
            btn.group = 'level_choose'
            self.level_choose_dialog.add(btn)

    def _build_color_choose_dialog(self):
        self.color_choose_dialog.clear()
        block_size = (30, 30)
        gap = 10
        total_height = gap * 3 + block_size[1] * 4
        top = (self.HEIGHT + total_height - self.status_bar.height) / 2
        left = (self.WIDTH - block_size[1] * 3 - gap * 2) / 2
        self.level_choose_dialog.add(Color(1, 1, 1, 1))

        border = Rectangle(size=(150, self.HEIGHT))
        border.pos = ((self.WIDTH - border.size[0]) / 2, 0)
        title = Rectangle(size=(110, 30), pos=(left, top))
        label = CoreLabel(text="选择颜色:", font_size=16, size=title.size, font_name=self.FONT_NAME)
        label.refresh()
        label.color = [0, 0, 0, 1]
        title.texture = label.texture

        self.color_choose_dialog.add(Color(0, 0, 0, .4))
        self.color_choose_dialog.add(border)
        self.color_choose_dialog.add(Color(1, 1, 1, 1))
        self.color_choose_dialog.add(title)
        index = 0
        for i in range(1, 4):
            y = top - i * 40
            for x in [left + l * 40 for l in range(3)]:
                block = Rectangle(size=block_size, pos=(x, y))
                block.texture = self.COLORFUL_BLOCKS[index]
                block.group = 'color'
                self.color_choose_dialog.add(block)
                if index == len(self.COLORS) - 1:
                    break
                index += 1

    def game_win(self):
        self._GAME_PLAYED_TIMES += 1
        self._WIN_TIMES += 1
        self.CURRENT_SCREEN = SCREENS.GAME_WIN
        self.show_win_dialog()

    def game_over(self, obj):
        self._GAME_PLAYED_TIMES += 1
        self.core.GAME_OVER = True
        self.canvas.add(self.failed_dialog)
        self.CURRENT_SCREEN = SCREENS.GAME_OVER

    def _show_mimes(self):
        mimes_left = len(self.core.MIMES)
        speed = 5
        if mimes_left > 30:
            speed = 50
        if mimes_left == 0:
            return
        else:
            for i in range(speed):
                if len(self.core.MIMES) > 0:
                    mime = self.core.MIMES.pop(0)
                    y = int(mime // self.core.MAP_WIDTH)
                    x = mime % self.core.MAP_WIDTH
                    self.get_block(x, y).texture = self.TEXTURES[self.core.MIME]
                else:
                    return

    def show_win_dialog(self):
        self.win_dialog.clear()
        width = self.WIDTH
        height = self.BLOCK_WIDTH * 4
        y = (self.HEIGHT - height) / 2
        border = Rectangle(size=(width, height), pos=(0, y))
        border.group = 'dialog'

        text_win = Rectangle()
        text_win.size = (self.BLOCK_WIDTH * 3, self.BLOCK_WIDTH)
        text_win.pos = ((self.width - text_win.size[0]) / 2, border.pos[1] + 2.5 * self.BLOCK_WIDTH)
        label = CoreLabel(text='你赢了!', font_size=32, font_name=self.FONT_NAME)
        label.refresh()
        text_win.texture = label.texture

        text_detail = Rectangle()
        text_detail.size = (self.BLOCK_WIDTH * 4.5, self.BLOCK_WIDTH * 0.8)
        text_detail.pos = ((self.width - text_detail.size[0]) / 2, border.pos[1] + 1.5 * self.BLOCK_WIDTH)
        time_used = time.time() - self.core.GAME_START_MILLIS
        label = CoreLabel(text='用时: %d 秒' % time_used, font_size=30, font_name=self.FONT_NAME)
        label.refresh()
        text_detail.texture = label.texture

        text_sum = Rectangle()
        text_sum.size = (self.BLOCK_WIDTH * 8, self.BLOCK_WIDTH * 0.7)
        text_sum.pos = ((self.width - text_sum.size[0]) / 2, text_detail.pos[1] - self.BLOCK_WIDTH)
        label = CoreLabel(text='共进行%d场游戏,胜利%d场' % (self._GAME_PLAYED_TIMES, self._WIN_TIMES), font_name=self.FONT_NAME,
                          font_size=30)
        label.refresh()
        text_sum.texture = label.texture

        self.win_dialog.add(Color(1, 1, 1, 0.9))
        self.win_dialog.add(border)
        self.win_dialog.add(Color(1, 0.3, 0.3, 1))
        self.win_dialog.add(text_win)
        self.win_dialog.add(Color(0.2, 0.2, 0.2, 1))
        self.win_dialog.add(text_detail)
        self.win_dialog.add(text_sum)
        self.canvas.add(self.win_dialog)

    def show_color_choose_dialog(self):
        self.CURRENT_SCREEN = SCREENS.COLOR_CHOOSE
        self.canvas.add(self.color_choose_dialog)

    def play_block_animation(self):
        if not self.USE_ANIMATION:
            return
        blocks = self.animation_layer.get_group('break_block')
        left = self.WIDTH
        right = 0
        top = 0
        bottom = self.HEIGHT
        for block in blocks:
            x = block.pos[0]
            y = block.pos[1]
            if left > x:
                left = x
            if right < x:
                right = x
            if top < y:
                top = y
            if bottom > y:
                bottom = y

        middle_x = (left + right) / 2
        for block in blocks:
            off_x = (block.pos[0] - middle_x) / self.BLOCK_WIDTH
            off_y = (block.pos[1] - bottom) / self.BLOCK_WIDTH
            self.broken_animation(block, off_x, off_y)

    def broken_animation(self, instance, off_x, off_y):
        pos = instance.pos
        left_or_right = 1 if off_x > 0 else -1
        x = pos[0] + off_y * self.BLOCK_WIDTH * left_or_right / 2
        y = pos[1] + (off_y + abs(off_x) + random.randrange(0, 5)) * self.BLOCK_WIDTH / 3
        speedup = off_y / 10
        animation = Animation(pos=(x, y), duration=0.3 - speedup, t='in_out_quad')
        animation += Animation(pos=(x, - self.BLOCK_WIDTH * 2), duration=0.5 - speedup, t='in_out_quad')
        animation.start(instance)

    def set_animated_blocks(self, blocks):
        self.clear_animated_blocks()
        for block in blocks:
            self.add_animated_block(block)

    def add_animated_block(self, block):
        block.group = 'break_block'
        self.animation_layer.add(block)
        index = self.core.MAP_WIDTH * block.pos[1] + block.pos[0]
        self.ANIMATED_BLOCKS[index] = block

    def remove_animated_block(self, x, y):
        index = self.core.MAP_WIDTH * y + x
        block = self.ANIMATED_BLOCKS.pop(index)
        self.animation_layer.remove(block)

    def clear_animated_blocks(self):
        self.ANIMATED_BLOCKS.clear()
        self.animation_layer.clear()

    def do_chect(self, code):
        if not self.CURRENT_SCREEN == SCREENS.GAME:
            return
        if code == 1:
            for mime in self.core.MIMES:
                y = mime // self.core.MAP_WIDTH
                x = mime % self.core.MAP_WIDTH
                if self.core.MAP[y][x] == self.core.FLAG:
                    continue
                self.get_block(x, y).texture = self.TEXTURES[self.core.MIME]
            Clock.schedule_once(self.refresh_block, 1.2)
        elif code == 2:
            range_width = range(self.core.MAP_WIDTH)
            for y in range(self.core.MAP_HEIGHT):
                for x in range_width:

                    if self.core.MAP[y][x] == self.core.AREA and \
                            not self.core.is_mime(x, y):
                        block = self.get_block(x, y)
                        ori_texture = block.texture

                        if self.USE_ANIMATION:
                            fake_block = Rectangle(pos=block.pos, size=block.size)
                            fake_block.texture = ori_texture
                            fake_block.group = 'break_block'
                            self.animation_layer.add(fake_block)
                        self.core.MAP[y][x] = self.core.EMPTY
                        block.texture = self.TEXTURES[self.core.self.core.EMPTY]
            # start animation
            if self.USE_ANIMATION:
                self.play_block_animation()
                Clock.schedule_once(self.clear_animation, 2)

        elif code == 3:
            flags = 0
            mimes = len(self.core.MIMES)
            last_mime_pos = ()
            range_width = range(self.core.MAP_WIDTH)
            for y in range(self.core.MAP_HEIGHT):
                for x in range_width:
                    num = self.core.MAP[y][x]
                    if num == self.core.FLAG:
                        if not self.core.is_mime(x, y):
                            self.core.MAP[y][x] = self.core.AREA
                        else:
                            flags += 1
                    elif num == self.core.AREA:
                        if self.core.is_mime(x, y):
                            flags += 1
                            if flags == mimes - 1:
                                last_mime_pos = (x, y)
                                continue
                            self.core.MAP[y][x] = self.core.FLAG

            self.refresh_block(None)
            block = self.get_block(last_mime_pos[0], last_mime_pos[1])
            block.texture = self.TEXTURES['heart']
            self.core.FLAG_COUNT = mimes - 1
            self.status_bar.update_content(mimes=1)

    def detect(self, x, y):
        idxs = self.pos_to_index(x, y)
        x = idxs[0]
        y = idxs[1]
        if (x, y) in self.DETECTED_POSITIONS:
            return
        if self.core.MAP[y][x] == self.core.FLAG and \
                self.core.is_mime(x, y):
            self.get_block(x, y).texture = self.TEXTURES['heart']
            self.DETECTED_POSITIONS.append((x, y))
            Clock.schedule_once(self.remove_a_detected_result, 0.5)

    def remove_a_detected_result(self, obj):
        if len(self.DETECTED_POSITIONS) > 0:
            pos = self.DETECTED_POSITIONS.pop(0)
            num = self.core.MAP[pos[1]][pos[0]]
            block = self.get_block(pos[0], pos[1])
            if num == self.core.FLAG:
                block.texture = self.pick_colorful_flag(self.CURRENT_COLOR)

    def change_color(self, color_idx):
        self.CURRENT_SCREEN = SCREENS.GAME
        source_name = resource_path('images/block_%s.png' % self.COLORS[color_idx])
        self.status_bar.btn_change_color.background_normal = source_name
        for y in range(self.core.MAP_HEIGHT):
            for x in range(self.core.MAP_WIDTH):
                if self.core.MAP[y][x] == self.core.AREA:
                    block = self.pick_colorful_block(color_idx)
                    self.get_block(x, y).texture = block
                elif self.core.MAP[y][x] == self.core.FLAG:
                    block = self.pick_colorful_flag(color_idx)
                    self.get_block(x, y).texture = block

    def pick_colorful_block(self, index):
        if index < len(self.COLORS) - 1:
            return self.COLORFUL_BLOCKS[index]
        else:
            return self.COLORFUL_BLOCKS[random.randint(0, 6)]

    def pick_colorful_flag(self, index):
        if index < 7:
            return self.COLORFUL_FLAGS[index]
        else:
            return self.COLORFUL_FLAGS[random.randint(0, 6)]

    def refresh_block(self, obj):
        range_width = range(self.core.MAP_WIDTH)
        for y in range(self.core.MAP_HEIGHT):
            for x in range_width:
                num = self.core.MAP[y][x]
                block = self.get_block(x, y)
                if num == self.core.AREA:
                    block.texture = self.pick_colorful_block(self.CURRENT_COLOR)
                elif num == self.core.FLAG:
                    block.texture = self.pick_colorful_flag(self.CURRENT_COLOR)
                else:
                    block.texture = self.TEXTURES[num]
                block.size = (self.BLOCK_WIDTH, self.BLOCK_WIDTH)
                block.pos = (x * self.BLOCK_WIDTH, y * self.BLOCK_WIDTH)

    def has_saved_data(self):
        file = self.get_game_data_location()
        if file is None:
            return False
        return os.path.exists(file)

    def save_game(self, a):
        data_loc = self.get_game_data_location()
        if data_loc is None:
            return
        data = {}
        restore = len(self.core.MAP) > 0 and not self.core.GAME_OVER and \
                  not self.CURRENT_SCREEN == SCREENS.GAME_WIN and \
                  not self.CURRENT_SCREEN == SCREENS.LEVEL_CHOOSE
        data['restore'] = restore
        if restore:
            data['map'] = self.core.MAP
            data['mimes'] = self.core.MIMES
            data['flag_count'] = self.core.FLAG_COUNT
            data['difficulty'] = self.core.DIFFICULTY
            data['game_over'] = self.core.GAME_OVER
            data['time'] = time.time() - self.core.GAME_START_MILLIS
        data['game_played_times'] = self._GAME_PLAYED_TIMES
        data['win_times'] = self._WIN_TIMES

        with open(data_loc, 'wb') as f:
            pickle.dump(data, f)

    def load_game(self):
        data_loc = self.get_game_data_location()
        if data_loc is None:
            return
        self.TACHED_BLOCKS.clear()
        with open(data_loc, 'rb') as f:
            data = pickle.load(f)
            self._GAME_PLAYED_TIMES = data['game_played_times']
            self._WIN_TIMES = data['win_times']
            restore = data['restore']
            if restore:
                self.core.MAP = data['map']
                self.core.MIMES = data['mimes']
                self.core.FLAG_COUNT = data['flag_count']
                self.core.DIFFICULTY = data['difficulty']
                self.core.GAME_OVER = data['game_over']
                t = data['time']
                self.core.GAME_START_MILLIS = time.time() - t
                mime_left = len(self.core.MIMES) - self.core.FLAG_COUNT
                self.status_bar.update_content(mimes=mime_left)
                self.core.MAP_HEIGHT = len(self.core.MAP)
                if self.core.MAP_HEIGHT > 0:
                    self.core.MAP_WIDTH = len(self.core.MAP[0])

                    self.land.clear()
                    self.land.add(Color(1, 1, 1, 1))
                    texture = None
                    size = (self.BLOCK_WIDTH, self.BLOCK_WIDTH)
                    for y in range(self.core.MAP_HEIGHT):
                        for x in range(self.core.MAP_WIDTH):
                            pos = (x * self.BLOCK_WIDTH, y * self.BLOCK_WIDTH)
                            num = self.core.MAP[y][x]
                            if num == self.core.AREA:
                                texture = self.pick_colorful_block(self.CURRENT_COLOR)
                            elif num == self.core.FLAG:
                                texture = self.pick_colorful_flag(self.CURRENT_COLOR)
                            else:
                                texture = self.TEXTURES[num]
                            block = Rectangle(pos=pos, size=size)
                            block.texture = texture
                            block.group = 'block'
                            self.land.add(block)
                            self.TACHED_BLOCKS[y * self.core.MAP_WIDTH + x] = block
                    self.canvas.add(self.land)
                    with self.canvas.before:
                        Color(0.2, 0.2, 0.2, 1)
                        Rectangle(size=self.size)

                self.CURRENT_SCREEN = SCREENS.GAME
                self.update_window_size()
            else:
                self.choose_level()

    def get_game_data_location(self):
        for char in [chr(c) for c in range(ord('D'), ord('Z') + 1)]:
            disk = '%s:/' % char
            if os.path.exists(disk):
                data_file = disk + "mime_sweeper.data"
                return data_file
        return None


def resource_path(relative_path):
    """
        定义一个读取相对路径的函数
        用于打包成exe时，获取包内资源
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


MimeSweeper().run()
