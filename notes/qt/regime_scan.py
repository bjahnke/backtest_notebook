from dataclasses import dataclass
import pandas as pd
import os
import dotenv
dotenv.load_dotenv()
import yfinance


class RegimeDataClient:
    def __init__(self, db_url):
        self.db_url = db_url

    def get_stock_data(self, symbol, interval, source):
        return get_stock_data(symbol, interval, source, self.db_url)
    
    def get_data_by_market(self, market_index, interval, data_source, tables=None):
        return get_data_by_market(market_index, interval, data_source, self.db_url, tables)


def get_stock_data(_symbol, _interval, _source, _neon_db_url):
    q = (
         "select {table}.*, stock.symbol, stock.is_relative "
         "from {table} "
         "left join stock on {table}.stock_id = stock.id "
         f"where stock.symbol = '{_symbol}' "
         f"and stock.interval = '{_interval}' "
         f"and stock.data_source = '{_source}'"
         "{extra}"
    ).format
    
    _stock_data = pd.read_sql(
        q(table='stock_data', extra="order by stock_data.bar_number asc"), con=_neon_db_url)
    _regime_data = pd.read_sql(
        q(table='regime', extra=""), con=_neon_db_url)
    _peak_data = pd.read_sql(
        q(table='peak', extra=""), con=_neon_db_url)
    return _stock_data, _regime_data, _peak_data


def get_data_by_market(_market_index, _interval, data_source, _neon_db_url, tables=None):
    if tables is None:
        tables = ['stock_data', 'regime', 'peak']
    q = (
         "select {table}.*, stock.symbol, stock.is_relative "
         "from {table} "
         "left join stock on {table}.stock_id = stock.id "
         f"where stock.market_index = '{_market_index}' "
         f"and stock.interval = '{_interval}' "
         f"and stock.data_source = '{data_source}'"
         "{extra}"
    ).format
    table_lookup = {
        'stock_data': lambda: pd.read_sql(q(table='stock_data', extra="order by stock_data.bar_number asc"), con=_neon_db_url),
        'regime': lambda: pd.read_sql(q(table='regime', extra=""), con=_neon_db_url),
        'peak': lambda: pd.read_sql(q(table='peak', extra=""), con=_neon_db_url)
    }
    result = [table_lookup[table]() for table in tables]
    return result


class MarketRegimeView:
    """
    contains regime analysis view by sector and sub-industry
    """
    def __init__(self, sector: pd.DataFrame, sub_industry: pd.DataFrame):
        self.sector = sector
        self.sub_industry = sub_industry

    @classmethod
    def build(cls, market_regime: pd.DataFrame, benchmark: pd.DataFrame, market_info: pd.DataFrame):
        sector, sub_sector = cls.group_regime_data(market_regime, market_info)

        return cls(sector, sub_sector)
    
    @staticmethod
    def group_regime_data(market_regime, stock_info):
        agg_market_regime = aggregate_regime(market_regime, how='sum')
        agg_market_regime = add_sector(agg_market_regime, stock_info)
        sector = agg_market_regime.groupby(level='GICS Sector', axis=1).mean()
        sub_industry = agg_market_regime.groupby(level='GICS Sub-Industry', axis=1).mean()
        return sector, sub_industry
    

class AbsRelRegimeView:
    def __init__(self, abs: MarketRegimeView, rel: MarketRegimeView, overviews, benchmark):
        self.abs = abs
        self.rel = rel
        self.overviews = overviews
        self.sector_overview = overviews[0][1]
        self.sub_industry_overview = overviews[1][1]
        self.sector_sub_sector_overview = overviews[2][1]
        self.full_market_overview = overviews[3][1]
        self.benchmark = benchmark
        
    @classmethod
    def build(cls, market_regime: pd.DataFrame, benchmark: pd.DataFrame, market_info: pd.DataFrame):

        abs = MarketRegimeView.build(
                market_regime.loc[market_regime.is_relative == False], 
                benchmark, 
                market_info
            )
        
        rel = MarketRegimeView.build(
                market_regime.loc[market_regime.is_relative == True], 
                benchmark, 
                market_info
            )
        overviews = AbsRelRegimeView.build_regime_overview(market_regime, market_info)
        return cls(abs, rel, overviews, benchmark)

    @staticmethod
    def build_regime_overview(regime_table, web_df):
        regime_cols = ['fc', 'fc_r', 'bo', 'bo_r', 'sma', 'sma_r', 'tt', 'tt_r']
        
        max_end_indices = regime_table.groupby(['symbol', 'type', 'is_relative'])['end'].idxmax()

        filtered_df = regime_table.loc[max_end_indices, ['symbol', 'type', 'is_relative', 'end', 'rg']].reset_index(drop=True)
        filtered_df['type'] = filtered_df['type'] + filtered_df['is_relative'].replace({True: '_r', False: ''})

        regime_overview = filtered_df.pivot(index=['symbol'], columns='type', values='rg').reset_index()
        regime_overview = regime_overview[['symbol'] + regime_cols]
        regime_overview['delta'] = 0
        regime_pairs = [('bo', 'bo_r'), ('fc', 'fc_r'), ('sma', 'sma_r'), ('tt', 'tt_r')]
        
        # if na, use the other value as default, else use 0 to avoid NaN calculations
        for absolute, relative in regime_pairs:
            regime_overview[absolute] = regime_overview[absolute].fillna(regime_overview[relative])
            regime_overview[relative] = regime_overview[relative].fillna(regime_overview[absolute])
            regime_overview[absolute] = regime_overview[absolute].fillna(0)
            regime_overview[relative] = regime_overview[relative].fillna(0)
            regime_overview['delta'] += (regime_overview[relative] - regime_overview[absolute])

        regime_overview['delta'] /= 2

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


