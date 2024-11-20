import pytest
from notes.strategy.indicators import TradingRange
from notes.strategy.strategies import TradingRangeBreakout
import yfinance as yf
import pickle
import os

def save_new_test_data(symbol):
    """download test data and save locally"""
    data = yf.download(symbol)
    assert not data.empty
    # Save data to pickle file
    with open(f'{symbol}.pickle', 'wb') as file:
        pickle.dump(data, file)
    
    return data

def get_data(symbol):
    # Check if pickle file exists
    if os.path.exists(f'{symbol}.pickle'):
        # Load data from pickle file
        with open(f'{symbol}.pickle', 'rb') as file:
            data = pickle.load(file)
    else:
        data = save_new_test_data(symbol)

    return data

@pytest.fixture
def price_data():
    return get_data('TSLA')

class TestTradingRange:

    def test_trading_range_assertions(self):
        with pytest.raises(AssertionError):
            # Test when low band is below 0
            TradingRange(-1, 0.5)

        with pytest.raises(AssertionError):
            # Test when high band is above 1
            TradingRange(0.5, 1.5)

        with pytest.raises(AssertionError):
            # Test when high band is less than low band
            TradingRange(0.6, 0.8)

    def test_bands_not_nan(self, price_data):
        """Test that the bands are not NaN after calculating"""
        tr = TradingRange(0.61, 0.40)
        tr.update(price_data.Close)
        tail = tr.value.tail()
        assert not tail.upper.isna().any()
        assert not tail.lower.isna().any()

    def test_update(self, price_data):
        tr = TradingRange(10, 20)
        tr.update(price_data['Close'])
        assert tr.current_value == price_data['Close'].iloc[-1]

    def test_trading_range_creation(self):
        tr = TradingRange(10, 20)
        assert tr.low_band == 10
        assert tr.high_band == 20

    def test_trading_range_update(self):
        tr = TradingRange(10, 20)
        tr.update(15)
        assert tr.low_band == 10
        assert tr.high_band == 20
        assert tr.current_value == 15

    def test_trading_range_contains(self):
        tr = TradingRange(10, 20)
        assert tr.contains(15)
        assert not tr.contains(5)
        assert not tr.contains(25)

class TestTradingRangeBreakout:
    def test_trading_range_no_nan(self, price_data):
        trb = TradingRangeBreakout(.6, .4)
        trb.update(price_data.Close)
        assert not trb.value.tail().isna().any()

    def test_trading_range_breakout_creation(self):
        trb = TradingRangeBreakout(0.1, 0.9, window=10)
        assert trb.high_band_pct == 0.1
        assert trb.low_band_pct == 0.9
        assert trb.window == 10

    def test_trading_range_breakout_update(self):
        trb = TradingRangeBreakout(0.1, 0.9, window=10)
        trb.update(15)
        assert trb.high_band_pct == 0.1
        assert trb.low_band_pct == 0.9
        assert trb.window == 10
        assert trb.current_value == 15

    def test_trading_range_breakout_contains(self):
        trb = TradingRangeBreakout(0.1, 0.9, window=10)
        assert trb.contains(15)
        assert not trb.contains(5)
        assert not trb.contains(25)


if __name__ == '__main__':
    r = get_data('TSLA')
    print(r)