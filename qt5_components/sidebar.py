import PyQt5.QtWidgets as qt
from PyQt5.QtCore import Qt

class Sidebar(qt.QWidget):
    def __init__(self, settingsForm, parent=None):
        super().__init__(parent)

        # Create input field and button
        self.edit = qt.QLineEdit("Stock('TSLA', 'SMART', 'USD')", self)
        self.startButton = qt.QPushButton('Start Streaming', self)

        # Create the streaming settings form
        self.settingsForm = settingsForm(self)

        # Create layout and add widgets
        layout = qt.QVBoxLayout(self)
        layout.addWidget(qt.QLabel('Contract:'))
        layout.addWidget(self.edit)
        layout.addWidget(self.settingsForm)
        layout.addWidget(self.startButton)
        
        # Align items to the top
        layout.setAlignment(Qt.AlignTop)

        self.setLayout(layout)

    def getSettings(self):
        return self.settingsForm.getSettings()