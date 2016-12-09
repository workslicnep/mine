# -*- coding:utf-8 -*-
import random

class MimeCore:
    # 当前难度
    DIFFICULTY = 0
    # 不同难度 地图的大小
    DIFFICULTIES = [(10,10),(15,10),(20,15),(25,20),(30,25),(40,30)]
    # 不同难度 雷的数量
    MIME_AMOUNTS = [0.1,0.1,0.15,0.2,0.2,0.2]

    # 方块类型
    AREA = 0        # 空地
    EMPTY = 10
    MIME = -1       # 地雷
    FLAG = 11       # 旗帜

    # 地图
    MAP = []
    MIMES = []
    MAP_WIDTH = 10
    MAP_HEIGHT = 10
    FLAG_COUNT = 0

    # 上次点击位置，用于限制翻转空白区域
    LAST_CLICK_POS = None
    AUTO_FLIP_DISTANCE = 2

    LIST_TO_CHECK = []
    LIST_CHECKED = []

    GAME_START_MILLIS = 0

    # game over
    GAME_OVER = True

    # 新游戏
    def new_game(self,difficulty=0):
        self.GAME_OVER = False
        self.FLAG_COUNT = 0
        self.DIFFICULTY = difficulty
        self.LIST_CHECKED.clear()
        self.LIST_TO_CHECK.clear()
        self.load_map()
        self.lay_mimes()

    # 加载地图
    def load_map(self):
        self.MAP.clear()
        map_size = self.DIFFICULTIES[self.DIFFICULTY]
        self.MAP_WIDTH = map_size[0]
        self.MAP_HEIGHT = map_size[1]

        for i in range(self.MAP_HEIGHT):
            row = [0] * self.MAP_WIDTH
            self.MAP.append(row)

    # 埋地雷
    def lay_mimes(self):
        total_blocks = self.MAP_WIDTH * self.MAP_HEIGHT
        mime_amount = int(self.MIME_AMOUNTS[self.DIFFICULTY] * total_blocks)     # 地雷数量
        map_amount = self.MAP_WIDTH * self.MAP_HEIGHT

        # 随机生成mimes个地雷
        self.MIMES = random.sample(range(map_amount),mime_amount)

    def mimes_at(self,x,y):
        mime_count = 0
        x -= 1
        y -= 1
        range_3 = range(3)
        for h in range_3:
            yy = h + y
            for w in range_3:
                xx = w + x
                if xx < 0 or xx >= self.MAP_WIDTH or\
                    yy < 0 or yy > self.MAP_HEIGHT:
                    continue
                dot = xx + yy * self.MAP_WIDTH
                if dot in self.MIMES:
                    mime_count += 1
        return mime_count

    def is_mime(self,x,y):
        dot = x + y * self.MAP_WIDTH
        return dot in self.MIMES

    def drag(self,x,y):
        self.LAST_CLICK_POS = (x,y)
        self.LIST_CHECKED.clear()
        self.LIST_TO_CHECK.clear()

        if self.is_mime(x,y):
            self.GAME_OVER = True
            return None
        self.check_bounds(x,y)
        while(len(self.LIST_TO_CHECK) > 0):
            block = self.LIST_TO_CHECK.pop(0)
            self.check_bounds(block[0], block[1])

        return self.LIST_CHECKED


    def check_bounds(self,x,y):
        self.LIST_CHECKED.append((x, y))
        if self.is_mime(x,y):
            return
        self.MAP[y][x] = self.EMPTY
        range_3 = range(3)
        for h in range_3:
            yy = h + y - 1
            for w in range_3:
                xx = w + x - 1
                point = (xx,yy)
                if xx < 0 or xx >= self.MAP_WIDTH or \
                    yy < 0 or yy >= self.MAP_HEIGHT:
                    continue
                if self.MAP[yy][xx] == self.FLAG:
                    self.LIST_CHECKED.append(point)
                    continue
                mime_count = self.mimes_around(xx, yy)
                if mime_count > 0:
                    if not self.is_mime(xx,yy):
                        self.MAP[yy][xx] = mime_count
                        self.LIST_CHECKED.append(point)
                    continue

                if point not in self.LIST_CHECKED and \
                    point not in self.LIST_TO_CHECK:
                    if not self._check_overstep(xx,yy):
                        self.LIST_TO_CHECK.append(point)

    # 判断自动翻转空白有没有超出限制
    def _check_overstep(self,x,y):
        if self.LAST_CLICK_POS is None:
            return False
        dis_x = abs(x - self.LAST_CLICK_POS[0])
        dis_y = abs(y - self.LAST_CLICK_POS[1])
        if dis_x > self.AUTO_FLIP_DISTANCE or\
            dis_y > self.AUTO_FLIP_DISTANCE:
            return True
        return False

    # 九宫格中mine的数量
    def mimes_around(self,x,y):
        mime_count = 0
        range_3 = range(3)
        for h in range_3:
            yy = h + y - 1
            for w in range_3:
                xx = w + x - 1
                if xx < 0 or xx >= self.MAP_WIDTH or \
                    yy < 0 or yy >= self.MAP_HEIGHT:
                    continue
                if self.is_mime(xx,yy):
                    mime_count += 1
        return mime_count

    # 判断是否胜利,
    def check_state(self):
        for mime in self.MIMES:
            y = mime // self.MAP_WIDTH
            x = mime % self.MAP_WIDTH
            if not self.MAP[y][x] == self.FLAG:
                return False
        return True
