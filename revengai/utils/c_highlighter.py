from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide6.QtCore import QRegularExpression

class CHighlighter(QSyntaxHighlighter):
    def __init__(self, document = None):
        super().__init__(document)

        def fmt(color, bold=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Bold)
            return f

        self.highlighting_rules = []

        # Keywords
        keywords = [
            "int", "char", "float", "double", "void", "if", "else", "while", "for", "return",
            "switch", "case", "break", "continue", "struct", "typedef", "const", "unsigned",
            "signed", "long", "short", "static", "volatile", "enum", "union", "do", "goto", "sizeof"
        ]
        keyword_format = fmt("#569CD6", True)
        for word in keywords:
            pattern = QRegularExpression(rf"\b{word}\b")
            self.highlighting_rules.append((pattern, keyword_format))

        # Types (optional C standard types)
        type_format = fmt("#4EC9B0")
        types = ["uint32_t", "int64_t", "uint8_t", "size_t"]
        for t in types:
            pattern = QRegularExpression(rf"\b{t}\b")
            self.highlighting_rules.append((pattern, type_format))

        # Strings
        string_format = fmt("#CE9178")
        self.highlighting_rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))

        # Char literals
        char_format = fmt("#CE9178")
        self.highlighting_rules.append((QRegularExpression(r"'.'"), char_format))

        # Comments
        comment_format = fmt("#6A9955")
        self.highlighting_rules.append((QRegularExpression(r"//.*"), comment_format))
        self.comment_start = QRegularExpression(r"/\*")
        self.comment_end = QRegularExpression(r"\*/")
        self.comment_format = comment_format

        # Numbers
        number_format = fmt("#B5CEA8")
        self.highlighting_rules.append((QRegularExpression(r"\b[0-9]+[uUlL]*\b"), number_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                start, length = match.capturedStart(), match.capturedLength()
                self.setFormat(start, length, fmt)

        # Multiline comment highlighting
        self.setCurrentBlockState(0)
        start_index = 0
        if self.previousBlockState() != 1:
            match = self.comment_start.match(text)
            start_index = match.capturedStart() if match.hasMatch() else -1

        while start_index >= 0:
            match_end = self.comment_end.match(text, start_index)
            end_index = match_end.capturedEnd() if match_end.hasMatch() else -1

            if end_index == -1:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            else:
                comment_length = end_index - start_index

            self.setFormat(start_index, comment_length, self.comment_format)
            start_index = self.comment_start.match(text, start_index + comment_length).capturedStart()