def aggregate_regime(_regime_table, by_regime=None, how='mean'):
    regime_types = _regime_table.type.unique()
    if by_regime is None:
        by_regime = regime_types
    # else throw error if by_regime not in regime_types
    elif not set(by_regime).issubset(set(regime_types)):
        raise ValueError(f"by_regime must be a subset of {regime_types}")

    # new df set index using start and end cols of spy_regime as range
    rg_long_table = pd.DataFrame(
        index=pd.RangeIndex(start=_regime_table.start.min(), stop=_regime_table.end.max(), step=1),
        columns=by_regime
    )
    # for each unique symbol in spy_regime, create a new column in spy_rg
    symbol_cols = []
    for _symbol in _regime_table.symbol.unique():
        rgs = _regime_table.loc[_regime_table.symbol == _symbol].copy()
        symbol_rg = rg_long_table.copy()
        for index, row in rgs.iterrows():
            symbol_rg.loc[row.start:row.end, row.type] = row.rg
        # aggregate rg_types by mean

        symbol_cols.append(pd.DataFrame({_symbol: getattr(symbol_rg[by_regime], how)(axis=1)}))
        # rg_long_table[_symbol] = symbol_rg[by_regime].mean(axis=1)
    rg_long_table = pd.concat(symbol_cols, axis=1)
    return rg_long_table


def aggregate_regime_counts(benchmark, bench_regime, by_regime=None):
    pos_counter = lambda x: x == 1
    neg_counter = lambda x: x == -1
    agg_regimes = aggregate_regime(bench_regime.copy(), by_regime)
    regime_counts = pd.DataFrame({
        'pos': agg_regimes.apply(pos_counter).sum(axis=1),
        'neg': agg_regimes.apply(neg_counter).sum(axis=1)
    })
    # merge counts on spy where count index = spy.bar_number
    # merge counts with spy on index
    regime_counts = benchmark[['close']].merge(regime_counts, left_index=True, right_index=True)
    return regime_counts, agg_regimes


def add_sector(aggregate_regime, sector_map_df):
    sector_map_df = sector_map_df[['symbol', 'GICS Sector', 'GICS Sub-Industry']].copy()
    sector_map_df = sector_map_df.set_index('symbol')
    multi_index = pd.MultiIndex.from_tuples(
        [(col, sector_map_df.loc[col, 'GICS Sector'], sector_map_df.loc[col, 'GICS Sub-Industry']) for col in aggregate_regime.columns],
        names=['symbol', 'GICS Sector', 'GICS Sub-Industry']
    )
    aggregate_regime.columns = multi_index
    return aggregate_regime


def plot_sector_on_bench(canvas, bench_df, rel, abs, selected: str):
    """
    Plot the sector data on the same plot as the benchmark data.
    Integrate with display library of choice.
    """
    # Create a figure and axes
    ax1 = canvas.axes()

    # Plot the 'spy' data on the primary axis
    ax1.plot(bench_df.index, bench_df['close'], color='lightblue', label='SPY')

    # Set the y-axis label for the primary axis
    ax1.set_ylabel('SPY Price', color='lightblue')
    ax1.tick_params(axis='y', colors='lightblue')

    # Create a secondary axis
    ax2 = ax1.twinx()

    # Plot the 'rel_sector' and 'abs_sector' data on the secondary axis
    ax2.plot(abs.index, abs[selected], color='darkred', linestyle='--', label='Absolute Sector')
    ax2.plot(rel.index, rel[selected], color='darkgreen', linestyle='--', label='Relative Sector')

    # Set the y-axis label for the secondary axis
    ax2.set_ylabel('Sector Value', color='darkred')
    ax2.tick_params(axis='y', colors='darkred')

    # Set the title and legend
    ax1.set_title(f'{selected}: Relative and Absolute Regime')
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')

    canvas.draw()


def main_market_scan(benchmark_symbol: str, interval: str, source: str, db_url):
    client = RegimeDataClient(db_url)
    (market_data, ) = client.get_data_by_market(benchmark_symbol, interval, source, tables=['regime'])
    benchmark, _, __ = client.get_stock_data(benchmark_symbol, interval, source)
    stock_info = pd.read_sql_table("stock_info", db_url)

    market_data = market_data.loc[
        (market_data.symbol != benchmark_symbol)
    ].copy()

    benchmark.index = benchmark.bar_number
    benchmark.index.name = 'index'

    view = AbsRelRegimeView.build(market_data, benchmark, stock_info)

    return view