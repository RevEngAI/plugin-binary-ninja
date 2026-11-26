from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QColor, QTextCursor, QTextFormat
from binaryninja import log_error, log_info, HighlightStandardColor
from reai_toolkit.utils import create_progress_dialog, get_function_by_addr, CHighlighter
from PySide6.QtWidgets import QVBoxLayout, QCheckBox, QWidget, QTabWidget, QPlainTextEdit, QTextEdit

ATTRIBUTED_LINE = QColor(255, 215, 0, 70)
ATTRIBUTED_INSTRUCTION = HighlightStandardColor.YellowHighlightColor

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
        self._editor = None
        self._function = None
        self._last_addr = None
        self._caret_line = -1
        self._highlighted_addrs = []
        self._suppressed_addr = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("RevEng.AI: AI Decompilation")
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
        if self._suppressed_addr is not None:
            suppressed, self._suppressed_addr = self._suppressed_addr, None
            if func == suppressed:
                return
        if self._function is not None and self.tabs.count() and self._function.view == bv \
                and any(f.start == self._function.start for f in bv.get_functions_containing(func)):
            self._last_addr = func
            self._clear_instruction_highlights()
            self._highlight_from_address(func)
            return
        try:
            progress_dialog = create_progress_dialog(self, "RevEng.AI", "Setting up AI Decompilation...")
            progress_dialog.show()
            QCoreApplication.processEvents()

            self.clear_tabs()
            self._clear_instruction_highlights()

            function = get_function_by_addr(bv, func)
            self._function = function
            self._last_addr = func
            self._caret_line = -1
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
            editor.setPlainText("Starting AI Decompilation...")
            editor.setReadOnly(True)
            editor.cursorPositionChanged.connect(lambda: self._on_caret_moved(editor))
            self._editor = editor

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
            self._clear_instruction_highlights()
        except Exception as e:
            log_error(f"RevEng.AI | Error during cleanup: {str(e)}")
        
        super().closeEvent(event)

    def edit_editor(self, editor, text):
        editor.setPlainText(text)
        CHighlighter(editor.document())
        if editor is self._editor:
            self._highlight_from_address(self._last_addr)

    def _attributions(self):
        checker = self.ai_decompiler._current_checker
        if checker is None:
            return None, []
        return checker.attributions, checker.display_source

    def _highlight_from_address(self, addr):
        """Light the decompilation lines the instruction at addr fed, and scroll the first into view."""
        editor, function = self._editor, self._function
        if editor is None or function is None or addr is None:
            return
        editor.setExtraSelections([])
        self._caret_line = -1
        attributions, display_source = self._attributions()
        if attributions is None:
            return
        start = function.get_instruction_containing_address(addr)
        lines = attributions.decompilation_lines_for(addr if start is None else start)
        first = self._highlight_decompilation_lines(display_source, lines)
        if first >= 0:
            block = editor.document().findBlockByNumber(first)
            top = editor.blockBoundingGeometry(block).translated(editor.contentOffset()).top()
            if top < 0 or top > editor.viewport().height() - editor.fontMetrics().height():
                editor.verticalScrollBar().setValue(first)

    def _on_caret_moved(self, editor):
        if editor is not self._editor or not editor.hasFocus():
            return
        line = editor.textCursor().blockNumber()
        if line == self._caret_line:
            return
        self._caret_line = line
        self._highlight_from_decompilation(line)

    def _highlight_from_decompilation(self, display_line):
        """Light the caret's decompilation line and the instructions that fed it, and navigate to the first."""
        self._editor.setExtraSelections([])
        self._clear_instruction_highlights()
        attributions, display_source = self._attributions()
        if attributions is None or display_line >= len(display_source) or display_source[display_line] is None:
            return
        source = display_source[display_line]
        addresses = attributions.addresses_for(source)
        if not addresses:
            return
        self._highlight_decompilation_lines(display_source, [source])
        function = self._function
        for addr in addresses:
            function.set_auto_instr_highlight(addr, ATTRIBUTED_INSTRUCTION)
        self._highlighted_addrs = [(function, addr) for addr in addresses]
        self._navigate(function.view, addresses[0])

    def _highlight_decompilation_lines(self, display_source, lines):
        """Light every displayed line rendered from one of the 0-based source lines. Returns the first, or -1."""
        editor = self._editor
        selections = []
        first = -1
        for display_line, source in enumerate(display_source):
            if source is None or source not in lines:
                continue
            block = editor.document().findBlockByNumber(display_line)
            if not block.isValid():
                continue
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(ATTRIBUTED_LINE)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = QTextCursor(block)
            selections.append(selection)
            if first < 0:
                first = display_line
        editor.setExtraSelections(selections)
        return first

    def _navigate(self, bv, addr):
        self._suppressed_addr = addr
        if not bv.file.navigate(bv.file.view, addr):
            self._suppressed_addr = None
        self._editor.setFocus()

    def _clear_instruction_highlights(self):
        for function, addr in self._highlighted_addrs:
            try:
                function.set_auto_instr_highlight(addr, HighlightStandardColor.NoHighlightColor)
            except Exception as e:
                log_error(f"RevEng.AI | Error clearing highlight at 0x{addr:x}: {str(e)}")
        self._highlighted_addrs = []



