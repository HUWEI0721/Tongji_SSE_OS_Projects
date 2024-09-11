import sys
from PyQt5.QtCore import QRect, QThread, QMutex, QTimer, Qt
from PyQt5.QtWidgets import QWidget, QPushButton, QApplication, QLabel, QTextEdit, \
    QVBoxLayout, QHBoxLayout, QLCDNumber,QLineEdit
from enum import Enum
from functools import partial

# 窗口大小设置
WINDOW_SIZE = QRect(300, 300, 1100, 700)

# 全局变量定义
ELEVATOR_NUMS = 5                       # 电梯数量
FLOORS = 20                             # 电梯层数
TIME_EACH_FLOOR = 1500                  # 运行一层电梯所需时间
DOOR_OPENING_TIME = 800                 # 打开一扇门所需时间
DOOR_OPEN_TIME = 1500                   # 门打开后维持的时间

elevator_status = []                    # 每组电梯的状态
elevator_move_status = []               # 每台电梯当前的扫描运行状态
elevator_now_floor = []                 # 每台电梯的当前楼层
up_task_remains = []                    # 电梯在向上扫描的过程中，还需要处理的任务（二维数组），每个一维数组表示一个电梯的情况
down_task_remains = []                  # 电梯在向下扫描的过程中，还需要处理的任务（二维数组），每个一维数组表示一个电梯的情况
open_button_clicked = []                # 每台电梯内部的开门键是否被按（True/False）
close_button_clicked = []               # 每台电梯内部的关门键是否被按（True/False）
door_open_status = []                   # 每台电梯开门的进度条 范围为0-1的浮点数
door_each_elevator = []                 # 每个电梯的门
outer_button_task = []                  # 外部按钮产生的事件
mutex = QMutex()                        # mutex互斥锁

# 电梯的扫描移动状态
class MOVING_STATUS(Enum):
    up = 1                              # 电梯在向上扫描的状态中
    down = -1                           # 电梯在向下扫描的状态中

# 电梯状态
class ELEVATOR_STATUS(Enum):
    normal = 0                          # 表示电梯状态是正常的
    break_down = 1                      # 表示电梯此时状态是故障的状态
    opening_door = 2                    # 表示电梯正在开门
    open_door = 3                       # 表示电梯门已经打开
    closing_door = 4                    # 表示电梯正在关门
    moving_up = 5                       # 表示电梯正在上行
    moving_down = 6                     # 表示电梯正在下行

# 外部按钮可能处在的状态
class OUTER_BUTTON_STATUS(Enum):
    unassigned = 1                      # 表示该按钮没有被按下
    waiting = 2                         # 表示该按钮已经被按下，正在等待被处理
    finished = 3                        # 表示该按钮的任务已经被完成

# 外部按钮按下产生的任务描述
class OUTER_BUTTON_GENERATE_TASK:
    for i in range(ELEVATOR_NUMS):
        elevator_status.append(ELEVATOR_STATUS.normal)  # 默认正常
        elevator_now_floor.append(1)  # 默认在1楼
        up_task_remains.append([])  # 二维数组
        down_task_remains.append([])  # 二维数组
        close_button_clicked.append(False)  # 默认关门键没按
        open_button_clicked.append(False)  # 默认关门键没按
        elevator_move_status.append(MOVING_STATUS.up)  # 默认向上
        door_open_status.append(0.0)  # 默认门没开 即进度条停在0.0

    def __init__(self, target, move_state, state=OUTER_BUTTON_STATUS.unassigned):
        self.target = target            # 目标楼层
        self.move_state = move_state    # 需要的电梯运行方向
        self.state = state              # 是否完成（默认未完成）

