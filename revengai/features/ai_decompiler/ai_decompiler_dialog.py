from binaryninja import log_error, log_info
from PySide6.QtWidgets import (QDockWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QCheckBox, QWidget, QTabWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QProgressBar
from revengai.utils import create_progress_dialog
from revengai.utils.data_thread import DataThread
import os

class AIDecompilerDialog(QWidget):
    def __init__(self, config, ai_decompiler, bv, func):
        super().__init__()
        self.config = config
        self.ai_decompiler = ai_decompiler
        self.bv = bv
        self.func = func
        self.tabs = QTabWidget()
        self.init_ui(func)

    def init_ui(self, func):
        self.setWindowTitle("RevEng.AI: AI Decompiler")
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.tabs)
        self.add_tab(func)
        self.tabs.tabCloseRequested.connect(self.close_tab)

    def add_tab(self, tab_name):
        tab_name = str(f"0x{tab_name:x}")
        for i in range(self.tabs.count()):
            log_info(f"RevEng.AI | Tab {self.tabs.tabText(i)} == {tab_name}")
            if self.tabs.tabText(i) == tab_name:
                self.tabs.setCurrentIndex(i)
                return

        log_info(f"RevEng.AI | Adding tab {tab_name}")
        tab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"{tab_name} UI goes here"))
        tab.setLayout(layout)
        index = self.tabs.addTab(tab, tab_name)
        self.tabs.setCurrentIndex(index)

        if self.tabs.count() > 1:
            self.tabs.setTabsClosable(True)
    
    def close_tab(self, index):
        log_info(f"RevEng.AI | Closing tab {index} of {self.tabs.count()} tabs")
        self.tabs.removeTab(index)
        if self.tabs.count() == 1: 
            self.tabs.setTabsClosable(False)

        
        

