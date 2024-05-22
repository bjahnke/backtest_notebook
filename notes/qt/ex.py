import sys
import os

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

class SectorOverview(QWidget):
    pass


class MarketView(QWidget):
    def __init__(self, widgets_pairs, parent=None):
        super(MarketView, self).__init__(parent)

        self.tab_widget = QTabWidget()

        for (title, widget) in widgets_pairs:
            self.tab_widget.addTab(widget, title)

        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)

        self.setLayout(layout)



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

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Pandas Data and Matplotlib Plot')

        self.market_views = Market.market_analysis_macro(os.getenv('NEON_DB_CONSTR'))

        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_market_view(), "Market View")
        self.tabs.addTab(self.create_asset_view(), "Asset View")

        self.setCentralWidget(self.tabs)

        
    def create_market_view(self):
        layout = QVBoxLayout()

        data_label = QLabel("Market Data Table")
        layout.addWidget(data_label)

        table_views = self.create_table_views(self.market_views)

        market_tab = MarketView(table_views)
        market_tab.setLayout(layout)
        return market_tab
    

    @staticmethod
    def create_table_views(data_items):
        table_views = []
        for (title, data) in data_items:
            table_view = QTableView()
            table_model = PandasModel(data)
            table_view.setSortingEnabled(True)
            table_view.setModel(table_model)
            table_views.append((title, table_view))
        return table_views

    def create_asset_view(self):
        return AssetView()

    def plot_data(self, data, canvas):
        canvas.axes.cla()
        data.plot(ax=canvas.axes)
        canvas.draw()

    def refresh_data(self, data, canvas):
        # Placeholder for refresh logic
        print("Data refreshed")
        self.plot_data(data, canvas)

    def export_data(self, data):
        # Placeholder for export logic
        print("Data exported")



class AssetPlotWidget(QWidget):
    def __init__(self, _stock_data, title, entries=False, secondary_y=None, style_map=None, parent=None):
        super(AssetPlotWidget, self).__init__(parent)

        # Create the canvas for the plot
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)

        # Call your plot function
        self.plot(_stock_data, title, entries, secondary_y, style_map)

        # Create a vertical box layout and add the canvas to it
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)

        # Set the layout to the QWidget
        self.setLayout(layout)

    def plot(self, _stock_data, title, entries=False, secondary_y=None, style_map=None):
        if secondary_y is None:
            secondary_y = ['fc', 'sma', 'bo', 'tt']
        sd = _stock_data.copy()

        style_map = {
            'close': '-', # line

            'lo3': 'g^', # green up arrow
            'dlo3': 'k^', # black up arrow (white for dark mode)

            'hi3': 'rv', # red down arrow
            'dhi3': 'kv', # black down arrow (white for dark mode)

            'lo2': 'g.', # green dot
            'dlo2': 'k.', # black dot (white for dark mode)

            'hi2': 'r.', # red dot
            'dhi2': 'm.', # magenta dot

            'fc': 'b--', # blue dashed line
            'sma': 'y--', # yellow dashed line
            'bo': 'k--', # black dashed line (white for dark mode)
            'tt': 'c--', # cyan dashed line
            # make fc_val green
            'fc_val': 'y*',
            # make rg_ch_val yellow start
            'rg_ch_val': 'c--',
            'trading_range_lo_band': 'r--',
            'trading_range_hi_band': 'g--',
        }

        if entries:
            if sd.fc.iloc[-1] == 1:
                del style_map['hi2']
                del style_map['dhi2']
                del style_map['hi3']
                del style_map['dhi3']
            else:
                del style_map['lo2']
                del style_map['dlo2']
                del style_map['lo3']
                del style_map['dlo3']

        remove_keys = []
        for key, val in style_map.items():
            if key not in sd.columns:
                remove_keys.append(key)
        for key in remove_keys:
            style_map.pop(key)

        try:
            ax = self.canvas.axes
            for key, style in style_map.items():
                if key in secondary_y:
                    ax2 = ax.twinx()
                    ax2.plot(sd.index, sd[key], style, label=key)
                    ax2.set_ylabel(key, color=style[0])
                else:
                    ax.plot(sd.index, sd[key], style, label=key)
            ax.set_title(title)
            ax.legend()
            self.canvas.draw()
        except KeyError:
            pass


class AssetView(QWidget):  # Replace with your actual class name
    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)
        self.asset_tab = self.create_asset_view()
        layout = QVBoxLayout()
        layout.addWidget(self.asset_tab)
        self.setLayout(layout)

    def create_asset_view(self):
        asset_tab = QWidget()
        layout = QVBoxLayout()

        # Input fields for symbol and interval
        self.symbol_input = QLineEdit()
        self.symbol_input.setMaximumWidth(200)  # Set maximum width
        self.interval_input = QLineEdit()
        self.interval_input.setMaximumWidth(200)  # Set maximum width

        # Submit button
        submit_button = QPushButton('Submit')
        submit_button.clicked.connect(self.fetch_and_plot_data)
        submit_button.setMaximumWidth(200)  # Set maximum width

        # Form layout for input fields
        form_layout = QFormLayout()
        form_layout.addRow(QLabel("Symbol:"), self.symbol_input)
        form_layout.addRow(QLabel("Interval:"), self.interval_input)

        # Group box for form
        form_group = QGroupBox("Enter Details")
        form_group.setLayout(form_layout)

        layout.addWidget(form_group)
        layout.addWidget(submit_button)

        # Labels for data and plot
        data_label = QLabel("Asset Data Table")
        layout.addWidget(data_label)
        plot_label = QLabel("Asset Data Plot")
        layout.addWidget(plot_label)

        asset_tab.setLayout(layout)
        return asset_tab

    def fetch_and_plot_data(self):
        _symbol = self.symbol_input.text()
        _interval = self.interval_input.text()

        stock, regime, peak, fc = get_stock_data(_symbol, _interval, os.environ.get('NEON_DB_CONSTR'))
        _absolute_stock_data, _relative_stock_data = setup_trend_view_graph(stock, regime, peak, fc)

        # Create the plot widget and add it to the layout
        self.abs_plot_widget = AssetPlotWidget(_absolute_stock_data, "Absolute Data")

        self.layout().addWidget(self.abs_plot_widget)
        self.layout().addWidget(AssetPlotWidget(_relative_stock_data, "Relative Data"))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