# 处理电梯的操作
class Elevator(QThread):
    def __init__(self, elevator_id):
        super().__init__()                  # 父类构造函数
        self.elevator_id = elevator_id      # 电梯编号
        self.rest_time = 10                 # 时间间隔

    # 移动一层楼
    def update_elevator_status(self, move_state):
        if move_state == MOVING_STATUS.up:
            elevator_status[self.elevator_id] = ELEVATOR_STATUS.moving_up
        elif move_state == MOVING_STATUS.down:
            elevator_status[self.elevator_id] = ELEVATOR_STATUS.moving_down

    def check_for_faults(self, move_state):
        slept_time = 0
        while slept_time != TIME_EACH_FLOOR:
            mutex.unlock()
            self.msleep(self.rest_time)
            slept_time += self.rest_time
            mutex.lock()
            if elevator_status[self.elevator_id] == ELEVATOR_STATUS.break_down:
                self.handle_fault()
                return False
        return True

    def update_current_floor(self, move_state):
        if move_state == MOVING_STATUS.up:
            elevator_now_floor[self.elevator_id] += 1
        elif move_state == MOVING_STATUS.down:
            elevator_now_floor[self.elevator_id] -= 1
        elevator_status[self.elevator_id] = ELEVATOR_STATUS.normal

    def move_one_floor(self, move_state):
        self.update_elevator_status(move_state)
        if not self.check_for_faults(move_state):
            return
        self.update_current_floor(move_state)
        if elevator_status[self.elevator_id] == ELEVATOR_STATUS.break_down:
            self.handle_fault()

    # 一次门的操作 包括开门和关门
    def door_operation(self):
        opening_time = 0.0  # 记录门打开所需的累积时间
        open_time = 0.0     # 记录门保持开启的累积时间
        elevator_status[self.elevator_id] = ELEVATOR_STATUS.opening_door  # 初始设置为门正在打开

        while True:
            # 检查电梯是否处于故障状态
            if elevator_status[self.elevator_id] == ELEVATOR_STATUS.break_down:
                self.handle_fault()  # 处理故障
                break

            # 用户请求开门
            if open_button_clicked[self.elevator_id]:
                # 如果门正在关，重置为开门状态
                if elevator_status[self.elevator_id] == ELEVATOR_STATUS.closing_door:
                    elevator_status[self.elevator_id] = ELEVATOR_STATUS.opening_door

                # 如果门已经是开启状态，重置保持开启的时间
                if elevator_status[self.elevator_id] == ELEVATOR_STATUS.open_door:
                    open_time = 0

                # 重置开门按钮状态
                open_button_clicked[self.elevator_id] = False

            # 用户请求关门
            if close_button_clicked[self.elevator_id]:
                elevator_status[self.elevator_id] = ELEVATOR_STATUS.closing_door  # 设置为门正在关闭
                open_time = 0  # 重置门开启时间

                # 重置关门按钮状态
                close_button_clicked[self.elevator_id] = False

            # 门正在打开的逻辑处理
            if elevator_status[self.elevator_id] == ELEVATOR_STATUS.opening_door:
                mutex.unlock()  # 允许其他线程运行
                self.msleep(self.rest_time)  # 等待一个时间段
                mutex.lock()  # 重新锁定
                opening_time += self.rest_time  # 累积增加开门时间
                door_open_status[self.elevator_id] = opening_time / DOOR_OPENING_TIME  # 更新门的打开进度

                # 如果达到了完全开门的时间
                if opening_time >= DOOR_OPENING_TIME:
                    elevator_status[self.elevator_id] = ELEVATOR_STATUS.open_door  # 设置状态为门已开

            # 门已经完全开启的处理
            elif elevator_status[self.elevator_id] == ELEVATOR_STATUS.open_door:
                mutex.unlock()
                self.msleep(self.rest_time)
                mutex.lock()
                open_time += self.rest_time  # 累积门开启时间
                if open_time >= DOOR_OPEN_TIME:
                    elevator_status[self.elevator_id] = ELEVATOR_STATUS.closing_door  # 时间到，开始关闭门

            # 门正在关闭的逻辑处理
            elif elevator_status[self.elevator_id] == ELEVATOR_STATUS.closing_door:
                mutex.unlock()
                self.msleep(self.rest_time)
                mutex.lock()
                opening_time -= self.rest_time  # 减少开门时间
                door_open_status[self.elevator_id] = opening_time / DOOR_OPENING_TIME  # 更新门的关闭进度

                # 如果门完全关闭
                if opening_time <= 0:
                    elevator_status[self.elevator_id] = ELEVATOR_STATUS.normal  # 设置电梯状态为正常
                    break  # 退出循环，操作结束

    # 当故障发生时 清除原先的所有任务
    def handle_fault(self):
        # 设置电梯状态为故障状态
        elevator_status[self.elevator_id] = ELEVATOR_STATUS.break_down
        # 初始化门的开启状态为0，表示门完全关闭
        door_open_status[self.elevator_id] = 0.0
        # 重置开门按钮状态，防止在故障处理期间误操作
        open_button_clicked[self.elevator_id] = False
        # 重置关门按钮状态，同样防止误操作
        close_button_clicked[self.elevator_id] = False
        # 再次确认设置电梯状态为故障，以确保处理逻辑的一致性
        elevator_status[self.elevator_id] = ELEVATOR_STATUS.break_down
        # 遍历所有外部按钮任务
        for outer_task in outer_button_task:
            # 检查任务是否处于等待状态
            if outer_task.state == OUTER_BUTTON_STATUS.waiting:
                # 如果任务目标楼层在上行或下行任务列表中，将其状态设置为未分配
                if outer_task.target in up_task_remains[self.elevator_id] or outer_task.target in down_task_remains[self.elevator_id]:
                    outer_task.state = OUTER_BUTTON_STATUS.unassigned  # 使得这些任务可以被重新分配
        # 清空当前电梯的上行任务列表
        up_task_remains[self.elevator_id] = []
        # 清空当前电梯的下行任务列表
        down_task_remains[self.elevator_id] = []

    def run(self):
        while True:
            mutex.lock()  # 锁定互斥量以保证线程安全
            # 检查电梯是否处于故障状态
            if elevator_status[self.elevator_id] == ELEVATOR_STATUS.break_down:
                self.handle_fault()  # 处理故障
                mutex.unlock()  # 解锁互斥量后继续循环
                continue

            # 处理向上移动状态
            if elevator_move_status[self.elevator_id] == MOVING_STATUS.up:
                # 检查是否还有未完成的上行任务
                if up_task_remains[self.elevator_id]:
                    next_floor = up_task_remains[self.elevator_id][0]
                    # 到达目标楼层
                    if next_floor == elevator_now_floor[self.elevator_id]:
                        self.door_operation()  # 执行开关门操作
                        up_task_remains[self.elevator_id].pop(0)  # 完成任务后从列表中移除
                        # 更新所有外部任务状态
                        for outer_task in outer_button_task:
                            if outer_task.target == elevator_now_floor[self.elevator_id]:
                                outer_task.state = OUTER_BUTTON_STATUS.finished
                    # 如果未到达目标楼层，向上移动一层
                    elif next_floor > elevator_now_floor[self.elevator_id]:
                        self.move_one_floor(MOVING_STATUS.up)

                # 如果没有上行任务但有下行任务，更改移动状态为下行
                elif not up_task_remains[self.elevator_id] and down_task_remains[self.elevator_id]:
                    elevator_move_status[self.elevator_id] = MOVING_STATUS.down

            # 处理向下移动状态
            elif elevator_move_status[self.elevator_id] == MOVING_STATUS.down:
                if down_task_remains[self.elevator_id]:
                    next_floor = down_task_remains[self.elevator_id][0]
                    # 到达目标楼层
                    if next_floor == elevator_now_floor[self.elevator_id]:
                        self.door_operation()  # 执行开关门操作
                        down_task_remains[self.elevator_id].pop(0)  # 完成任务后从列表中移除
                        # 更新所有外部任务状态
                        for outer_task in outer_button_task:
                            if outer_task.target == elevator_now_floor[self.elevator_id]:
                                outer_task.state = OUTER_BUTTON_STATUS.finished
                    # 如果未到达目标楼层，向下移动一层
                    elif next_floor < elevator_now_floor[self.elevator_id]:
                        self.move_one_floor(MOVING_STATUS.down)

                # 如果没有下行任务但有上行任务，更改移动状态为上行
                elif not down_task_remains[self.elevator_id] and up_task_remains[self.elevator_id]:
                    elevator_move_status[self.elevator_id] = MOVING_STATUS.up

            mutex.unlock()  # 解锁互斥量，允许其他线程运行

