# region imports
from AlgorithmImports import *
import datetime

# endregion

"""
    The Turtle Trading strategy is a trend-following approach originally developed 
    by Richard Dennis and William Eckhardt in the 1980s. This implementation trades 
    the top 10 stocks from a selected index (default: S&P 500 Momentum), buying 
    breakouts above the Donchian Channel upper band and selling on breakdowns below 
    the lower band. Timeframes for breakout levels are configurable (e.g., yearly, 
    quarterly, monthly). Trades can optionally be filtered to only occur when 
    the benchmark index is in an uptrend (price above 200-day SMA).
"""

class TurtleV2(QCAlgorithm):

    INDEXES = {
        "SP500": {
            "stocks": ["NVDA", "MSFT", "AAPL", "AMZN", "META", "AVGO", "GOOGL", "BRK.B", "TSLA", "GOOG"],
            "benchmark_symbol": "SPY"
            # https://finance.yahoo.com/quote/SPY/holdings/
        },
        "NASDAQ100": {
            "stocks": ["NVDA", "MSFT", "AAPL", "AMZN", "AVGO", "META", "NFLX", "TSLA", "COST", "GOOGL"],
            "benchmark_symbol": "QQQ"
            # https://finance.yahoo.com/quote/QQQ/holdings/
        },
        "SP500 MOMENTUM": {
            "stocks": ["NVDA", "META", "AMZN", "AVGO", "JPM", "TSLA", "WMT", "NFLX", "PLTR", "COST"],
            "benchmark_symbol": "SPMO"
            # https://finance.yahoo.com/quote/SPMO/holdings/
        },
        "SP MEDIUM CAP MOMENTUM": {
            "stocks": ["IBKR", "EME", "SFM", "FIX", "GWRE", "USFD", "CRS", "EQH", "CW", "CASY"],
            "benchmark_symbol": "XMMO"
            # https://finance.yahoo.com/quote/XMMO/holdings/
        },
        "SP SMALL CAP MOMENTUM": {
            "stocks": ["EAT", "CORT", "COOP", "AWI", "IDCC", "SKYW", "JXN", "CALM", "DY", "SMTC"],
            "benchmark_symbol": "XSMO"
            # https://finance.yahoo.com/quote/XSMO/holdings/
        },
        "IPOX 100 US": {
            "stocks": ["GEV", "PLTR", "APP", "CEG", "RBLX", "DASH", "IBM", "HOOD", "TT", "IOT"],
            "benchmark_symbol": "FPX"
            # https://finance.yahoo.com/quote/FPX/
        }
    }

    BENCHMARK_OLD = "SPY"  # fallback benchmark

    BREAK_OUTS = {
        "YEARLY": {"entry": 250, "exit": 125},
        "SEMI-YEARLY": {"entry": 125, "exit": 62},
        "QUARTERLY": {"entry": 60, "exit": 30},
        "MONTHLY": {"entry": 20, "exit": 10},
        "WEEKLY": {"entry": 5, "exit": 3}
    }

    def initialize(self):

        # ********************************
        # User defined inputs
        # ********************************

        # Basic settings
        index = self.get_parameter("index", "SP500 MOMENTUM")
        breakout = self.get_parameter("breakout", "YEARLY")
        self.leverage = self.get_parameter("leverage", 0)

        # Filter settings
        self.enable_filter = True if (self.get_parameter("enable_filter", "True") == "True") else False

        # ********************************
        # Algorithm settings
        # ********************************

        # Basic
        self.set_start_date(datetime.date.today().year - 5, 1, 1)
        # self.set_end_date(2025,1,1)
        self.set_cash(10000)
        self.enable_automatic_indicator_warm_up = True

        self.benchmark_symbol = self.INDEXES[index]["benchmark_symbol"]
        self.benchmark_old_symbol = self.BENCHMARK_OLD
        self.symbols = self.INDEXES[index]["stocks"]
        self.markets = {symbol: self.add_equity(symbol, Resolution.DAILY, leverage=10) for symbol in self.symbols}
        self.add_equity(self.benchmark_symbol, Resolution.DAILY)
        self.add_equity(self.benchmark_old_symbol, Resolution.DAILY)
        self.enable_trading = True

        # Init indicators
        self.dchs = {symbol: self.dch(symbol, self.BREAK_OUTS[breakout]["entry"], self.BREAK_OUTS[breakout]["exit"]) for
                     symbol in self.symbols}
        self.benchmark_sma200 = self.sma(self.benchmark_symbol, 200)
        self.benchmark_old_sma200 = self.sma(self.benchmark_old_symbol, 200)

    def on_data(self, data: Slice):
        # **********************************
        # Zkontroluj trend benchmarku
        # **********************************
        if self.enable_filter:
            if self.benchmark_symbol in data.Bars:
                bar_benchmark = data.Bars[self.benchmark_symbol]
                self.enable_trading = bar_benchmark.close >= self.benchmark_sma200[1].value
            elif self.benchmark_old_symbol in data.Bars:  # fallback
                bar_benchmark = data.Bars[self.benchmark_old_symbol]
                self.enable_trading = bar_benchmark.close >= self.benchmark_old_sma200[1].value

        # **********************************
        # Aplikuj strategii na každou akcii
        # **********************************
        for symbol in self.symbols:
            dch = self.dchs[symbol]
            self.strategy(data, symbol, dch)

    def strategy(self, data, symbol, dch):
        # **********************************
        # Perform calculations and analysis
        # **********************************

        # Basic
        if symbol not in data.Bars or self.benchmark_symbol not in data.Bars:
            return

        bar = data.Bars[symbol]

        buy_condition = bar.close > dch.upper_band[1].value and self.enable_trading and not self.portfolio[symbol].is_long
        sell_condition = bar.close < dch.lower_band[1].value if self.enable_trading else True

        # ********************************
        # Manage trade
        # ********************************
        if buy_condition:
            self.set_holdings(symbol, (1 / len(self.symbols)) + (1 / len(self.symbols) * self.leverage))

        if sell_condition:
            self.liquidate(symbol)