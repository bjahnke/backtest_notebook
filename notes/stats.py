import pandas as pd
import numpy as np

def rolling_sharpe(returns, r_f, window):
    avg_returns = returns.rolling(window).mean()
    std_returns = returns.rolling(window).std(ddof=0)
    return (avg_returns - r_f) / std_returns

def expanding_sharpe(returns, r_f):
    avg_returns = returns.expanding().mean()
    std_returns = returns.expanding().std(ddof=0)
    return (avg_returns - r_f) / std_returns


def rolling_grit(cumul_returns, window):
    tt_rolling_peak = cumul_returns.rolling(window).max()
    drawdown_squared = (cumul_returns - tt_rolling_peak) ** 2
    ulcer = drawdown_squared.rolling(window).sum() ** 0.5
    return cumul_returns / ulcer


def expanding_grit(cumul_returns):
    tt_peak = cumul_returns.expanding().max()
    drawdown_squared = (cumul_returns - tt_peak) ** 2
    ulcer = drawdown_squared.expanding().sum() ** 0.5
    return cumul_returns / ulcer


def rolling_profits(returns,window):
    profit_roll = returns.copy()
    profit_roll[profit_roll < 0] = 0
    profit_roll_sum = profit_roll.rolling(window).sum().ffill()
    return profit_roll_sum


def rolling_losses(returns,window):
    loss_roll = returns.copy()
    loss_roll[loss_roll > 0] = 0
    loss_roll_sum = loss_roll.rolling(window).sum().ffill()
    return loss_roll_sum


def expanding_profits(returns): 
    profit_roll = returns.copy() 
    profit_roll[profit_roll < 0] = 0 
    profit_roll_sum = profit_roll.expanding().sum().ffill() 
    return profit_roll_sum 
 

def expanding_losses(returns): 
    loss_roll = returns.copy() 
    loss_roll[loss_roll > 0] = 0 
    loss_roll_sum =    loss_roll.expanding().sum().ffill() 
    return loss_roll_sum 


def profit_ratio(profits, losses):    
    pr = profits.ffill() / abs(losses.ffill())
    return pr


def rolling_tail_ratio(cumul_returns, window, percentile=0.05,limit=5):
    left_tail = np.abs(cumul_returns.rolling(window).quantile(percentile))
    right_tail = cumul_returns.rolling(window).quantile(1-percentile)
    np.seterr(all='ignore')
    tail = np.maximum(np.minimum(right_tail / left_tail,limit),-limit)
    return tail


def expanding_tail_ratio(cumul_returns, percentile=0.05,limit=5):
    left_tail = np.abs(cumul_returns.expanding().quantile(percentile))
    right_tail = cumul_returns.expanding().quantile(1 - percentile)
    np.seterr(all='ignore')
    tail = np.maximum(np.minimum(right_tail / left_tail,limit),-limit)
    return tail


def common_sense_ratio(pr, tr):
    return pr * tr    


def expectancy(win_rate, avg_win, avg_loss):  
    # win% * avg_win% - loss% * abs(avg_loss%) 
    return win_rate * avg_win + (1-win_rate) * avg_loss 


def t_stat(signal_count, trading_edge): 
    sqn = (signal_count ** 0.5) * trading_edge / trading_edge.std(ddof=0) 
    return sqn 


def robustness_score(grit, csr, sqn): 
    start_date = max(grit[pd.notnull(grit)].index[0],
               csr[pd.notnull(csr)].index[0],
               sqn[pd.notnull(sqn)].index[0])
    score = grit * csr * sqn / (grit[start_date] * csr[start_date] * sqn[start_date])
    return score


class Stats:
    def __init__(self, strategy):
        self.strategy = strategy
        strategy.apply_signals()
        self.price = strategy.price.close 
        self.trade_count = strategy.price.trade_count
        self.signal = strategy.price.signal

    def sharpe(self, r_f=0.00001, window=None):
        if window is None:
            res = expanding_sharpe(self.returns, r_f)
        else:
            res = rolling_sharpe(self.returns, r_f, window)
        return res

    def grit(self, window=None):
        if window is None:
            res = expanding_grit(self.returns)
        else:
            res = rolling_grit(self.returns, window)
        return res

    def profits(self, window=None):
        if window is None:
            res = expanding_profits(self.returns)
        else:
            res = rolling_profits(self.returns, window)
        return res

    def losses(self, window=None):
        if window is None:
            res = expanding_losses(self.returns)
        else:
            res = rolling_losses(self.returns, window)
        return res

    def profit_ratio(self, window=None):
        return profit_ratio(self.profits(window), self.losses(window))

    def tail_ratio(self, window=None):
        if window is None:
            res = expanding_tail_ratio(self.returns)
        else:
            res = rolling_tail_ratio(self.returns, window)
        return res

    def common_sense_ratio(self, window=None):
        return common_sense_ratio(self.profit_ratio(window), self.tail_ratio(window))

    def expectancy(self, window=None):
        return expectancy(self.win_rate(window), self.avg_win(window), self.avg_loss(window))

    def t_stat(self, window=None):
        return t_stat(self.signal_count(window), self.expectancy(window))

    def robustness_score(self, window=None):
        return robustness_score(self.grit(window), self.common_sense_ratio(window), self.t_stat(window))
    
    def avg_win(self, window=None):
        # if none then window is simply the entire series
        if window is None:
            window = self.log_returns[self.log_returns!=0].expanding().count().ffill()
            res = self.profits() / window
        else:
            res = self.profits(window) / window
        
        return res
    
    def avg_loss(self, window=None):
        # if none then window is simply the entire series
        if window is None:
            window = self.log_returns[self.log_returns!=0].expanding().count().ffill()
            res = self.losses() / window
        else:
            res = self.losses(window) / window
        
        return res
    
    @property
    def returns(self):
        # use log returns on purpose
        # arithmentic: self.price.pct_change()
        # TODO Shift signal to avoid look-ahead bias?
        return np.log(self.price / self.price.shift(1)) * self.signal
    
    @property
    def log_returns(self):
        return np.log(self.price / self.price.shift(1)) * self.signal
    
    def cumulative_log_returns(self, start=None):
        returns = self.log_returns
        if start is not None:
            returns = returns.loc[start:]
        
        return returns.cumsum().apply(np.exp) - 1
    
    def signal_count(self, window=None) -> pd.Series:
        if window is None:
            res = self.trade_count
        else:
            res = self.trade_count.diff(window)
        return res
    
    def win_rate(self, window=None):
        if window is None:
            res = self.returns.expanding().apply(lambda x: (x > 0).sum() / len(x))
        else:
            res = self.returns.rolling(window).apply(lambda x: (x > 0).sum() / len(x))
        return res