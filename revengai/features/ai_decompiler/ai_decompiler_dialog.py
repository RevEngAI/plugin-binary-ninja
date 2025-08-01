from binaryninja import log_error, log_info
from PySide6.QtWidgets import (QDockWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QCheckBox, QWidget, QTabWidget, QPlainTextEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QProgressBar
from revengai.utils import create_progress_dialog
from .c_highlighter import CHighlighter
from revengai.utils.data_thread import DataThread
from revengai.utils import get_function_by_addr
from revengai.utils.periodic_check import PeriodicChecker
import os

class AIDecompilerDialog(QWidget):
    def __init__(self, config, ai_decompiler, bv, func):
        super().__init__()
        self.config = config
        self.ai_decompiler = ai_decompiler
        self.bv = bv
        self.func = func
        self.tabs = QTabWidget()
        self.number_of_clicks = 0
        self.init_ui(bv, func)

    def init_ui(self, bv, func):
        self.setWindowTitle("RevEng.AI: AI Decompiler")
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.tabs)
        self.pre_tab_setup(bv, func)
        self.tabs.tabCloseRequested.connect(self.close_tab)

    def pre_tab_setup(self, bv, func):
        function = get_function_by_addr(bv, func)
        tab_name = str(f"0x{function.start:x}")
        log_info(f"RevEng.AI | Given address 0x{func:x} is function: {function.name} at 0x{function.start:x}")
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == tab_name:
                log_info(f"RevEng.AI | Tab {tab_name} already exists, switching to it.")
                return
            
        log_info(f"RevEng.AI | Adding tab {tab_name}")
        tab = QWidget()
        layout = QVBoxLayout()

        editor = QPlainTextEdit()
        editor.setPlainText("Starting AI Decompiler...")
        editor.setReadOnly(True)

        #CHighlighter(editor.document())
        editor.show()
        layout.addWidget(editor)
        tab.setLayout(layout)
        
        index = self.tabs.addTab(tab, tab_name)
        self.tabs.setCurrentIndex(index)

        if self.tabs.count() > 1:
            self.tabs.setTabsClosable(True)

        options = {
            "editor": editor,
            "tab_name": tab_name,
            "function": function,
            "callback": self.edit_editor
        }
        self.ai_decompiler.start_ai_decompiler(self.bv, options)
    
    def close_tab(self, index):
        log_info(f"RevEng.AI | Closing tab {index} of {self.tabs.count()} tabs")
        
        # Stop AI decompiler for this tab if it's running
        try:
            self.ai_decompiler.stop_ai_decompiler()
        except Exception as e:
            log_error(f"RevEng.AI | Error stopping AI decompiler on tab close: {str(e)}")
        
        self.tabs.removeTab(index)
        if self.tabs.count() == 1: 
            self.tabs.setTabsClosable(False)

    def closeEvent(self, event):
        """Handle dialog close event"""
        try:
            # Stop any running AI decompiler
            if hasattr(self, 'ai_decompiler'):
                self.ai_decompiler.stop_ai_decompiler()
        except Exception as e:
            log_error(f"RevEng.AI | Error during cleanup: {str(e)}")
        
        super().closeEvent(event)

    def edit_editor(self, editor, text):
        editor.setPlainText(text)
        CHighlighter(editor.document())