# controller用于处理外面按钮产生的任务，并选择合适的相应的电梯，将任务添加到对应电梯的任务列表中
class OuterTaskController(QThread):
    def __init__(self):
        super().__init__()  # 初始化父类 QThread

    def run(self):
        while True:
            mutex.lock()
            self.assign_tasks()
            self.cleanup_finished_tasks()
            mutex.unlock()

    def assign_tasks(self):
        global outer_button_task
        for outer_task in outer_button_task:
            if outer_task.state == OUTER_BUTTON_STATUS.unassigned:
                target_id = self.find_closest_elevator(outer_task)
                if target_id != -1:
                    self.assign_task_to_elevator(outer_task, target_id)

    def find_closest_elevator(self, outer_task):
        min_distance = FLOORS + 1
        target_id = -1
        for i in range(ELEVATOR_NUMS):
            if elevator_status[i] == ELEVATOR_STATUS.break_down:
                continue
            distance = self.calculate_distance(i, outer_task)
            if distance < min_distance:
                min_distance = distance
                target_id = i
        return target_id

    def calculate_distance(self, elevator_id, outer_task):
        origin = elevator_now_floor[elevator_id] + (1 if elevator_status[elevator_id] == ELEVATOR_STATUS.moving_up else -1)
        targets = up_task_remains[elevator_id] if elevator_move_status[elevator_id] == MOVING_STATUS.up else down_task_remains[elevator_id]
        if not targets:
            return abs(origin - outer_task.target)
        if elevator_move_status[elevator_id] == outer_task.move_state and \
                ((outer_task.move_state == MOVING_STATUS.up and outer_task.target >= origin) or
                 (outer_task.move_state == MOVING_STATUS.down and outer_task.target <= origin)):
            return abs(origin - outer_task.target)
        return abs(origin - targets[-1]) + abs(outer_task.target - targets[-1])

    def assign_task_to_elevator(self, outer_task, elevator_id):
        if elevator_now_floor[elevator_id] == outer_task.target:
            self.append_task(elevator_id, outer_task)
        elif elevator_now_floor[elevator_id] < outer_task.target:
            up_task_remains[elevator_id].append(outer_task.target)
            up_task_remains[elevator_id].sort()
        elif elevator_now_floor[elevator_id] > outer_task.target:
            down_task_remains[elevator_id].append(outer_task.target)
            down_task_remains[elevator_id].sort(reverse=True)
        outer_task.state = OUTER_BUTTON_STATUS.waiting

    def append_task(self, elevator_id, outer_task):
        if outer_task.move_state == MOVING_STATUS.up:
            up_task_remains[elevator_id].append(outer_task.target)
            up_task_remains[elevator_id].sort()
        else:
            down_task_remains[elevator_id].append(outer_task.target)
            down_task_remains[elevator_id].sort(reverse=True)

    def cleanup_finished_tasks(self):
        global outer_button_task
        outer_button_task = [task for task in outer_button_task if task.state != OUTER_BUTTON_STATUS.finished]

