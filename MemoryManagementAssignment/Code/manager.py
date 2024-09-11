import queue

class MyManager:
    def __init__(self, page_size, algo):
        self.task_memory_page_amount = 4  # 分配给任务的页面数
        self.page_size = page_size  # 页面尺寸
        self.task_page = [None] * self.task_memory_page_amount  # 分配的页面 记录页面号
        self.code_num = 0  # 记录执行到第几条代码
        self.algo = algo  # 记录设定的管理器的算法
        self.page_allocated_amount = 0

        if self.algo == 'FIFO':  # 根据不同的算法配置不同的参数
            self.page_allocate_queue = queue.Queue()  # 记录页面分配顺序
        elif self.algo == 'LRU':
            self.unused_time = [None] * self.task_memory_page_amount  # 记录页面未被使用的时间

    def page_swap(self, dst_memory_page_id, code_page_id, task):  # 页面调换
        old_page = self.task_page[dst_memory_page_id]  # 获取旧页面
        self.task_page[dst_memory_page_id] = code_page_id  # 写入新页面
        task.pcb.page_table[old_page] = -1  # 更新旧页面页表
        task.pcb.page_table[code_page_id] = dst_memory_page_id  # 更新新页面页表
        return old_page

    def allocate_empty_page(self, empty_page_id, code_page_id, task):  # 分配空页面
        self.task_page[empty_page_id] = code_page_id
        task.pcb.page_table[code_page_id] = empty_page_id
        self.page_allocated_amount += 1

    def update_unused_time(self, used_page_id):  # 用于LRU算法，更新页面未被使用的时间
        for i in range(self.task_memory_page_amount):
            if self.unused_time[i] is not None:
                self.unused_time[i] += 1
        self.unused_time[used_page_id] = 0  # 被使用的页面重置未使用时间

    def run_task(self, task):
        if self.algo == 'FIFO':
            return self.run_task_fifo(task)
        elif self.algo == 'LRU':
            return self.run_task_lru(task)

    def run_task_fifo(self, task):
        # 获取当前要执行的代码信息
        current_code_id, memory_page_for_code, code_page_id = task.get_current_code_id()
        # 初始化log，记录可视化界面所需信息
        log_code_num, log_cur_code, log_page_missing, log_old_page, log_code_page, log_memory_page = 0, 0, False, -1, -1, -1

        if memory_page_for_code != -1:  # 在内存中
            log_page_missing, log_old_page, log_memory_page = False, -1, memory_page_for_code
        else:  # 不在内存中
            if self.page_allocated_amount < self.task_memory_page_amount:  # 内存没有分配满
                for i in range(self.task_memory_page_amount):
                    if self.task_page[i] is None:  # 找到空位置
                        self.allocate_empty_page(i, code_page_id, task)  # 分配空的模拟内存页面
                        self.page_allocate_queue.put(i)  # 插入FIFO算法队列
                        log_page_missing, log_old_page, log_memory_page = True, -1, i
                        break
            else:  # 内存已满，进行页面调换
                dst_memory_page_id = self.page_allocate_queue.get()  # 从队列中取出最早分配的页序号
                old_page = self.page_swap(dst_memory_page_id, code_page_id, task)  # 页面调换
                self.page_allocate_queue.put(dst_memory_page_id)  # 新分配的页序号插入队尾
                log_page_missing, log_old_page, log_memory_page = True, old_page, dst_memory_page_id

        log_code_num, log_cur_code, log_code_page = self.code_num, current_code_id, code_page_id
        self.code_num += 1
        return log_code_num, log_cur_code, log_page_missing, log_old_page, log_code_page, log_memory_page

    def run_task_lru(self, task):
        # 获取当前要执行的代码信息
        current_code_id, memory_page_for_code, code_page_id = task.get_current_code_id()
        # 初始化log，记录可视化界面所需信息
        log_code_num, log_cur_code, log_page_missing, log_old_page, log_code_page, log_memory_page = 0, 0, False, -1, -1, -1

        if memory_page_for_code != -1:  # 在内存中
            self.update_unused_time(used_page_id=memory_page_for_code)
            log_page_missing, log_old_page, log_memory_page = False, -1, memory_page_for_code
        else:  # 不在内存中
            if self.page_allocated_amount < self.task_memory_page_amount:  # 内存没有分配满
                for i in range(self.task_memory_page_amount):
                    if self.task_page[i] is None:  # 找到空位置
                        self.allocate_empty_page(i, code_page_id, task)  # 分配空的模拟内存页面
                        self.update_unused_time(used_page_id=i)  # 更新LRU算法记录的未使用时间
                        log_page_missing, log_old_page, log_memory_page = True, -1, i
                        break
            else:  # 内存已满，进行页面调换
                dst_memory_page_id = self.unused_time.index(max(self.unused_time))  # 找到最久未使用的页序号
                old_page = self.page_swap(dst_memory_page_id, code_page_id, task)  # 页面调换
                self.update_unused_time(used_page_id=dst_memory_page_id)  # 更新LRU算法记录的未使用时间
                log_page_missing, log_old_page, log_memory_page = True, old_page, dst_memory_page_id

        log_code_num, log_cur_code, log_code_page = self.code_num, current_code_id, code_page_id
        self.code_num += 1
        return log_code_num, log_cur_code, log_page_missing, log_old_page, log_code_page, log_memory_page
