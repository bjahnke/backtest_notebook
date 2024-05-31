from dataclasses import dataclass
import sys
import os
from typing import List

from utils import *

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

@dataclass
class Tab:
    title: str
    model: QTabWidget



class PandasModel(QAbstractTableModel):
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

    @classmethod
    def create_table_view(cls, data):
        model = cls(data)
        view = QTableView()
        view.setSortingEnabled(True)
        view.setModel(model)
        return view


class CustomDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        # Add any additional custom painting here if needed


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)


def create_tab_widget(tab_data: List[Tab]):

    tab_widget = QTabWidget()

    for tab in tab_data:
        tab_widget.addTab(tab.model, tab.title)

    return tab_widget



def market_trend_analysis_app(title, tabs: List[Tab]):
    app = QApplication(sys.argv)
    window = QMainWindow()

    window.setWindowTitle(title)

    window_tabs = create_tab_widget(tabs)

    window.setCentralWidget(window_tabs)

    window.show()
    app.exec()


def create_market_display(tabs):
    """
    create the market view tabs 
    each tab has one table for each market related view
        - Market Overview (regime analysis by sector)
        - Sub industry analysis
        - sub industry with mapping to sector
        - analysis of all constituents
    """
    layout = QVBoxLayout()

    data_label = QLabel("Market Data Table")
    layout.addWidget(data_label)

    table_views = self.create_table_views(self.market_views)

    market_tab = MarketView(table_views)
    market_tab.setLayout(layout)
    return market_tab




def create_asset_view():
    qwidget = QWidget()



def main():
    
    market_views = Market.market_analysis_macro(os.getenv('NEON_DB_CONSTR'))
    market_tabs = []
    for (title, data) in market_views:
        market_tabs.append(Tab(title=title, model=PandasModel.create_table_view(data)))

    market_trend_analysis_app(
        title='Market Trend Analysis',
        children=[
            Tab(
                title='Market View', 
                children=create_market_display(market_tabs)
            ),
            Tab(
                title='Asset View', 
                model=Model()
            )
        ]
        tabs=[
            Tab(
                title='Market View', 
                model=create_market_display(market_tabs)
            ),
            Tab(
                title='Asset View', 
                model=Model()
            )
        ]
    )




if __name__ == '__main__':
    main()