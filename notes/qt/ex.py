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


@dataclass
class View:
    title: str
    view: Any

from PyQt6.QtWidgets import QApplication, QLineEdit, QVBoxLayout, QWidget, QTabWidget, QTableView
from PyQt6.QtCore import QSortFilterProxyModel
from PyQt6.QtGui import QStandardItemModel, QStandardItem


def f():
    pass
    # if title in ['Sector Overview', 'Sub Industry Overview']:
    # if False:
    #     # Create a new widget and layout for this tab
    #     tab_widget = QWidget()
    #     tab_layout = QVBoxLayout()

    #     # Create the table and add it to the layout
    #     table_view = create_table_view(data)
    #     tab_layout.addWidget(table_view)

    #     # Create the plot and add it to the layout
    #     for sector_name in market_data.abs.sector.columns:
    #         plot_widget = SectorPlotWidget(
    #             bench=market_data.benchmark,
    #             abs_sector=market_data.abs.sector,
    #             rel_sector=market_data.rel.sector,
    #             col=sector_name
    #         )
    #         tab_layout.addWidget(plot_widget)

    #     # Set the layout for the tab widget and add it to the tab
    #     tab_widget.setLayout(tab_layout)
    #     self.tab_widget.addTab(tab_widget, title)
    # else:

class MarketView(QWidget):
    def __init__(self, market_data: AbsRelRegimeView, parent=None):
        super().__init__(parent)

        self.tab_widget = self.__class__.init_tab_widget(market_data, self.filter_table_hof)

        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)

        self.setLayout(layout)

    def filter_table_hof(self, index):
        def filter_table(query):
            widget = self.tab_widget.widget(index)
            for child in widget.children():
                if isinstance(child, QTableView):
                    model = child.model().sourceModel()
                    if isinstance(model, PandasModel):
                        try:
                            filtered_data = model._original_data.query(query)
                        except Exception as e:
                            filtered_data = model._original_data
                            
                        model.update_data(filtered_data)
                    break
        return filter_table

    @staticmethod
    def init_tab_widget(market_data, filter_function):
        """
        configure tabs with data and filter features
        """
        tab_widget = QTabWidget()
        for i, (title, data) in enumerate(market_data.overviews):
            # Create the model
            layout = QVBoxLayout()
            
            filter_field = QLineEdit()
            filter_field.setPlaceholderText("Enter filter query")
            filter_field.textChanged.connect(filter_function(i))
            layout.addWidget(filter_field)
            
            table_view = QTableView()
            table_view.setSortingEnabled(True)
            sort_filter_model = QSortFilterProxyModel()
            table_view.setModel(sort_filter_model)
            sort_filter_model.setSourceModel(PandasModel(data))
            layout.addWidget(table_view)

            widget = QWidget()
            widget.setLayout(layout)
            tab_widget.addTab(widget, title)
        return tab_widget

# class MarketView(QWidget):
#     def __init__(self, market_data: AbsRelRegimeView, parent=None):
#         super(MarketView, self).__init__(parent)

#         self.tab_widget = QTabWidget()

#         for (title, data) in market_data.overviews:

#             table_view = create_table_view(data)
#             self.tab_widget.addTab(table_view, title)

#         layout = QVBoxLayout()
#         layout.addWidget(self.tab_widget)

#         self.setLayout(layout)


class PandasModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data
        self._original_data = data.copy()
        self.sort_column = None
        self.sort_order = Qt.SortOrder.AscendingOrder

    def reset_data(self):
        self.beginResetModel()
        self._data = self._original_data
        self.endResetModel()

    def update_data(self, data):
        self.beginResetModel()
        self._data = data
        self.endResetModel()

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
        column_data = self._original_data.iloc[:, column]
        normalized_value = (value - column_data.min()) / (column_data.max() - column_data.min())
        # Get the RGB values from the RdYlGn colormap
        rgb = plt.get_cmap('RdYlGn')(normalized_value)[:3]
        # Convert the RGB values to be between 0 and 255
        rgb = [int(x * 255) for x in rgb]
        # Avoid black color
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


class MainWindow(QMainWindow):
    """
    Main window class which builds the GUI content for all tabs
    """
    def __init__(self, title, tabs):
        super().__init__()
        self.setWindowTitle(title)

        self.tabs = QTabWidget()

        for tab in tabs:
            self.tabs.addTab(tab.view, tab.title)

        self.setCentralWidget(self.tabs)

        
    # def create_market_view(self):
    #     """
    #     create the market view tabs 
    #     each tab has one table for each market related view
    #      - Market Overview (regime analysis by sector)
    #      - Sub industry analysis
    #      - sub industry with mapping to sector
    #      - analysis of all constituents
    #     """
    #     layout = QVBoxLayout()

    #     data_label = QLabel("Market Data Table")
    #     layout.addWidget(data_label)

    #     table_views = self.create_table_views(self.market_views)

    #     market_tab = MarketView(table_views)
    #     market_tab.setLayout(layout)
    #     return market_tab
    

    # @staticmethod
    # def create_table_views(data_items):
    #     """
    #     Create a table view for each data item in the list
    #     """
    #     table_views = []
    #     for (title, data) in data_items:
    #         table_view = QTableView()
    #         table_model = PandasModel(data)
    #         table_view.setSortingEnabled(True)
    #         table_view.setModel(table_model)
    #         table_views.append((title, table_view))
    #     return table_views

    # def create_asset_view(self):
    #     return AssetView()

    # def plot_data(self, data, canvas):
    #     canvas.axes.cla()
    #     data.plot(ax=canvas.axes)
    #     canvas.draw()

    # def refresh_data(self, data, canvas):
    #     # Placeholder for refresh logic
    #     print("Data refreshed")
    #     self.plot_data(data, canvas)

    # def export_data(self, data):
    #     # Placeholder for export logic
    #     print("Data exported")


class PlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Create the canvas for the plot
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)

        # Create a vertical box layout and add the canvas to it
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)

        # Set the layout to the QWidget
        self.setLayout(layout)


class AssetPlotWidget(PlotWidget):
    def __init__(self, _stock_data, title, entries=False, secondary_y=None, style_map=None, parent=None):
        super().__init__(parent)
        self.plot(_stock_data, title, entries, secondary_y, style_map)

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


class SectorPlotWidget(PlotWidget):
    def __init__(self, bench, abs_sector, rel_sector, col, parent=None):
        super().__init__(parent)
        self.plot(bench, abs_sector, rel_sector, col)

    def plot(self, bench, abs, rel, col):
        plot_sector_on_bench(self.canvas, bench, rel, abs, col)


class AssetView(QWidget):  # Replace with your actual class name
    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)
        input_labels = [
            'Symbol',
            'Interval',
            'Data Source'
        ]

        self.input_fields = {}

        self.asset_tab = self.create_asset_view(input_labels)
        layout = QVBoxLayout()
        layout.addWidget(self.asset_tab)
        self.setLayout(layout)

    def create_input_field(self, label):
        line_edit = QLineEdit()
        line_edit.setMaximumWidth(200)  # Set maximum width
        return QLabel(f"{label}:"), line_edit

    def create_asset_view(self, input_labels):
        asset_tab = QWidget()
        layout = QVBoxLayout()

        # Form layout for input fields
        form_layout = QFormLayout()

        # Create input fields based on provided labels
        for label in input_labels:
            lbl, le = self.create_input_field(label)
            self.input_fields[label] = le
            form_layout.addRow(lbl, le)

        # Submit button
        submit_button = QPushButton('Submit')
        submit_button.clicked.connect(self.fetch_and_plot_data)
        submit_button.setMaximumWidth(200)  # Set maximum width

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
        _symbol = self.input_fields['Symbol'].text()
        _interval = self.input_fields['Interval'].text()
        _data_source = self.input_fields['Data Source'].text() if self.input_fields['Data Source'].text() else 'yahoo'

        stock, regime, peak, fc = get_stock_data(_symbol, _interval, _data_source, os.environ.get('NEON_DB_CONSTR'))
        _absolute_stock_data, _relative_stock_data = setup_trend_view_graph(stock, regime, peak, fc)

        # Remove existing plot widgets if they exist
        if hasattr(self, 'abs_plot_widget'):
            self.layout().removeWidget(self.abs_plot_widget)
            self.abs_plot_widget.deleteLater()
        if hasattr(self, 'rel_plot_widget'):
            self.layout().removeWidget(self.rel_plot_widget)
            self.rel_plot_widget.deleteLater()

        # Create the plot widgets and add them to the layout
        self.abs_plot_widget = AssetPlotWidget(_absolute_stock_data, "Absolute Data")
        self.layout().addWidget(self.abs_plot_widget)

        self.rel_plot_widget = AssetPlotWidget(_relative_stock_data, "Relative Data")
        self.layout().addWidget(self.rel_plot_widget)


def create_market_view(market_data: AbsRelRegimeView):
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

    market_tab = MarketView(market_data)
    market_tab.setLayout(layout)
    return market_tab

def create_table_view(data) -> QTableView:
    """
    Create a table view for each data item in the list
    """
    table_view = QTableView()
    table_model = PandasModel(data)
    table_view.setSortingEnabled(True)
    table_view.setModel(table_model)
    table_view.setModel(QSortFilterProxyModel())

    return table_view

def create_asset_view(self):
    return AssetView()


import pickle
import os

def main(load_from_pickle=False):
    if load_from_pickle:
        with open('market_data.pkl', 'rb') as f:
            market_data = pickle.load(f)
    else:
        market_data = main_market_scan(
            benchmark_symbol='SPY',
            interval='1d',
            source='yahoo',
            db_url=os.getenv('NEON_DB_CONSTR')
        )
        with open('market_data.pkl', 'wb') as f:
            pickle.dump(market_data, f)

    app = QApplication(sys.argv)
    window = MainWindow(
        title='Pandas Data and Matplotlib Plot',
        tabs=[
            View(
                title='Market View', 
                view=create_market_view(market_data)),
            View(
                title='Asset View', 
                view=AssetView())
        ]
    )
    window.show()
    app.exec()

if __name__ == '__main__':
    main(load_from_pickle=True)
    """
    Main application:
        Tab Market View:
            Tab (Sector):
                HeatGraph Sector View
                Plot Sector Views 
            Tab (Sub Industry):
                HeatGraph Sub Industry View
            Tab (Sub Industry Mapping):
                HeatGraph Sub Industry Mapping
            Tab (Constituents):
                Table Constituents
        Tab Asset View:
            Display:
                Form (Symbol, Interval, Data Source)
                onSubmit fetch data and plot
    """
