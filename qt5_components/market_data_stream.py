import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from ib_insync import *
import PyQt5.QtWidgets as qt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import pandas as pd
from .sidebar import Sidebar
from .stream_settings_form import StreamingSettingsForm
from notes.strategy.indicators import TradingRange

class MarketDataTab(qt.QWidget):
    def __init__(self, ib, parent=None):
        super().__init__(parent)
        self.ib = ib

        # Create the sidebar
        self.sidebar = Sidebar(settingsForm=StreamingSettingsForm, parent=self)
        self.sidebar.startButton.clicked.connect(self.startStreaming)

        # Create a matplotlib figure and canvas
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)

        # Set a minimum size for the canvas
        self.canvas.setMinimumSize(600, 400)

        # Create layout and add widgets
        mainLayout = qt.QHBoxLayout(self)
        mainLayout.addWidget(self.sidebar)
        mainLayout.addWidget(self.canvas)

        self.setLayout(mainLayout)

        self.bars = None
        self.title = ''
        self.bandAdder = None

    def startStreaming(self):
        text = self.sidebar.edit.text()
        settings = self.sidebar.getSettings()


        
        if text:
            contract = eval(text)
            if contract and self.ib.qualifyContracts(contract):
                # Request historical data
                if self.bars is not None:
                    self.ib.cancelHistoricalData(self.bars)
                    self.bars = None
                    bars = self.ib.reqHistoricalData(
                        contract,
                        endDateTime='',
                        durationStr=settings['durationStr'],
                        barSizeSetting=settings['barSizeSetting'],
                        whatToShow='TRADES',
                        useRTH=settings['useRTH'],
                        formatDate=1
                    )
                    self.updatePlot(bars, True, settings)
                self.title = self.sidebar.edit.text()
                self.bars = self.ib.reqHistoricalData(
                    contract,
                    endDateTime='',
                    durationStr=settings['durationStr'],
                    barSizeSetting=settings['barSizeSetting'],
                    whatToShow='TRADES',
                    useRTH=settings['useRTH'],
                    formatDate=1,
                    keepUpToDate=True
                )
                self.bars.updateEvent += lambda bars, hasNewBar: self.updatePlot(bars, hasNewBar, settings)
        
    def updatePlot(self, bars, hasNewBar, settings):
        if hasNewBar:
            df = util.df(bars)

            # Clear the previous content of the figure but keep its size
            self.canvas.figure.clear()

            # Create the new plot on the existing figure
            ax = self.canvas.figure.add_subplot(111)
            # Add bands to the price data if the checkbox is checked
            if settings['addBand']:
                self.bandAdder = TradingRange(window=settings['window'])
                self.bandAdder.update(df.close)
                self.bandAdder.plot(ax=ax, linestyle='--', linewidth=1)

            self.barplot(df, ax=ax, title=self.title)


            # Plot the bands if they were added
            if self.bandAdder:
                self.bandAdder.plot(ax)
            
            # Redraw the canvas with the updated plot
            self.canvas.draw()

    def resizeFigure(self, event=None):
        # Get the size of the canvas in pixels
        width, height = self.canvas.get_width_height()
        
        # Convert the size from pixels to inches (DPI is dots per inch)
        dpi = self.canvas.figure.dpi
        self.canvas.figure.set_size_inches(max(width / dpi, 6), max(height / dpi, 4))
        self.canvas.draw()

    def resizeEvent(self, event):
        self.resizeFigure(event)
        self.adjustSidebarWidth()
        super().resizeEvent(event)

    def adjustSidebarWidth(self):
        # Set the maximum width of the sidebar to 25% of the parent container's width
        parent_width = self.width()
        max_sidebar_width = int(parent_width * 0.25)
        self.sidebar.setMaximumWidth(max_sidebar_width)

    def barplot(self, bars, ax=None, title='', upColor='blue', downColor='red'):
        if isinstance(bars, pd.DataFrame):
            ohlcTups = [
                tuple(v) for v in bars[['open', 'high', 'low', 'close']].values]
        elif bars and hasattr(bars[0], 'open_'):
            ohlcTups = [(b.open_, b.high, b.low, b.close) for b in bars]
        else:
            ohlcTups = [(b.open, b.high, b.low, b.close) for b in bars]

        if ax is None:
            fig, ax = plt.subplots()
        ax.set_title(title)
        ax.grid(True)

        for n, (open_, high, low, close) in enumerate(ohlcTups):
            if close >= open_:
                color = upColor
                bodyHi, bodyLo = close, open_
            else:
                color = downColor
                bodyHi, bodyLo = open_, close
            line = Line2D(
                xdata=(n, n),
                ydata=(low, bodyLo),
                color=color,
                linewidth=1)
            ax.add_line(line)
            line = Line2D(
                xdata=(n, n),
                ydata=(high, bodyHi),
                color=color,
                linewidth=1)
            ax.add_line(line)
            rect = Rectangle(
                xy=(n - 0.3, bodyLo),
                width=0.6,
                height=bodyHi - bodyLo,
                edgecolor=color,
                facecolor=color,
                alpha=0.4,
                antialiased=True
            )
            ax.add_patch(rect)

        ax.autoscale_view()

class BandAdder:
    def __init__(self, window=20):
        self.window = window
        self.bands = None

    def add_data(self, price):
        price['rolling_max'] = price.close.rolling(window=self.window).max()
        price['rolling_min'] = price.close.rolling(window=self.window).min()
        price['trading_range'] = (price.rolling_max - price.rolling_min)
        price['trading_range_lo_band'] = price.rolling_min + price.trading_range * .61
        price['trading_range_hi_band'] = price.rolling_min + price.trading_range * .40
        price['band_24'] = price.rolling_min + price.trading_range * .24
        price['band_76'] = price.rolling_min + price.trading_range * .76
        self.bands = price[['rolling_max', 'rolling_min', 'trading_range_lo_band', 'trading_range_hi_band', 'band_24', 'band_76']]
        return price

    def plot(self, ax):
        if self.bands is not None:
            self.bands.plot(ax=ax, linestyle='--', linewidth=1)
            ax.grid(True)