import sys
import MainWindow
import file_system_components
from datetime import datetime

from PyQt5 import QtCore
from PyQt5.QtGui import QIcon, QStandardItemModel, QStandardItem, QTextOption,QCursor
from PyQt5.QtCore import QModelIndex,Qt
from PyQt5.QtWidgets import  QApplication,QMainWindow, QMessageBox, QInputDialog, QAbstractItemView, QMenu,QWidget


import qdarkstyle
from qdarkstyle.light.palette import LightPalette

class FileSystem(QMainWindow,QWidget,file_system_components.FileSystem):
    def __init__(self):
        super().__init__()
        self.ui = MainWindow.Ui_MainWindow()
        self.ui.setupUi(self)
        # 记录当前路径
        self.cur_path = "User/"

        # Node
        self.cur_selected_file = None
        self.cur_selected_dir = None

        # HeadNode
        self.Head = file_system_components.FileTreeNode("head",datetime.now())
        self.Head.DirNode.append(self.file_tree)

        # 右键菜单
        self.ui.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.treeView.customContextMenuRequested.connect(self.rightclick)

        self.setui()


    def setui(self):
        self.UpdateUI()
        self.ui.filecontent.setWordWrapMode(QTextOption.WrapAnywhere)
        # 记录connect
        self.ui.SaveFile.clicked.connect(self.SaveFile)
        self.ui.FormatFileSystem.triggered.connect(self.sys_format)
        self.ui.Save_System_Status.triggered.connect(self.sys_SaveSys)
        self.ui.CreateDir.triggered.connect(self.sys_create_dir)
        self.ui.CreateFile.triggered.connect(self.sys_create_file)
        self.ui.DeleteDir.triggered.connect(self.sys_delete_dir)
        self.ui.DeleteFile.triggered.connect(self.sys_delete_file)
        self.ui.RenameDir.triggered.connect(self.sys_rename_dir)
        self.ui.RenameFile.triggered.connect(self.sys_rename_file)
        self.ui.actionHelp.triggered.connect(self.sys_Help)
        self.ui.actionAbout.triggered.connect(self.sys_About)
        self.ui.actionaddition.triggered.connect(self.sys_Addition)




    def sys_Help(self):
        msg="1.请点击中间界面的文件/文件夹，当上方'当前路径栏'内显示点击的路径后可以右键选择或上方菜单栏选择\n"\
            "2.请不要选择文件夹后选择文件操作，反之亦然\n"\
            "3.选择文件后可以在右边框内修改文件内容\n"\
            "4.总储存只有4K(4B*1024块）"
        QMessageBox.about(self,'使用说明',msg)

    def sys_About(self):
        msg = "文件管理系统\n"\
                "作者：2153393 胡峻玮\n"
        QMessageBox.about(self, '关于', msg)

    def sys_Addition(self):
        msg = "好离谱！"
        QMessageBox.about(self,'破防了',msg)
    def SysStatusLog(self):
        if self.cur_selected_dir is not None:
            print(f"curent dir:{self.cur_selected_dir.dir_name}")
        else:
            print(f"curent dir is None")
        if self.cur_selected_file is not None:
            print(f"curent file:{self.cur_selected_file.file_name}")
        else:
            print("curent file is None")
    def dfsBuildTreeModel(self,model:QStandardItemModel,file_tree_node:file_system_components.FileTreeNode):
        for file in file_tree_node.FileNode:
            Item = QStandardItem(file.file_name)
            Item.setIcon(QIcon('picture/File.png'))
            model.appendRow(Item)

        for dirnode in file_tree_node.DirNode:
            child_model = QStandardItem(dirnode.dir_name)
            child_model.setIcon(QIcon('picture/NoContentFileDir.png'))
            self.dfsBuildTreeModel(child_model,dirnode)
            model.appendRow(child_model)


    def BuildTreeModel(self)-> QStandardItemModel:
        root_item = QStandardItem(self.file_tree.dir_name)
        self.dfsBuildTreeModel(root_item,self.file_tree)
        model = QStandardItemModel()
        model.appendRow(root_item)
        return model

    def UpdateTreeView(self):
        self.ui.treeView.setModel(self.BuildTreeModel())
        self.ui.treeView.expandAll()
        # 点击事件
        self.ui.treeView.selectionModel().currentChanged.connect(self.ClickTreeItem)
        # 不可修改
        self.ui.treeView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # 鼠标滚轮
        self.ui.treeView.header().setStretchLastSection(True)
        self.ui.treeView.horizontalScrollBar().setEnabled(True)
        self.ui.treeView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.ui.treeView.verticalScrollBar().setEnabled(True)
        self.ui.treeView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

    def rightclick(self):
        if self.cur_selected_dir is None and self.cur_selected_file is None:
            return
        SelectMenu = QMenu(self)
        if self.cur_selected_file is not None:
            SelectMenu.addAction("删除文件",self.sys_delete_file)
            SelectMenu.addAction("重命名文件",self.sys_rename_file)
        elif self.cur_selected_dir is not None:
            SelectMenu.addAction("创建文件",self.sys_create_file)
            SelectMenu.addAction("创建文件夹",self.sys_create_dir)
            SelectMenu.addAction("重命名文件夹",self.sys_rename_dir)
            SelectMenu.addAction("删除文件夹",self.sys_delete_dir)
        SelectMenu.addAction("保存系统状态",self.sys_SaveSys)
        SelectMenu.addAction("格式化",self.sys_format)
        SelectMenu.popup(QCursor.pos())

    def bulidListView(self) ->QStandardItemModel:
        model = QStandardItemModel()
        if self.cur_selected_dir is not None and self.cur_selected_file is None:
            for file in self.cur_selected_dir.FileNode:
                Item =QStandardItem(file.file_name)
                Item.setIcon(QIcon('picture/File.png'))
                model.appendRow(Item)
            for childdir in self.cur_selected_dir.DirNode:
                Item = QStandardItem(childdir.dir_name)
                Item.setIcon(QIcon('picture/NoContentFileDir.png'))
                model.appendRow(Item)
        else:
            model.clear()
        return model

    def UpdateListView(self):
        self.ui.CurDirAllNode.setModel(self.bulidListView())
        # ListView
        self.ui.CurDirAllNode.selectionModel().currentChanged.connect(self.ClickListItem)

    def UpdateComponent(self):
        if self.cur_selected_file is None:
            self.ui.SaveFile.setEnabled(False)
        else:
            self.ui.SaveFile.setEnabled(True)

    def ClickListItem(self, Item:QModelIndex):
        print(f"click item.row()={Item.row()}")
        if Item.row() < len(self.cur_selected_dir.FileNode):
            self.cur_selected_file = self.cur_selected_dir.FileNode[Item.row()]
            self.cur_path +=f"{self.cur_selected_file.file_name}/"
        else:
            self.cur_selected_dir = self.cur_selected_dir.DirNode[Item.row()-len(self.cur_selected_dir.FileNode)]
            self.cur_path +=f"{self.cur_selected_dir.dir_name}/"
        print("Click List Item")
        self.SysStatusLog()
        self.UpdateUI()
        print("finish click list item")

    def UpdateFileText(self):
        msg=""
        if self.cur_selected_file is None:
            msg = "暂无信息"
            self.ui.filecontent.setReadOnly(True)
        elif self.cur_selected_file.start_address is None:
            msg= ""
            self.ui.filecontent.setReadOnly(False)
        else:
            msg = self.ReadFile(self.cur_selected_file)
            self.ui.filecontent.setReadOnly(False)
        self.ui.filecontent.setPlainText(msg)

    def UpdateUI(self,UpdateTreeView=1,UpdateListView=1):
        # 更新组件

        self.UpdateComponent()
        # 更新当前目录
        self.ui.CurDir.setText(self.cur_path)
        # 更新左侧当前树结构
        if UpdateTreeView == 1:
            self.UpdateTreeView()

        # 更新中间视图
        if UpdateListView == 1:
            self.UpdateListView()
        # 更新文件信息
        self.UpdateSelectInfo()

        # 更新右侧内容
        self.UpdateFileText()


    def UpdateSelectInfo(self):
        msg = ""
        if self.cur_selected_dir is not None:
            msg += (
                f"当前文件夹: {str(self.cur_selected_dir.dir_name).ljust(10)} "
                f"最近更新时间: {str(self.cur_selected_dir.modify_time).ljust(20)}\n"
                f"创建时间: {str(self.cur_selected_dir.create_time).ljust(20)} "
                f"子文件个数: {str(len(self.cur_selected_dir.FileNode) + len(self.cur_selected_dir.DirNode)).ljust(5)}\n"
            )
        if self.cur_selected_file is not None:
            msg += (
                f"当前文件: {str(self.cur_selected_file.file_name).ljust(10)} "
                f"创建时间: {str(self.cur_selected_file.create_time).ljust(20)}\n"
                f"最近更新时间: {str(self.cur_selected_file.modify_time).ljust(20)} "
                f"文件大小: {str(self.cur_selected_file.length).ljust(5)}B"
            )
        if self.cur_selected_dir is None and self.cur_selected_file is None:
            msg = "未选择文件"

        self.ui.textBrowser_3.setText(msg)



    def ClickTreeItem(self,Item:QModelIndex):
        # 记录当前index
        record = Item
        # 更新当前路径
        reverse_path = []
        while record.data() is not None:
            reverse_path.append(record.data())
            record=record.parent()
        pathlist = list(reversed(reverse_path))
        path = ""
        for pathname in pathlist:
            path = path +str(pathname)+'/'
        self.cur_path = path

        # 更新当前信息
        # 首先搜索到这一信息块
        pointer = self.Head
        # 第一个一定是根节点,因为要判断类型所以搜索到倒数第二个
        for i in range(0,len(pathlist)-1):
            for childdir in pointer.DirNode:
                if childdir.dir_name == pathlist[i]:
                    pointer = childdir
                    break
        # 前面是文件后面是文件夹,根据索引判断是文件还是文件夹
        if Item.row() > len(pointer.FileNode)-1:
            self.cur_selected_dir = pointer.DirNode[Item.row()-len(pointer.FileNode)]
            self.cur_selected_file = None
        else:
            self.cur_selected_file = pointer.FileNode[Item.row()]
            self.cur_selected_dir = pointer
        print("ClickEvent:")
        self.SysStatusLog()

        self.UpdateUI(0)
        print("finish click event")
        print(self.file_tree.DirNode)
    def SaveFile(self):
        self.WriteFile(self.cur_selected_file,self.ui.filecontent.toPlainText())
        QMessageBox.warning(self,"提示","保存成功！")

    def sys_format(self):
        ans = QMessageBox.question(self,"您确定吗？","是否格式化",QMessageBox.Yes|QMessageBox.No)
        if ans == QMessageBox.Yes:
            self.FormatSystem()
            self.cur_selected_file=None
            self.cur_selected_dir=None
            self.cur_path = "User/"
            print(self.file_tree.DirNode)
            self.Head.DirNode.clear()
            self.Head.DirNode.append(self.file_tree)
            self.UpdateUI()

    def sys_SaveSys(self):
        self.SaveSystemState()
        QMessageBox.warning(self,"消息","已保存当前系统状态")

    def sys_create_dir(self):
        dir_name,check = QInputDialog.getText(self,'New File','输入文件夹名')
        if check:
            if dir_name == "":
                QMessageBox.warning(self,"Warning","文件夹名为空！")
            elif self.cur_selected_dir is None:
                QMessageBox.warning(self, "Warning", "未选定创建路径！")
            elif len([i for i in self.cur_selected_dir.DirNode if i.dir_name == dir_name])>0:
                QMessageBox.warning(self,"Warning","文件夹已存在！")
            else:
                self.createDir(self.cur_selected_dir,dir_name,datetime.now())
                self.UpdateUI()
    def sys_create_file(self):
        new_file_name, ok = QInputDialog.getText(self, '创建文件', '输入创建文件名：')
        if ok:
            if new_file_name == "":
                QMessageBox.warning(self, "Warning", "文件名为空！")
            elif self.cur_selected_dir is None:
                QMessageBox.warning(self, "Warning", "未选定文件所在文件夹！")
            elif len([x for x in self.cur_selected_dir.DirNode if x.dir_name == new_file_name]) > 0:
                QMessageBox.warning(self, "Warning", "已有重复文件名！")
            else:
                self.createFile(self.cur_selected_dir,new_file_name,datetime.now())
                self.UpdateUI()
    def sys_delete_file(self):
        if self.cur_selected_file is None:
            QMessageBox.warning(self,"Warning","未选定删除的文件！")
            return
        self.DeleteFile(self.cur_selected_dir,self.cur_selected_file)
        self.cur_selected_file = None
        self.UpdateUI()

    def sys_delete_dir(self):
        if self.cur_selected_dir is None:
            QMessageBox.warning(self,"Warning","未选定删除的文件夹！")
            return
        elif self.cur_selected_dir == self.file_tree:
            QMessageBox.warning(self,"Warning","不能删去根文件夹！")
            return
        self.deleteDir(self.cur_selected_dir)
        self.cur_selected_dir = None
        self.cur_selected_file = None
        self.UpdateUI()

    def sys_rename_file(self):
        if self.cur_selected_file is None:
            QMessageBox.warning(self, "Warning", "未选中文件！")
            return
        new_name,check = QInputDialog.getText(self,"重命名文件","输入新文件名:")
        if check:
            if new_name == "":
                QMessageBox.warning(self, "Warning", "文件名为空！")
            elif len([i for i in self.cur_selected_dir.FileNode if i.file_name == new_name])>0:
                QMessageBox.warning(self, "Warning", "已有重复文件名！")
            else:
                self.RenameFile(self.cur_selected_file,new_name,self.cur_selected_dir)
                self.UpdateUI()

    def sys_rename_dir(self):
        if self.cur_selected_dir is None:
            QMessageBox.warning(self, "Warning", "未选中文件夹！")
            return
        elif self.cur_selected_dir == self.file_tree:
            QMessageBox.warning(self, "Warning", "不可修改根目录信息！")
            return
        new_name, check = QInputDialog.getText(self, "重命名文件", "输入新文件夹名:")
        if check:
            if new_name == "":
                QMessageBox.warning(self, "Warning", "文件夹名为空！")
            elif len([i for i in self.cur_selected_dir.parent.FileNode if i.file_name == new_name])>0:
                QMessageBox.warning(self, "Warning", "存在相同文件名！")
            else:
                self.RenameDir(new_name,self.cur_selected_dir)
                self.UpdateUI()
    def closeEvent(self, Event) -> None:
        self.sys_SaveSys()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    mymain = FileSystem()
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5', palette=LightPalette()))

    mymain.show()
    sys.exit(app.exec_())