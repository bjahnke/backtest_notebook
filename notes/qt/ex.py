import sys
import os
import dotenv
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

dotenv.load_dotenv()


class Market:
    def market_analysis_macro(source_connection: str):
        return Market.market_trend_analysis(*Market.load_tables(source_connection))

    def load_tables(source_connection: str):
        regime_table = pd.read_sql(f'SELECT * FROM regime', source_connection)
        stock_table = pd.read_sql("SELECT id, symbol, is_relative FROM stock where stock.data_source = 'yahoo' and stock.market_index = 'SPY'", source_connection)
        web_df = pd.read_sql("SELECT * FROM stock_info", source_connection)
        return regime_table, stock_table, web_df


    def market_trend_analysis(regime_table, stock_table, web_df):
        regime_cols = ['fc', 'fc_r', 'bo', 'bo_r', 'sma', 'sma_r', 'tt', 'tt_r']
        
        regime_table = stock_table.merge(regime_table, left_on='id', right_on='stock_id', how='inner')
        max_end_indices = regime_table.groupby(['symbol', 'type', 'is_relative'])['end'].idxmax()

        filtered_df = regime_table.loc[max_end_indices, ['symbol', 'type', 'is_relative', 'end', 'rg']].reset_index(drop=True)
        filtered_df['type'] = filtered_df['type'] + filtered_df['is_relative'].replace({True: '_r', False: ''})

        regime_overview = filtered_df.pivot(index=['symbol'], columns='type', values='rg').reset_index()
        regime_overview = regime_overview[['symbol'] + regime_cols]
        regime_overview['delta'] = 0
        regime_pairs = [('bo', 'bo_r'), ('fc', 'fc_r'), ('sma', 'sma_r'), ('tt', 'tt_r')]
        for absolute, relative in regime_pairs:
            regime_overview[absolute] = regime_overview[absolute].fillna(regime_overview[relative])
            regime_overview[relative] = regime_overview[relative].fillna(regime_overview[absolute])
            regime_overview[absolute] = regime_overview[absolute].fillna(0)
            regime_overview[relative] = regime_overview[relative].fillna(0)
            delta = (regime_overview[relative] - regime_overview[absolute]) / 2
            regime_overview['delta'] += delta

        regime_overview['delta'] /= len(regime_pairs)
        regime_overview['score'] = regime_overview[regime_cols].sum(axis=1)
        full_regime_overview = regime_overview.merge(web_df[['symbol', 'GICS Sector', 'GICS Sub-Industry']], left_on='symbol', right_on='symbol')
        regime_overview = full_regime_overview.drop(columns=['symbol'])

        groupby_cols = ['score', 'delta'] + regime_cols
        sort_key = ['GICS Sector']
        sector_overview = regime_overview.groupby(sort_key)[groupby_cols].mean().sort_values(by='score')

        groupby_cols = ['score', 'delta'] + regime_cols
        sort_key = ['GICS Sub-Industry']
        sub_industry_overview = regime_overview.groupby(sort_key)[groupby_cols].mean().sort_values(
            by= 'score')
        
        groupby_cols = ['score', 'delta'] + regime_cols
        sort_key = ['GICS Sector','GICS Sub-Industry']

        sector_sub_sector_overview = regime_overview.groupby(sort_key)[groupby_cols].mean().sort_values(
            by= ['GICS Sector','score'])
        
        full_regime_overview = full_regime_overview[['symbol', 'delta', 'score', 'GICS Sector', 'GICS Sub-Industry']]
        
        return (
            ('Sector Overview', sector_overview), 
            ('Sub Industry Overview', sub_industry_overview), 
            ('Sub Sector/Sector Overview', sector_sub_sector_overview), 
            ('Full Market Overview', full_regime_overview),
        )


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

        # refresh_button = QPushButton("Refresh")
        # refresh_button.clicked.connect(lambda: self.refresh_data(self.sector_overview, canvas))
        # layout.addWidget(refresh_button)

        # export_button = QPushButton("Export")
        # export_button.clicked.connect(lambda: self.export_data(self.sector_overview))
        # layout.addWidget(export_button)
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
        asset_tab = QWidget()
        layout = QVBoxLayout()

        data_label = QLabel("Asset Data Table")
        layout.addWidget(data_label)

        plot_label = QLabel("Asset Data Plot")
        layout.addWidget(plot_label)

        asset_tab.setLayout(layout)
        return asset_tab

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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
