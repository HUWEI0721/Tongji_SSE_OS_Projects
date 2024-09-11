import sys
import time
import random
from PyQt5.QtCore import QThread, pyqtSignal, QSemaphore, QTimer, QCoreApplication, Qt
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QApplication, QMainWindow
import MainWindow
from manager import MyManager



class Pcb:
    def __init__(self, page_size, code_amount):
        self.task_page_table_size = code_amount // page_size
        if code_amount % page_size != 0:
            self.task_page_table_size += 1  # 若不能整除，则增加一个页表页面
        self.page_table = [-1] * self.task_page_table_size  # 初始化页表，值为-1表示不在内存中

class Task:
    def __init__(self, page_size, code_amount):
        self.code_amount = code_amount  # 代码数量
        self.page_size = page_size  # 页尺寸
        self.pcb = Pcb(page_size, code_amount)  # 记录任务信息
        self.current_code_id = random.randint(0, self.code_amount - 1)  # 当前代码序号
        self.state = 0  # 状态，用于生成下一条代码的序号

    def get_current_code_id(self):
        tmp_code_id = self.current_code_id

        if self.state == 0:
            self.current_code_id = (self.current_code_id + 1) % self.code_amount  # 顺序执行
        elif self.state == 1:
            self.current_code_id = random.randint(0, max(self.current_code_id - 1, 0))  # 从当前代码之前的代码中随机取
        elif self.state == 2:
            self.current_code_id = (self.current_code_id + 1) % self.code_amount  # 顺序执行
        elif self.state == 3:
            self.current_code_id = random.randint(min(self.current_code_id + 1, self.code_amount - 1), self.code_amount - 1)  # 从当前代码之后的代码中随机取

        self.state = (self.state + 1) % 4  # 在四种状态中循环，每次被调用切换到下一个状态
        return tmp_code_id, self.pcb.page_table[tmp_code_id // self.page_size], tmp_code_id // self.page_size



# 定义运行模式信号量和运行模式标志
run_mode_semaphore = QSemaphore(1)
run_mode = 0

# 定义重置信号量和重置标志
reset_flag_semaphore = QSemaphore(1)
reset_flag = 0


# 信号量操作：获取信号量
def semaphore_acquire(semaphore):
    semaphore.acquire()


# 信号量操作：释放信号量
def semaphore_release(semaphore):
    semaphore.release()


# 单步执行按钮响应
def enable_step_mode():
    global run_mode
    semaphore_acquire(run_mode_semaphore)
    run_mode = 1
    semaphore_release(run_mode_semaphore)


# 连续执行按钮响应
def enable_continuous_mode():
    global run_mode
    semaphore_acquire(run_mode_semaphore)
    run_mode = 2
    semaphore_release(run_mode_semaphore)


# 暂停按钮响应
def pause_execution():
    global run_mode
    semaphore_acquire(run_mode_semaphore)
    run_mode = 0
    semaphore_release(run_mode_semaphore)


# 重置按钮响应
def reset_execution():
    global reset_flag
    semaphore_acquire(reset_flag_semaphore)
    reset_flag = 1
    semaphore_release(reset_flag_semaphore)


# 按钮颜色还原
def restore_button_color(button):
    button.setStyleSheet("background-color: #d3d3d3")  # 更改为浅灰色


# 更新界面
def update_ui(code_num, cur_code, need_swap, old_page, code_page, memory_page, page_missing, page_size, code_amount):
    # 构建对齐文本行
    aligned_text = "{:<3} {:<4} {:<4} {:<4} {:<2}".format(
        str(code_num), str(cur_code), "是" if need_swap else "否",
        str(old_page) if old_page != -1 else "-", str(code_page) if need_swap else "-"
    )

    # 更新文本框内容并设置只读
    ui.textEdit.append("<pre><font face='仿宋'>{}</font></pre>".format(aligned_text))
    ui.textEdit.setReadOnly(True)
    ui.textEdit.moveCursor(QTextCursor.End)

    if need_swap:
        ui.label_16.setText(str(page_missing))
        eval("ui.label_" + str(memory_page + 1)).setText("第" + str(code_page).ljust(2) + "页".ljust(4))
        for i in range(1, 11):
            eval("ui.pushButton_" + str(memory_page * 10 + i)).setText(str(code_page * page_size + i - 1))

    # 更新缺页率
    ui.label_18.setText("{:.2f}%".format(page_missing / (code_num + 1) * 100))

    if (code_num + 1) >= code_amount:
        ui.textEdit.append("{}条指令(0-{})完成".format(code_amount, code_amount - 1))
        ui.textEdit.moveCursor(QTextCursor.End)

    # 按钮高亮显示当前执行的指令，并在短时间后还原颜色
    button = eval("ui.pushButton_" + str(memory_page * 10 + cur_code % page_size + 1))
    button.setStyleSheet("background-color: #90ee90")  # 更改为浅绿色
    QTimer.singleShot(100, lambda: restore_button_color(button))


# 重置界面
def reset_ui():
    # 打印重置信息
    ui.textEdit.append("已重置")
    ui.textEdit.append("开始新一轮模拟!")
    ui.textEdit.moveCursor(QTextCursor.End)

    # 重置所有标签文本
    for i in range(1, 5):
        eval("ui.label_" + str(i)).setText("第--页")

    # 重置所有按钮文本和颜色
    for j in range(4):
        for i in range(1, 11):
            button = eval("ui.pushButton_" + str(j * 10 + i))
            button.setText(" ")
            button.setStyleSheet("background-color: #ffffff")  # 将按钮背景色设置为白色
    # 重置缺页数和缺页率
    ui.label_16.setText("0")  # 缺页数重置为0
    ui.label_18.setText("0.00%")  # 缺页率重置为0.00%

# 模拟线程类
class SimulationThread(QThread):
    # 定义信号
    update_signal = pyqtSignal(int, int, bool, int, int, int, int, int, int)
    reset_signal = pyqtSignal()

    def __init__(self):
        super(SimulationThread, self).__init__()
        self.tmp_reset_flag = None
        # 连接信号与槽
        self.update_signal.connect(update_ui)
        self.reset_signal.connect(reset_ui)

    # 检查重置状态
    def check_for_reset(self):
        global reset_flag
        semaphore_acquire(reset_flag_semaphore)
        if reset_flag:
            reset_flag = 0
            semaphore_release(reset_flag_semaphore)
            self.reset_signal.emit()
            return True
        semaphore_release(reset_flag_semaphore)
        return False

    # 等待用户第一次设定运行模式
    def wait_for_initial_mode(self):
        global run_mode
        while True:
            semaphore_acquire(run_mode_semaphore)
            if run_mode in [1, 2]:
                semaphore_release(run_mode_semaphore)
                break
            semaphore_release(run_mode_semaphore)

    # 等待用户更改运行模式
    def wait_for_mode_change(self):
        global run_mode
        while True:
            semaphore_acquire(run_mode_semaphore)
            if run_mode == 1:
                run_mode = 0
                semaphore_release(run_mode_semaphore)
                break
            elif run_mode == 2:
                semaphore_release(run_mode_semaphore)
                break
            semaphore_release(run_mode_semaphore)

            semaphore_acquire(reset_flag_semaphore)
            if reset_flag:
                semaphore_release(reset_flag_semaphore)
                self.tmp_reset_flag = True
                break
            semaphore_release(reset_flag_semaphore)

    def run(self):
        while True:
            global run_mode
            semaphore_acquire(run_mode_semaphore)
            run_mode = 0
            semaphore_release(run_mode_semaphore)

            self.wait_for_initial_mode()

            global reset_flag
            semaphore_acquire(reset_flag_semaphore)
            reset_flag = 0
            semaphore_release(reset_flag_semaphore)

            page_size = 10
            code_amount = ui.spinBox.value()
            page_swap_algo = ui.comboBox.currentText()

            task = Task(page_size=page_size, code_amount=code_amount)
            manager = MyManager(page_size=page_size, algo=page_swap_algo)
            page_missing = 0

            self.tmp_reset_flag = False

            while True:
                if self.check_for_reset():
                    break

                self.wait_for_mode_change()
                if self.tmp_reset_flag:
                    self.tmp_reset_flag = False
                    continue

                log_code_num, log_cur_code, log_page_missing, log_old_page, log_code_page, log_memory_page = manager.run_task(
                    task)

                if log_page_missing:
                    page_missing += 1
                if log_code_num >= (code_amount - 1):
                    semaphore_acquire(reset_flag_semaphore)
                    reset_flag = 1
                    semaphore_release(reset_flag_semaphore)

                self.update_signal.emit(log_code_num, log_cur_code, log_page_missing, log_old_page, log_code_page,
                                        log_memory_page, page_missing, page_size, code_amount)
                time.sleep(0.1)


if __name__ == "__main__":
    # 启用高DPI显示
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    main_window = QMainWindow()
    ui = MainWindow.Ui_MainWindow()
    ui.setupUi(main_window)

    # 连接按钮点击事件与相应的功能
    ui.pushButton_41.clicked.connect(enable_step_mode)
    ui.pushButton_42.clicked.connect(enable_continuous_mode)
    ui.pushButton_43.clicked.connect(pause_execution)
    ui.pushButton.clicked.connect(reset_execution)

    simulation_thread = SimulationThread()
    simulation_thread.start()

    main_window.show()
    sys.exit(app.exec_())
