from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from typing import Optional, List
from scripts.update_db import Stock, Regime, Peak, StockData  # Import your model classes
import dotenv
import os
dotenv.load_dotenv()

from sqlalchemy.orm import Session
from sqlalchemy.sql import func
import src.position_calculation as pc

@dataclass
class EntryData:
    current_signal: Peak
    valid_stop_swings: List[Peak]

    def parse_entry_data(self):
        cost = self.current_signal.en_px
        trail = self.current_signal.st_px
        stop_swing = self.valid_stop_swings[0]
        stop = stop_swing.st_px
        # target = float(pc.TwoLegTradeEquation.Solve.price(stop, cost, fraction))
        # quantity = float(pc.PositionSize.Solve.quantity(stop, cost, risk))
        return {
            'cost': cost,
            'trail': trail,
            'stop': stop,
        }




def get_entry_data(session: Session, stock_id: int) -> dict:
    """
    Get entry data for a given stock ID.

    :param session: SQLAlchemy session object
    :param stock_id: ID of the stock
    :return: Dictionary containing entry data
    """
    # Subquery for the latest regime start
    current_regime_subq = session.query(
        Regime.stock_id,
        func.max(Regime.start).label('latest_start')
    ).filter(
        Regime.stock_id == stock_id,
        Regime.type == 'fc'
    ).group_by(Regime.stock_id).subquery('current_regime')

    # Subquery for the last stock data
    last_stock_data_subq = session.query(
        StockData.stock_id,
        func.max(StockData.bar_number).label('max_bar_number')
    ).filter(
        StockData.stock_id == stock_id
    ).group_by(StockData.stock_id).subquery('last_stock_data')

    # Main query to fetch peaks, regime, and last stock data
    peaks_and_regime_and_stock_data = session.query(
        Peak,
        current_regime_subq.c.latest_start,
        StockData
    ).outerjoin(
        current_regime_subq, Peak.stock_id == current_regime_subq.c.stock_id
    ).outerjoin(
        last_stock_data_subq, Peak.stock_id == last_stock_data_subq.c.stock_id
    ).outerjoin(
        StockData, (StockData.stock_id == last_stock_data_subq.c.stock_id) &
                   (StockData.bar_number == last_stock_data_subq.c.max_bar_number)
    ).filter(
        Peak.stock_id == stock_id,
        Peak.lvl >= 2
    ).all()

    # Initialize dictionary to store entry data
    entry_data = {}

    # Processing the query results to find the current signal and valid stop swings
    for peak, latest_start, _ in peaks_and_regime_and_stock_data:
        if peak.start >= latest_start:
            entry_data['current_signal'] = peak
            break

    if 'current_signal' in entry_data:
        current_signal = entry_data['current_signal']
        entry_data['valid_stop_swings'] = [
            peak for peak, _, _ in peaks_and_regime_and_stock_data
            if peak.start < current_signal.start and
               peak.end < current_signal.end and
               (peak.st_px - current_signal.st_px) * current_signal.type <= 0
        ]

    return entry_data


if __name__ == '__main__':
    _engine = create_engine(os.environ.get('NEON_DB_CONSTR'))
    with Session(_engine) as session:
        stock_id = 1  # Example stock ID
        entry_data = get_entry_data(session, stock_id)
    print('done')
        # entry_data now contains 'current_signal', 'valid_stop_swings', and 'estimated_cost'
    # current_regime = regime.loc[regime['type'] == 'fc'].iloc[-1]
    # filtered_peaks = peak.loc[
    #     (peak['lvl'] >= 2) &
    #     (peak['type'] == current_regime.rg)
    #     ].copy()
    # current_signal = filtered_peaks.loc[
    #         (peak.start >= current_regime.start)
    #     ].iloc[-1]
    #
    # # previous swings that are lower/higher and exist before the current signal
    # _valid_stop_swings = filtered_peaks.loc[
    #     (filtered_peaks['start'] < current_signal.start) &
    #     (filtered_peaks['end'] < current_signal.end) &
    #     ((filtered_peaks.st_px - current_signal.st_px) * current_signal.type <= 0)
    #     ]
    # trail = current_signal.st_px * multiple
    # stop = _valid_stop_swings.loc[(_valid_stop_swings.lvl == 2)].iloc[-1].st_px * multiple
    # estimated_cost = stock_data.iloc[-1].close * multiple

    """
    for each stock.id, I want to get the entry data: The current signal will be the peak row where peak.type = (regime.rg where regime.type = 'fc' and ma and where peak., peak.lvl = 2,. 
    The valid stop swings will be the previous peaks that are lower/higher than the current signal and exist before the current signal. 
    The entry price will be the current signal's start price. The stop loss will be the lowest/highest price of the valid stop swings. 
    The trailing stop will be the lowest/highest price of the valid stop swings. The quantity will be the current signal's level.
    """