# 可视化界面
class UI_MainWindow(QWidget):
    def __init__(self):
        super().__init__()  # 调用父类的构造函数
        self.output = None
        # 初始化各类按钮和显示设备
        self.__floor_displayers = []  # 电梯上方的楼层显示屏
        self.__inner_num_buttons = []  # 电梯内部的楼层按钮
        self.__inner_open_buttons = []  # 电梯内部的开门按钮
        self.__inner_close_buttons = []  # 电梯内部的关门按钮
        self.__outer_up_buttons = []  # 楼层外的上行按钮
        self.__outer_down_buttons = []  # 楼层外的下行按钮
        self.__inner_fault_buttons = []  # 电梯内部的故障按钮
        self.timer = QTimer()  # 主定时器，用于UI更新
        self.door_timer = []  # 门的计时器列表
        self.setup_ui()  # 初始化UI界面

    # 设置UI
    def setup_ui(self):
        self.setWindowTitle("Elevator scheduling system designed by Hu Junwei 2153393 ")
        self.setGeometry(WINDOW_SIZE)

        h1 = QHBoxLayout()
        self.setLayout(h1)
        v1 = QVBoxLayout()
        h1.addLayout(v1)
        title1 = QLabel("电梯总控台")
        title1.setStyleSheet("font-size:40px;""font-weight:bold;")
        v1.addWidget(title1)
        v1.setAlignment(title1, Qt.AlignHCenter)
        # 接收用户输入的产生任务的数量
        instruction1 = QLabel("请输入随机产生的电梯任务数量:")
        v1.addWidget(instruction1)
        self.generate_num_edit = QLineEdit()
        self.generate_num_edit.setText("0")
        self.generate_num_edit.setStyleSheet("font-size:40px;""font-weight:bold;")
        v1.addWidget(self.generate_num_edit)
        button = QPushButton()
        button.setText("产生随机任务")
        button.setStyleSheet("background-color :rgb(148, 0, 211);""border-style: solid;"
                             "border-width: 20px;"
                             "border-color:  rgb(148, 0, 211);"
                             "border-radius:20px;"
                             "color:white;")
        button.clicked.connect(self.__generate_tasks)
        v1.addWidget(button)

        # 输出电梯信息
        self.output = QTextEdit()
        self.output.setText("电梯运行信息如下所示：\n")
        v1.addWidget(self.output)
        h2 = QHBoxLayout()
        h1.addLayout(h2)

        # 对每一个电梯都进行相同的设置
        for i in range(ELEVATOR_NUMS):
            v2 = QVBoxLayout()  # 竖直布局
            h2.addLayout(v2)

            # 电梯上方的LCD显示屏
            floor_display = QLCDNumber()  # 定义了一个LCD显示屏，用来显示电梯当前所在的楼层数
            # 将显示屏的位数设置为 2
            floor_display.setNumDigits(2)
            # 将段的样式设置为 Flat，使数字居中显示
            floor_display.setSegmentStyle(QLCDNumber.Flat)
            # 设置样式表，将数字颜色设为红色
            floor_display.setStyleSheet("color: rgb(255, 0, 0);")
            floor_display.setFixedSize(100, 50)  # LCD显示屏的大小
            self.__floor_displayers.append(floor_display)
            v2.addWidget(floor_display)  # 将该LCD添加到v2布局中

            # 添加文字提示
            Text = QLabel("电梯" + str(i + 1) + "内部按钮", self)
            v2.addWidget(Text)
            v2.addStretch()

            # 故障按钮
            fault_button = QPushButton("故障")
            fault_button.setFixedSize(120, 40)
            fault_button.clicked.connect(partial(self.__inner_fault_button_clicked, i))
            self.__inner_fault_buttons.append(fault_button)
            v2.addWidget(fault_button)

            # 设置每一个电梯的内部按钮
            self.__inner_num_buttons.append([])
            elevater_button_layout = QHBoxLayout()  # 用来水平的排列每排按钮
            # 创建电梯按钮
            button_group1 = QVBoxLayout()  # 前10层按钮
            for j in range(1, int(FLOORS / 2 + 1)):
                button = QPushButton(str(int(FLOORS / 2 + 1 - j)))
                button.setFixedSize(35, 35)

                # 绑定点击每一个楼层的按钮后的事件
                button.clicked.connect(partial(self.__inner_num_button_clicked, i, int(FLOORS / 2 + 1 - j)))
                button.setStyleSheet("background-color : rgb(255,255,255);""border-style: solid;"
                                     "border-width: 2px;"
                                     "border-color:  rgb(165,93,81);"
                                     "border-radius:10px;"
                                     "color:black;")
                self.__inner_num_buttons[i].append(button)
                button_group1.addWidget(button)
            # 增大元素之间的竖直方向距离
            button_group1.setSpacing(10)

            # 开门按钮
            open_button = QPushButton("开")
            open_button.setFixedSize(35, 35)
            open_button.clicked.connect(partial(self.__inner_open_button_clicked, i))
            self.__inner_open_buttons.append(open_button)
            open_button.setStyleSheet("background-color :rgb(237,220,195);""border-style: solid;"
                                      "border-width: 2px;"
                                      "border-color: rgb(192, 192, 192);"
                                      "border-radius:10px;"
                                      "color:black;")
            button_group1.addWidget(open_button)

            button_group2 = QVBoxLayout()  # 后10层按钮
            for j in range(1, int(FLOORS / 2 + 1)):
                button = QPushButton(str(FLOORS + 1 - j))
                button.setFixedSize(35, 35)

                # 绑定点击每一个楼层的按钮后的事件
                button.clicked.connect(partial(self.__inner_num_button_clicked, i, FLOORS + 1 - j))
                button.setStyleSheet("background-color : rgb(255,255,255);""border-style: solid;"
                                     "border-width: 2px;"
                                     "border-color:  rgb(165,93,81);"
                                     "border-radius:10px;"
                                     "color:black;")
                self.__inner_num_buttons[i].append(button)
                button_group2.addWidget(button)
            button_group2.setSpacing(10)

            # 关门按钮
            close_button = QPushButton("关")
            close_button.setFixedSize(35, 35)
            close_button.clicked.connect(partial(self.__inner_close_button_clicked, i))
            close_button.setStyleSheet("background-color :rgb(237,220,195);""border-style: solid;"
                                       "border-width: 2px;"
                                       "border-color: rgb(192, 192, 192);"
                                       "border-radius:10px;"
                                       "color:black;")
            self.__inner_close_buttons.append(close_button)
            button_group2.addWidget(close_button)

            # 将 button_group1 添加到 elevater_button_layout 中
            button_group1_widget = QWidget()
            button_group1_widget.setLayout(button_group1)  # 嵌套一下 QVBoxLayout
            elevater_button_layout.addWidget(button_group1_widget)
            # 将 button_group1 添加到 elevater_button_layout 中
            button_group2_widget = QWidget()
            button_group2_widget.setLayout(button_group2)  # 嵌套一下 QVBoxLayout
            elevater_button_layout.addWidget(button_group2_widget)

            elevater_button_layout_widget = QWidget()
            elevater_button_layout_widget.setLayout(elevater_button_layout)  # 嵌套一下 QHBoxLayout
            v2.addWidget(elevater_button_layout_widget)
            v2.addStretch()
            # 接下来给v2添加门
            door = []
            # 创建四个充当门的按钮的水平布局
            hbox1 = QHBoxLayout()
            for d in range(4):
                DoorTimer = QTimer()
                self.door_timer.append(DoorTimer)
                button = QPushButton('', self)
                button.setFixedSize(20, 20)
                door.append(button)
                hbox1.addWidget(button)
            door[0].setStyleSheet('background-color: transparent;')
            door[1].setStyleSheet('background-color: black;')
            door[2].setStyleSheet('background-color: black;')
            door[3].setStyleSheet('background-color: transparent;')
            door_each_elevator.append(door)  # 将这扇门添加进Doors中
            hbox1_widget = QWidget()
            hbox1_widget.setLayout(hbox1)
            v2.addWidget(hbox1_widget)

            # 添加文字提示
            Text1 = QLabel("电梯" + str(i + 1) + "的门", self)
            v2.addWidget(Text1)
            # v2.addStretch()

            v2.addStretch()
            # 设置布局中的组件水平居中
            v2.setAlignment(floor_display, Qt.AlignHCenter)
            v2.setAlignment(fault_button, Qt.AlignHCenter)
            v2.setAlignment(elevater_button_layout_widget, Qt.AlignHCenter)
            v2.setAlignment(hbox1_widget, Qt.AlignHCenter)
            v2.setAlignment(Text, Qt.AlignHCenter)
            v2.setAlignment(Text1, Qt.AlignHCenter)

        # 上下按钮
        v3 = QVBoxLayout()  # 创建一个垂直布局
        h1.addLayout(v3)
        # 标题
        title_outer = QLabel("外侧按钮")
        v3.addWidget(title_outer)
        v3.setAlignment(title_outer, Qt.AlignHCenter)

        for i in range(FLOORS):  # 对于每一层楼
            h4 = QHBoxLayout()  # 创建一个水平布局
            v3.addLayout(h4)
            label = QLabel(str(FLOORS - i))
            h4.addWidget(label)
            if i != 0:
                # 给2楼到顶楼放置上行按钮
                up_button = QPushButton("▲")
                up_button.setFixedSize(30, 30)
                up_button.clicked.connect(
                    partial(self.__outer_direction_button_clicked, FLOORS - i, MOVING_STATUS.up))
                self.__outer_up_buttons.append(up_button)  # 从顶楼往下一楼开始..
                h4.addWidget(up_button)

            if i != FLOORS - 1:
                # 给1楼到顶楼往下一楼放置下行按钮
                down_button = QPushButton("▼")
                down_button.setFixedSize(30, 30)
                down_button.clicked.connect(
                    partial(self.__outer_direction_button_clicked, FLOORS - i, MOVING_STATUS.down))
                self.__outer_down_buttons.append(down_button)  # 从顶楼开始..到2楼
                h4.addWidget(down_button)

        # 设置定时
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.update)
        self.timer.start()

        self.show()


    # 开门
    def open_the_door(self, elevator_id, choice):
        # print(door_each_elevator)
        door_each_elevator[elevator_id][0].setStyleSheet('background-color: gray;')
        door_each_elevator[elevator_id][1].setStyleSheet('background-color: black;')
        door_each_elevator[elevator_id][2].setStyleSheet('background-color: black;')
        door_each_elevator[elevator_id][3].setStyleSheet('background-color: gray;')
        door_each_elevator[elevator_id][1].hide()
        door_each_elevator[elevator_id][2].setFixedSize(20, 20)

        if choice:
            self.door_timer[elevator_id].setInterval(4000)
            self.door_timer[elevator_id].timeout.connect(lambda: self.close_1s(elevator_id))
            self.door_timer[elevator_id].start()
    # 关门
    def close_the_door(self, elevator_id):
        # print(door_each_elevator)
        door_each_elevator[elevator_id][0].setStyleSheet('background-color: transparent;')
        door_each_elevator[elevator_id][1].setStyleSheet('background-color: black;')
        door_each_elevator[elevator_id][2].setStyleSheet('background-color: black;')
        door_each_elevator[elevator_id][3].setStyleSheet('background-color: transparent;')
        door_each_elevator[elevator_id][1].show()
        door_each_elevator[elevator_id][2].setFixedSize(20, 20)

    # 产生随机任务
    def __generate_tasks(self):
        import random
        for i in range(int(self.generate_num_edit.text())):
            if random.randint(0, 100) < 50:  # 50% 产生外部任务
                rand = random.randint(1, FLOORS)
                if rand == 1:  # 1楼只能向上
                    self.__outer_direction_button_clicked(1, MOVING_STATUS.up)
                elif rand == FLOORS:  # 顶楼只能向下
                    self.__outer_direction_button_clicked(rand, MOVING_STATUS.down)
                else:  # 其余则随机指派方向
                    self.__outer_direction_button_clicked(rand,
                                                          random.choice([MOVING_STATUS.up, MOVING_STATUS.down]))
            else:  # 产生内部任务
                self.__inner_num_button_clicked(random.randint(0, ELEVATOR_NUMS - 1), random.randint(1, FLOORS))

    # 处理指定电梯的开门请求
    def __inner_open_button_clicked(self, elevator_id):
        mutex.lock()
        # 电梯故障
        if elevator_status[elevator_id] == ELEVATOR_STATUS.break_down:
            self.output.append(str(elevator_id) + "号电梯出现故障 正在维修!")
            mutex.unlock()
            return
        # 电梯正在关门或者正在开门
        if elevator_status[elevator_id] == ELEVATOR_STATUS.closing_door or elevator_status[
            elevator_id] == ELEVATOR_STATUS.open_door:
            open_button_clicked[elevator_id] = True
            close_button_clicked[elevator_id] = False
        mutex.unlock()
        # 开门按钮

        self.__inner_open_buttons[elevator_id].setStyleSheet("background-color : rgb(192, 192, 192)")
        self.output.append(str(elevator_id) + "电梯开门!")
        # 调用开门函数
        self.open_the_door(elevator_id, 1)

    def close_1s(self, elevator_id):
        print(999)
        # 调用关门函数
        self.close_the_door(elevator_id)
        # 关闭定时器
        self.door_timer[elevator_id] = self.sender()  # 获取信号发送者
        self.door_timer[elevator_id].stop()

    # 处理电梯关门
    def __inner_close_button_clicked(self, elevator_id):
        mutex.lock()
        if elevator_status[elevator_id] == ELEVATOR_STATUS.break_down:
            self.output.append(str(elevator_id) + "号电梯出现故障 正在维修!")
            mutex.unlock()
            return

        if elevator_status[elevator_id] == ELEVATOR_STATUS.opening_door or elevator_status[
            elevator_id] == ELEVATOR_STATUS.open_door:
            close_button_clicked[elevator_id] = True
            open_button_clicked[elevator_id] = False
        mutex.unlock()
        # 关门按钮
        self.__inner_close_buttons[elevator_id].setStyleSheet("background-color : rgb(192, 192, 192)")
        self.output.append(str(elevator_id) + "电梯关门!")
        self.close_the_door(elevator_id)

    # 处理电梯故障
    def __inner_fault_button_clicked(self, elevator_id):
        mutex.lock()
        # 如果电梯本来没有故障，那就设置成故障
        if elevator_status[elevator_id] != ELEVATOR_STATUS.break_down:
            elevator_status[elevator_id] = ELEVATOR_STATUS.break_down
            mutex.unlock()
            # 将电梯的状态设置为损坏之后，改变其样式
            self.__inner_fault_buttons[elevator_id].setStyleSheet("background-color : gray;")
            for button in self.__inner_num_buttons[elevator_id]:
                button.setStyleSheet("background-color :gray;""border-radius:10px;")
            self.__inner_open_buttons[elevator_id].setStyleSheet("background-color : gray;")
            self.__inner_close_buttons[elevator_id].setStyleSheet("background-color : gray;")

            self.output.append(str(elevator_id) + "电梯故障!")
        # 如果电梯本来就有故障，则再点一下故障就会消失
        else:
            elevator_status[elevator_id] = ELEVATOR_STATUS.normal
            mutex.unlock()

            self.__inner_fault_buttons[elevator_id].setStyleSheet("background-color : None")
            for button in self.__inner_num_buttons[elevator_id]:
                button.setStyleSheet("background-color : rgb(255,255,255);""border-style: solid;"
                                     "border-width: 2px;"
                                     "border-color:  rgb(165,93,81);"
                                     "border-radius:10px;"
                                     "color:black;")
            self.__inner_open_buttons[elevator_id].setStyleSheet("background-color : None;")
            self.__inner_close_buttons[elevator_id].setStyleSheet("background-color : None;")
            self.output.append(str(elevator_id) + "电梯正常!")

    # 如果按的是电梯内部的数字按钮，则执行下面的函数进行处理
    def __inner_num_button_clicked(self, elevator_id, floor):
        mutex.lock()
        # 如果电梯出现故障
        if elevator_status[elevator_id] == ELEVATOR_STATUS.break_down:
            self.output.append(str(elevator_id) + "号电梯出现故障 正在维修!")
            mutex.unlock()
            return

        # 相同楼层不处理
        if floor == elevator_now_floor[elevator_id]:
            mutex.unlock()
            return

        if elevator_status[elevator_id] != ELEVATOR_STATUS.break_down:
            if floor > elevator_now_floor[elevator_id] and floor not in up_task_remains[elevator_id]:
                up_task_remains[elevator_id].append(floor)  # 将该楼添加到上行的目标楼层中
                up_task_remains[elevator_id].sort()  # 按照从小到大的顺序排序
            elif floor < elevator_now_floor[elevator_id] and floor not in down_task_remains[elevator_id]:
                down_task_remains[elevator_id].append(floor)
                down_task_remains[elevator_id].sort(reverse=True)  # 降序排序

            mutex.unlock()
            index = 0
            if floor <= FLOORS / 2:
                index = int(FLOORS / 2 - floor)
            else:
                index = int(30 - floor)
            # 将当前楼层按钮的颜色改变
            self.__inner_num_buttons[elevator_id][index].setStyleSheet(
                "background-color : rgb(192, 192, 192);""border-radius:10px;")
            self.output.append(str(elevator_id) + "号电梯" + "用户需要去" + str(floor) + "楼")

    # 处理电梯外部每层楼的按钮点击事件
    def __outer_direction_button_clicked(self, floor, move_state):
        mutex.lock()
        # 排除故障电梯
        # 先假定所有的电梯都是故障的
        all_fault_flag = True
        for state in elevator_status:
            # 然后遍历所有的电梯的状态，只要有一个电梯的状态是正常的，就让all_fault_flag变成False
            if state != ELEVATOR_STATUS.break_down:
                all_fault_flag = False

        if all_fault_flag:
            self.output.append("所有电梯均已故障！")
            mutex.unlock()
            return

        task = OUTER_BUTTON_GENERATE_TASK(floor, move_state)

        if task not in outer_button_task:
            outer_button_task.append(task)

            if move_state == MOVING_STATUS.up:
                self.__outer_up_buttons[FLOORS - floor - 1].setStyleSheet("background-color : yellow")
                self.output.append(str(floor) + "楼的用户有上楼的需求～")

            elif elevator_move_status == MOVING_STATUS.down:
                self.__outer_down_buttons[FLOORS - floor].setStyleSheet("background-color : yellow")
                self.output.append(str(floor) + "楼的用户下楼的需求～")

        mutex.unlock()

    # 实时更新界面
    def update(self):
        mutex.lock()
        for i in range(ELEVATOR_NUMS):
            # 实时更新楼层
            if elevator_status[i] == ELEVATOR_STATUS.moving_up:
                self.__floor_displayers[i].display(str(elevator_now_floor[i]))
                self.close_the_door(i)
            elif elevator_status[i] == ELEVATOR_STATUS.moving_down:
                self.__floor_displayers[i].display(str(elevator_now_floor[i]))
                self.close_the_door(i)
            else:
                self.__floor_displayers[i].display(elevator_now_floor[i])

            # 实时更新开关门按钮
            if not open_button_clicked[i] and not elevator_status[i] == ELEVATOR_STATUS.break_down:
                self.__inner_open_buttons[i].setStyleSheet(
                    "background-color :rgb(237,220,195);""border-style: solid;"
                    "border-width: 2px;"
                    "border-color: rgb(192, 192, 192);"
                    "border-radius:10px;"
                    "color:black;")

            if not close_button_clicked[i] and not elevator_status[i] == ELEVATOR_STATUS.break_down:
                self.__inner_close_buttons[i].setStyleSheet(
                    "background-color :rgb(237,220,195);""border-style: solid;"
                    "border-width: 2px;"
                    "border-color: rgb(192, 192, 192);"
                    "border-radius:10px;"
                    "color:black;")

            # 对内部的按钮，如果在开门或关门状态的话，则设进度条
            if elevator_status[i] in [ELEVATOR_STATUS.opening_door, ELEVATOR_STATUS.open_door,
                                      ELEVATOR_STATUS.closing_door]:
                index = 0
                if elevator_now_floor[i] <= FLOORS / 2:
                    index = int(FLOORS / 2 - elevator_now_floor[i])
                else:
                    index = int(30 - elevator_now_floor[i])
                self.__inner_num_buttons[i][index].setStyleSheet(
                    "background-color : rgb(255,255,255);""border-style: solid;"
                    "border-width: 2px;"
                    "border-color:  rgb(165,93,81);"
                    "border-radius:10px;"
                    "color:black;")
                # self.open_the_door(i)
            # 如果是正在开门，需要调用开门的函数
            if elevator_status[i] == ELEVATOR_STATUS.opening_door:
                self.open_the_door(i, 0)
            else:
                self.close_the_door(i)

        mutex.unlock()
        # 对外部来说，遍历任务，找出未完成的设为红色，其他设为默认none
        for button in self.__outer_up_buttons:
            button.setStyleSheet("background-color : None")

        for button in self.__outer_down_buttons:
            button.setStyleSheet("background-color : None")

        mutex.lock()
        # 这是一组对于外部上下楼按钮事件的处理
        for outer_task in outer_button_task:
            # 如果外部的事件还没有被完全处理好，则将对应的按钮的背景变成红色的
            if outer_task.state != OUTER_BUTTON_STATUS.finished:
                if outer_task.move_state == MOVING_STATUS.up:  # 注意index
                    self.__outer_up_buttons[FLOORS - outer_task.target - 1].setStyleSheet(
                        "background-color : rgb(192, 192, 192);")
                elif outer_task.move_state == MOVING_STATUS.down:
                    self.__outer_down_buttons[FLOORS - outer_task.target].setStyleSheet(
                        "background-color : rgb(192, 192, 192);")

        mutex.unlock()

# 程序入口
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # 开启线程
    controller = OuterTaskController()
    controller.start()

    elevator_list = []
    for i in range(ELEVATOR_NUMS):
        elevator_list.append(Elevator(i))

    for elevator in elevator_list:
        elevator.start()

    w = UI_MainWindow()
    sys.exit(app.exec_())