import pickle
import sys
from PyQt6.QtCore import Qt, QAbstractTableModel
from PyQt6.QtWidgets import QApplication, QMainWindow, QTableView, QFileDialog, QMenuBar, QStatusBar, QVBoxLayout, QWidget
from PyQt6.QtGui import QIcon, QAction
import pandas as pd

from dataclasses import dataclass
import sys
import os
from typing import List

from utils import *
from regime_scan import AbsRelRegimeView, main_market_scan

import pandas as pd
import matplotlib.pyplot as plt
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTableView, QPushButton, QLabel, QTabWidget
from PyQt6.QtCore import QAbstractTableModel, Qt
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtWebEngineWidgets import QWebEngineView
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QTabWidget, QWidget, QVBoxLayout
from PyQt6.QtWidgets import QLineEdit, QPushButton, QLabel, QVBoxLayout, QWidget
from PyQt6.QtWidgets import QFormLayout, QGroupBox

# data = {'col1': ['1', '2', '3'], 'col2': ['4', '5', '6'], 'col3': ['7', '8', '9']}
# head807677 = ['Date', 'Heure', 'OK-NOK', 'Detect', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7']
# head801986 = ['Date', 'Heure', 'Ok-NOK', 'Detect', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8']
# head = head807677

class PandasModel(QAbstractTableModel):
    """
    Class to populate a table view with a pandas dataframe
    """
    def __init__(self, data):
        super().__init__()
        self._data = data
        self._original_data = data.copy()
        self.sort_column = None
        self.sort_order = Qt.SortOrder.AscendingOrder

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid():
            if role == Qt.ItemDataRole.DisplayRole:
                value = self._data.iloc[index.row(), index.column()]
                if isinstance(value, (int, float)):
                    return "{:.1g}".format(value)
                else:
                    return str(value)
            elif role == Qt.ItemDataRole.BackgroundRole:
                value = self._data.iloc[index.row(), index.column()]
                if isinstance(value, (int, float)):
                    # Apply gradient coloring based on value
                    color = self.get_color(value, index.column())
                    return QBrush(color)
                else:   
                    return str(value)
        return None

    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._data.columns[section])
            if orientation == Qt.Orientation.Vertical:
                return str(self._data.index[section])
        return None

    def get_color(self, value, column):
        # Normalize the value to be between 0 and 1
        normalized_value = (value - self._data.iloc[:, column].min()) / (self._data.iloc[:, column].max() - self._data.iloc[:, column].min())
        # Get the RGB values from the RdYlGn colormap
        rgb = plt.get_cmap('RdYlGn')(normalized_value)[:3]
        # Convert the RGB values to be between 0 and 255
        rgb = [int(x * 255) for x in rgb]
        return QColor(*rgb)

    def sort(self, column, order):
        self.layoutAboutToBeChanged.emit()
        self.sort_column = column
        self.sort_order = order

        if order == Qt.SortOrder.AscendingOrder:
            self._data = self._data.sort_values(self._data.columns[column], ascending=True)
        else:
            self._data = self._data.sort_values(self._data.columns[column], ascending=False)

        self.layoutChanged.emit()

class QMT(QMainWindow):
    def __init__(self, parent=None):
        super(QMT, self).__init__(parent)
        self.view = QTableView(self)
        self.header = self.view.horizontalHeader()
        self.header.sectionClicked.connect(self.headerClicked)
        self.setCentralWidget(self.view)
        self.view.show()
        self.initUI()

    def initUI(self):
        exitAction = QAction(QIcon('exit.png'), '&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(QApplication.instance().quit)

        self.showDialog()

        self.setStatusBar(QStatusBar(self))
        self.setGeometry(200, 200, 400, 400)
        self.setWindowTitle('Menubar')
        self.show()

    def showDialog(self):
        data = self.get_data()
        self.model = PandasModel(data)
        self.view.setModel(self.model)
        self.view.show()

    def get_data(self):
        with open('market_data.pkl', 'rb') as f:
            data = pickle.load(f)
        return data.overviews[0][1]
    
    def headerClicked(self, logicalIndex):
        data = self.model._data
        self.order = self.header.sortIndicatorOrder()
        data.sort(data.columns[logicalIndex],
                        ascending=self.order,inplace=True)
        self.model = PandasModel(data)
        self.view.setModel(self.model)
        self.view.update()

def main(args):
    app = QApplication(args)
    win = QMT()
    win.show()
    app.exec()

if __name__ == "__main__":
    main(sys.argv)
