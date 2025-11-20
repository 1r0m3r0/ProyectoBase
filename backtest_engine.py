"""
BACKTEST ENGINE
Motor de backtesting con simulación realista
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger
from strategies.base_strategy import BaseStrategy, SignalType


@dataclass
class Trade:
    """Representación de un trade en backtesting"""
    entry_time: datetime
    exit_time: Optional[datetime] = None
    symbol: str = ""
    side: str = ""  # 'long' or 'short'
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    pnl: float = 0.0
    pnl_percentage: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    strategy: str = ""
    status: str = "open"  # open, closed


@dataclass
class BacktestResults:
    """Resultados de backtesting"""
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=pd.Series)
    
    # Métricas de rendimiento
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    total_pnl: float = 0.0
    total_return_pct: float = 0.0
    
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    
    total_commission: float = 0.0
    total_slippage: float = 0.0


class BacktestEngine:
    """
    Motor de backtesting
    Simula ejecución de estrategias en datos históricos
    """
    
    def __init__(
        self,
        initial_capital: float,
        commission_rate: float = 0.0004,
        slippage_pct: float = 0.05,
        config: Optional[Dict] = None
    ):
        """
        Inicializar backtesting engine
        
        Args:
            initial_capital: Capital inicial
            commission_rate: Tasa de comisiones (0.04% default)
            slippage_pct: Slippage en % (0.05% default)
            config: Configuración adicional
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_pct = slippage_pct
        self.config = config or {}
        
        self.trades: List[Trade] = []
        self.open_positions: Dict[str, Trade] = {}
        self.equity_curve = []
        
        logger.info(f"BacktestEngine inicializado con ${initial_capital:.2f}")
    
    # ===================================
    # EJECUCIÓN DE BACKTEST
    # ===================================
    
    def run(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        position_size_pct: float = 2.0
    ) -> BacktestResults:
        """
        Ejecutar backtest
        
        Args:
            strategy: Estrategia a probar
            data: DataFrame con datos OHLCV
            position_size_pct: % del capital por trade
            
        Returns:
            BacktestResults con métricas
        """
        logger.info(f"Iniciando backtest de {strategy.name}...")
        
        # Reset estado
        self.current_capital = self.initial_capital
        self.trades = []
        self.open_positions = {}
        self.equity_curve = []
        
        # Obtener historia mínima requerida
        min_history = strategy.get_required_history()
        
        # Iterar sobre datos
        for i in range(min_history, len(data)):
            # Slice de datos hasta el punto actual
            historical_data = data.iloc[:i+1].copy()
            
            # Obtener señal de estrategia
            signal = strategy.analyze(historical_data)
            
            # Procesar señal
            self._process_signal(signal, historical_data, position_size_pct)
            
            # Actualizar posiciones abiertas (stop loss, take profit)
            current_price = historical_data['close'].iloc[-1]
            current_time = historical_data.index[-1]
            self._update_open_positions(current_price, current_time)
            
            # Registrar equity
            self._update_equity()
        
        # Cerrar posiciones abiertas al final
        self._close_all_positions(data['close'].iloc[-1], data.index[-1])
        
        # Calcular métricas
        results = self._calculate_metrics()
        
        logger.success(f"Backtest completado: {results.total_trades} trades")
        return results
    
    def _process_signal(
        self,
        signal,
        data: pd.DataFrame,
        position_size_pct: float
    ):
        """Procesar señal de trading"""
        symbol = signal.symbol
        
        # Si señal es HOLD, no hacer nada
        if signal.signal == SignalType.HOLD:
            return
        
        # Si señal es cerrar, cerrar posición
        if signal.signal in [SignalType.CLOSE_LONG, SignalType.CLOSE_SHORT]:
            if symbol in self.open_positions:
                self._close_position(
                    symbol,
                    data['close'].iloc[-1],
                    data.index[-1]
                )
            return
        
        # Si señal es LONG o SHORT, abrir posición
        if signal.signal in [SignalType.LONG, SignalType.SHORT]:
            # No abrir si ya hay posición
            if symbol in self.open_positions:
                return
            
            self._open_position(
                symbol=symbol,
                side='long' if signal.signal == SignalType.LONG else 'short',
                price=data['close'].iloc[-1],
                time=data.index[-1],
                position_size_pct=position_size_pct,
                strategy_name=signal.strategy_name
            )
    
    def _open_position(
        self,
        symbol: str,
        side: str,
        price: float,
        time: datetime,
        position_size_pct: float,
        strategy_name: str
    ):
        """Abrir nueva posición"""
        # Calcular tamaño
        position_value = (self.current_capital * position_size_pct) / 100
        
        # Aplicar slippage
        slippage = price * (self.slippage_pct / 100)
        if side == 'long':
            entry_price = price + slippage
        else:
            entry_price = price - slippage
        
        quantity = position_value / entry_price
        
        # Calcular comisión
        commission = position_value * self.commission_rate
        
        # Calcular stop loss y take profit (simplificado)
        if side == 'long':
            stop_loss = entry_price * 0.98  # 2% stop
            take_profit = entry_price * 1.04  # 4% target
        else:
            stop_loss = entry_price * 1.02
            take_profit = entry_price * 0.96
        
        # Crear trade
        trade = Trade(
            entry_time=time,
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            commission=commission,
            slippage=slippage,
            strategy=strategy_name,
            status='open'
        )
        
        self.open_positions[symbol] = trade
        self.current_capital -= (position_value + commission)
        
        logger.debug(
            f"Posición abierta: {side.upper()} {quantity:.6f} {symbol} @ ${entry_price:.4f}"
        )
    
    def _close_position(
        self,
        symbol: str,
        price: float,
        time: datetime,
        reason: str = "signal"
    ):
        """Cerrar posición"""
        if symbol not in self.open_positions:
            return
        
        trade = self.open_positions[symbol]
        
        # Aplicar slippage
        slippage = price * (self.slippage_pct / 100)
        if trade.side == 'long':
            exit_price = price - slippage
        else:
            exit_price = price + slippage
        
        # Calcular P&L
        if trade.side == 'long':
            pnl_per_unit = exit_price - trade.entry_price
        else:
            pnl_per_unit = trade.entry_price - exit_price
        
        gross_pnl = pnl_per_unit * trade.quantity
        
        # Calcular comisión de cierre
        exit_value = exit_price * trade.quantity
        exit_commission = exit_value * self.commission_rate
        
        # P&L neto
        net_pnl = gross_pnl - exit_commission
        pnl_pct = (net_pnl / (trade.entry_price * trade.quantity)) * 100
        
        # Actualizar trade
        trade.exit_time = time
        trade.exit_price = exit_price
        trade.pnl = net_pnl
        trade.pnl_percentage = pnl_pct
        trade.commission += exit_commission
        trade.status = 'closed'
        
        # Actualizar capital
        self.current_capital += (exit_value + net_pnl)
        
        # Registrar trade
        self.trades.append(trade)
        del self.open_positions[symbol]
        
        logger.debug(
            f"Posición cerrada: {symbol} P&L: ${net_pnl:+.2f} ({pnl_pct:+.2f}%) "
            f"[{reason}]"
        )
    
    def _update_open_positions(self, current_price: float, current_time: datetime):
        """Actualizar posiciones abiertas (verificar SL/TP)"""
        to_close = []
        
        for symbol, trade in self.open_positions.items():
            if trade.side == 'long':
                # Check stop loss
                if current_price <= trade.stop_loss:
                    to_close.append((symbol, current_price, 'stop_loss'))
                # Check take profit
                elif current_price >= trade.take_profit:
                    to_close.append((symbol, current_price, 'take_profit'))
            
            else:  # short
                # Check stop loss
                if current_price >= trade.stop_loss:
                    to_close.append((symbol, current_price, 'stop_loss'))
                # Check take profit
                elif current_price <= trade.take_profit:
                    to_close.append((symbol, current_price, 'take_profit'))
        
        # Cerrar posiciones
        for symbol, price, reason in to_close:
            self._close_position(symbol, price, current_time, reason)
    
    def _close_all_positions(self, price: float, time: datetime):
        """Cerrar todas las posiciones abiertas"""
        symbols = list(self.open_positions.keys())
        for symbol in symbols:
            self._close_position(symbol, price, time, "end_of_backtest")
    
    def _update_equity(self):
        """Actualizar curva de equity"""
        # Capital + valor posiciones abiertas
        open_positions_value = sum(
            trade.quantity * trade.entry_price
            for trade in self.open_positions.values()
        )
        
        total_equity = self.current_capital + open_positions_value
        self.equity_curve.append(total_equity)
    
    # ===================================
    # CÁLCULO DE MÉTRICAS
    # ===================================
    
    def _calculate_metrics(self) -> BacktestResults:
        """Calcular todas las métricas de rendimiento"""
        if not self.trades:
            logger.warning("No hay trades para analizar")
            return BacktestResults()
        
        results = BacktestResults()
        results.trades = self.trades
        
        # Convertir equity curve a Series
        results.equity_curve = pd.Series(self.equity_curve)
        
        # Métricas básicas
        results.total_trades = len(self.trades)
        results.winning_trades = sum(1 for t in self.trades if t.pnl > 0)
        results.losing_trades = sum(1 for t in self.trades if t.pnl < 0)
        results.win_rate = (results.winning_trades / results.total_trades) * 100
        
        # P&L
        results.total_pnl = sum(t.pnl for t in self.trades)
        results.total_return_pct = (
            (results.total_pnl / self.initial_capital) * 100
        )
        
        # Wins y losses
        wins = [t.pnl for t in self.trades if t.pnl > 0]
        losses = [t.pnl for t in self.trades if t.pnl < 0]
        
        results.avg_win = np.mean(wins) if wins else 0
        results.avg_loss = np.mean(losses) if losses else 0
        results.largest_win = max(wins) if wins else 0
        results.largest_loss = min(losses) if losses else 0
        
        # Profit factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        results.profit_factor = (
            gross_profit / gross_loss if gross_loss > 0 else 0
        )
        
        # Sharpe y Sortino
        returns = results.equity_curve.pct_change().dropna()
        results.sharpe_ratio = (
            (returns.mean() / returns.std()) * np.sqrt(252)
            if returns.std() > 0 else 0
        )
        
        downside_returns = returns[returns < 0]
        results.sortino_ratio = (
            (returns.mean() / downside_returns.std()) * np.sqrt(252)
            if len(downside_returns) > 0 else 0
        )
        
        # Drawdown
        cummax = results.equity_curve.cummax()
        drawdown = (results.equity_curve - cummax) / cummax * 100
        results.max_drawdown = abs(drawdown.min())
        
        # Comisiones y slippage
        results.total_commission = sum(t.commission for t in self.trades)
        results.total_slippage = sum(t.slippage * t.quantity for t in self.trades)
        
        return results
    
    # ===================================
    # REPORTING
    # ===================================
    
    def print_results(self, results: BacktestResults):
        """Imprimir resultados de backtest"""
        print("\n" + "="*60)
        print("RESULTADOS DEL BACKTEST")
        print("="*60)
        
        print(f"\n📊 TRADES:")
        print(f"  Total: {results.total_trades}")
        print(f"  Ganadores: {results.winning_trades} ({results.win_rate:.1f}%)")
        print(f"  Perdedores: {results.losing_trades}")
        
        print(f"\n💰 RENDIMIENTO:")
        print(f"  P&L Total: ${results.total_pnl:+,.2f}")
        print(f"  Retorno: {results.total_return_pct:+.2f}%")
        print(f"  Capital Inicial: ${self.initial_capital:,.2f}")
        print(f"  Capital Final: ${self.initial_capital + results.total_pnl:,.2f}")
        
        print(f"\n📈 ESTADÍSTICAS:")
        print(f"  Ganancia Promedio: ${results.avg_win:,.2f}")
        print(f"  Pérdida Promedio: ${results.avg_loss:,.2f}")
        print(f"  Ganancia Máxima: ${results.largest_win:,.2f}")
        print(f"  Pérdida Máxima: ${results.largest_loss:,.2f}")
        print(f"  Profit Factor: {results.profit_factor:.2f}")
        
        print(f"\n📉 RIESGO:")
        print(f"  Max Drawdown: {results.max_drawdown:.2f}%")
        print(f"  Sharpe Ratio: {results.sharpe_ratio:.2f}")
        print(f"  Sortino Ratio: {results.sortino_ratio:.2f}")
        
        print(f"\n💸 COSTOS:")
        print(f"  Comisiones: ${results.total_commission:,.2f}")
        print(f"  Slippage: ${results.total_slippage:,.2f}")
        
        print("="*60 + "\n")