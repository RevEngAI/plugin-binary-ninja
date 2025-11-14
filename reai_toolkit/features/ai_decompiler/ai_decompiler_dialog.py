from PySide6.QtCore import QCoreApplication
from binaryninja import log_error, log_info
from reai_toolkit.utils import create_progress_dialog, get_function_by_addr, CHighlighter
from PySide6.QtWidgets import QVBoxLayout, QCheckBox, QWidget, QTabWidget, QPlainTextEdit

class AIDecompilerDialog(QWidget):
    def __init__(self, config, ai_decompiler, bv, func):
        super().__init__()
        self.config = config
        self.ai_decompiler = ai_decompiler
        self.ai_decompiler.dialog = self
        self.bv = bv
        self.func = func
        self.tabs = QTabWidget()
        self.number_of_clicks = 0
        self.initial_setup_done = False
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("RevEng.AI: AI Decompiler")
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.tabs)
        self.address_tracking_checkbox = QCheckBox("Address Tracking")
        self.address_tracking_checkbox.setChecked(True)
        layout.addWidget(self.address_tracking_checkbox)
        self.address_tracking_checkbox.stateChanged.connect(self.toggle_address_tracking)
        self.tabs.tabCloseRequested.connect(self.close_tab)

    def showEvent(self, event):
        super().showEvent(event)
        if not self.initial_setup_done:
            self.initial_setup_done = True
            QCoreApplication.processEvents()
            self.pre_tab_setup(self.bv, self.func)

    def toggle_address_tracking(self, state):
        log_info(f"RevEng.AI | Address tracking checkbox state changed to {state}")
        if state == 2:
            log_info(f"RevEng.AI | Starting address tracking")
            self.ai_decompiler.start_address_tracking()
        else:
            log_info(f"RevEng.AI | Stopping address tracking")
            self.ai_decompiler.stop_address_tracking()
    
    def clear_tabs(self):
        for i in range(self.tabs.count()):
            self.close_tab(i)
 
    def pre_tab_setup(self, bv, func):
        try:
            progress_dialog = create_progress_dialog(self, "RevEng.AI", "Setting up AI Decompiler...")
            progress_dialog.show()
            QCoreApplication.processEvents()

            self.clear_tabs()

            function = get_function_by_addr(bv, func)
            tab_name = str(f"0x{function.start:x}")
            log_info(f"RevEng.AI | Given address 0x{func:x} is function: {function.name} at 0x{function.start:x}")
            for i in range(self.tabs.count()):
                if self.tabs.tabText(i) == tab_name:
                    log_info(f"RevEng.AI | Tab {tab_name} already exists, switching to it.")
                    self.tabs.setCurrentIndex(i)
                    progress_dialog.close()
                    return
                
            log_info(f"RevEng.AI | Adding tab {tab_name}")
            tab = QWidget()
            layout = QVBoxLayout()

            editor = QPlainTextEdit()
            editor.setPlainText("Starting AI Decompiler...")
            editor.setReadOnly(True)

            editor.show()
            QCoreApplication.processEvents()

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
            progress_dialog.close()
        except Exception as e:
            if 'progress_dialog' in locals():
                progress_dialog.close()
            log_error(f"RevEng.AI | Error during pre_tab_setup: {str(e)}")
    
    def close_tab(self, index):
        log_info(f"RevEng.AI | Closing tab {index} of {self.tabs.count()} tabs")
        
        try:
            self.ai_decompiler.stop_ai_decompiler()
        except Exception as e:
            log_error(f"RevEng.AI | Error stopping AI decompiler on tab close: {str(e)}")
        
        self.tabs.removeTab(index)
        if self.tabs.count() == 1: 
            self.tabs.setTabsClosable(False)

    def closeEvent(self, event):
        try:
            if hasattr(self, 'ai_decompiler'):
                log_info(f"RevEng.AI | Stopping AI decompiler")
                self.ai_decompiler.stop_ai_decompiler()
        except Exception as e:
            log_error(f"RevEng.AI | Error during cleanup: {str(e)}")
        
        super().closeEvent(event)

    def edit_editor(self, editor, text):
        editor.setPlainText(text)
        CHighlighter(editor.document())



