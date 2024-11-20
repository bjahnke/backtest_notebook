from PyQt5 import QtWidgets as qt

class StreamingSettingsForm(qt.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Create input fields and labels
        self.countEdit = qt.QSpinBox(self)
        self.countEdit.setRange(1, 1000)
        self.countEdit.setValue(1)

        self.unitEdit = qt.QComboBox(self)
        self.unitEdit.addItems(['S', 'D', 'W', 'M', 'Y'])
        self.unitEdit.setCurrentIndex(1)

        self.barSizeNum = qt.QSpinBox(self)
        self.barSizeNum.setRange(1, 1000)
        self.barSizeNum.setValue(5)
        self.barSizeUnit = qt.QComboBox(self)
        self.barSizeUnit.addItems(['S', 'Mi', 'H', 'D', 'W', 'Mo'])
        self.barSizeUnit.setCurrentIndex(1)

        self.useRTHCheckBox = qt.QCheckBox('Use RTH', self)
        self.useRTHCheckBox.setChecked(True)

        self.addBandCheckBox = qt.QCheckBox('Add Band', self)
        self.addBandCheckBox.setChecked(False)

        self.windowEdit = qt.QSpinBox(self)
        self.windowEdit.setRange(1, 1000)
        self.windowEdit.setValue(20)

        # Create horizontal layouts for duration and bar size inputs
        durationLayout = qt.QHBoxLayout()
        durationLayout.addWidget(self.countEdit)
        durationLayout.addWidget(self.unitEdit)

        barSizeLayout = qt.QHBoxLayout()
        barSizeLayout.addWidget(self.barSizeNum)
        barSizeLayout.addWidget(self.barSizeUnit)

        # Create main layout and add widgets
        layout = qt.QFormLayout(self)
        layout.addRow('Duration:', durationLayout)
        layout.addRow('Bar Size:', barSizeLayout)
        layout.addRow(self.useRTHCheckBox)
        layout.addRow(self.addBandCheckBox)
        layout.addRow('Band Window:', self.windowEdit)

        self.setLayout(layout)

    def getSettings(self):
        durationStr = f"{self.countEdit.value()} {self.unitEdit.currentText()}"

        convert = {'S': 'secs', 'Mi': 'mins', 'H': 'hours', 'D': 'days', 'W': 'weeks', 'Mo': 'months'}
        bar_interval_num = self.barSizeNum.value()
        bar_size_unit = convert[self.barSizeUnit.currentText()]
        if bar_size_unit in ['mins', 'hours'] and bar_interval_num == 1:
            bar_size_unit = bar_size_unit[:-1]
        barSizeSetting = f"{bar_interval_num} {bar_size_unit}"

        return {
            'durationStr': durationStr,
            'barSizeSetting': barSizeSetting,
            'useRTH': self.useRTHCheckBox.isChecked(),
            'addBand': self.addBandCheckBox.isChecked(),
            'window': self.windowEdit.value()
        }
