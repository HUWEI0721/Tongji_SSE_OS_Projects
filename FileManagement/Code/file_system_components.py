import pickle
import os
from datetime import datetime
from bitarray import bitarray

BLOCK_NUM = 2 ** 10  # 块数
BLOCK_SIZE = 4  # 每块的大小

FAT_FREE = -2  # 表示FAT表中此块未被使用
FAT_END = -1  # 表示为FAT表中链表结尾

SPACE_OCCUPY = 1  # 磁盘被占用
SPACE_FREE = 0  # 未被占用

SAVEFILE = "file_system_save.save"


# 文件信息
class FCB:
    def __init__(self, file_name, create_time, length, parent = None,start_address=None):
        self.file_name = file_name
        self.create_time = create_time
        self.modify_time = create_time
        self.length = length
        self.start_address = start_address
        self.parent=parent


class FAT:
    def __init__(self):
        self.block_num = BLOCK_NUM
        self.table = []
        for i in range(BLOCK_NUM):
            self.table.append(FAT_FREE)


# 磁盘
class Disk():
    def __init__(self):
        # 用list代替链表指针
        self.list = []
        for i in range(BLOCK_NUM):
            self.list.append("")


# 空闲空间bitmap
class FreeSpace:
    def __init__(self):
        self.bitmap = bitarray(BLOCK_NUM)
        self.bitmap.setall(0)


# 多级目录中的文件夹结点
# N叉树的数据结构
class FileTreeNode:  # dir
    def __init__(self, name: str,create_time, parent=None):
        self.DirNode = []
        self.FileNode = []
        self.parent = parent
        self.dir_name = name
        self.create_time = create_time
        self.modify_time = create_time

class FileSystem:
    def __init__(self):
        # 存在存档文件
        if os.path.exists(SAVEFILE):
            # 按序读出文件信息
            with open(SAVEFILE, 'rb') as f:
                self.file_tree = pickle.load(f)
                self.free_space = pickle.load(f)
                self.disk = pickle.load(f)
                self.fat = pickle.load(f)
        # 不存在文件，自己创建一个
        else:
            self.file_tree = FileTreeNode("User",datetime.now())
            self.free_space = FreeSpace()
            self.disk = Disk()
            self.fat = FAT()

    def find_free_index(self):
        # 0 -> free
        return self.free_space.bitmap.find(0)

    def SaveSystemState(self):
        with open(SAVEFILE, 'wb') as f:
            pickle.dump(self.file_tree, f)
            pickle.dump(self.free_space, f)
            pickle.dump(self.disk, f)
            pickle.dump(self.fat, f)

    def FormatSystem(self):
        self.file_tree = FileTreeNode("User",datetime.now())
        self.free_space = FreeSpace()
        self.disk = Disk()
        self.fat = FAT()
        print("finish format")

    def createDir(self, curDir: FileTreeNode, Dirname, Curtime):
        for file in curDir.DirNode:
            if file.dir_name == Dirname:
                print("name exist")
                return False
        curDir.DirNode.append(FileTreeNode(Dirname,Curtime,curDir))
        curDir.modify_time = Curtime
        return True

    def createFile(self, curDir: FileTreeNode, Filename, Curtime):
        for file in curDir.FileNode:
            if file.file_name == Filename:
                print("File exist")
                return False

        curDir.modify_time = Curtime
        curDir.FileNode.append(FCB(Filename, Curtime, 0,curDir))

    def WriteFile(self, File: FCB, data):
        File.modify_time = datetime.now()
        File_Pointer = -1

        # 将data逐元素读入
        while data !="":
            # 找到第一个空的块
            next_point = self.find_free_index()
            if next_point == -1:
                # 满了
                print("no more free space")
                raise AssertionError("no more space")
            if File_Pointer == -1:
                # 第一个块的位置
                File.start_address = next_point
            else:
                self.fat.table[File_Pointer] = next_point

            self.disk.list[next_point] = data[:BLOCK_SIZE]
            data = data[BLOCK_SIZE:]
            self.free_space.bitmap[next_point] = SPACE_OCCUPY

            File_Pointer = next_point
            self.fat.table[File_Pointer] = FAT_END
            File.length += BLOCK_SIZE


    def DeleteFile(self,CurDir: FileTreeNode,File:FCB):
        # 删去记录
        CurDir.modify_time = datetime.now()
        CurDir.FileNode.remove(File)
        pointer = File.start_address
        if pointer is None:
            return False
        # 在位图中将相关的记录都删掉
        while self.fat.table[pointer] != FAT_END:
            self.free_space.bitmap[pointer]=SPACE_FREE
            pointer = self.fat.table[pointer]
        self.free_space.bitmap[pointer] = SPACE_FREE
        return True

    # 为递归清空文件夹提供函数
    def ClearDir(self,CurDir:FileTreeNode, DeleteDir:FileTreeNode):
        # 清空当前目录下的文件
        for file in DeleteDir.FileNode:
            self.DeleteFile(DeleteDir,file)
        # 递归清空当前目录下的子目录
        while len(DeleteDir.DirNode) >0:
            ChildDir = DeleteDir.DirNode[0]
            self.ClearDir(DeleteDir,ChildDir)
        CurDir.DirNode.remove(DeleteDir)
    def deleteDir(self, DeleteDir:FileTreeNode):
        pointer = DeleteDir.parent
        self.ClearDir(pointer,DeleteDir)

    def ReadFile(self,File:FCB):
        pointer = File.start_address
        if pointer is None:
            AssertionError("Open File which start addr is none")
        data = ""
        while pointer != FAT_END:
            data += self.disk.list[pointer]
            pointer=self.fat.table[pointer]
        return data

    def RenameFile(self,File:FCB, NewName:str, CurDir:FileTreeNode):
        File.file_name = NewName
        File.modify_time=datetime.now()
        CurDir.modify_time=datetime.now()

    def RenameDir(self, NewName:str, CurDir:FileTreeNode):
        CurDir.modify_time = datetime.now()
        CurDir.dir_name = NewName