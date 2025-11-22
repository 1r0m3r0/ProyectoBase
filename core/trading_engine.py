"""
TRADING ENGINE - MOTOR PRINCIPAL
Coordina todos los componentes del bot
"""

import asyncio
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime
import pandas as pd

from exchange_connector.ccxt_connector import CCXTConnector
from exchange_connector.binance_websocket import BinanceWebSocket
from strategies.strategy_loader import StrategyLoader
from strategies.signal_combiner import SignalCombiner
from risk_management.risk_manager import RiskManager
from portfolio_manager.capital_allocator import CapitalAllocator, MarketType
from notifications.notification_manager import NotificationManager
from data_handler.data_manager import DataManager
from core.order_manager import OrderManager
from core.position_tracker import PositionTracker
from core.state_manager import StateManager


class TradingEngine:
    """
    Motor principal del bot de trading
    Orquesta todos los componentes y ejecuta el loop de trading
    """
    
    def __init__(self, config: Dict, mode: str = "testnet"):
        """
        Inicializar motor de trading
        
        Args:
            config: Configuración completa
            mode: 'production', 'testnet', 'paper', 'backtest'
        """
        self.config = config
        self.mode = mode
        self.running = False
        
        # Componentes principales
        self.exchanges = {}
        self.websockets = {}
        self.strategies = []
        self.risk_manager = None
        self.portfolio_manager = None
        self.notification_manager = None
        self.data_manager = None
        self.order_manager = None
        self.position_tracker = None
        self.state_manager = None
        self.signal_combiner = None
        
        # Estado interno
        self.market_data = {}  # Symbol -> DataFrame
        self.latest_signals = {}  # Strategy -> Signal
        
        logger.info(f"TradingEngine creado en modo: {mode}")
    
    async def initialize(self):
        """Inicializar todos los componentes"""
        logger.info("Inicializando TradingEngine...")
        
        try:
            # 1. State Manager
            self.state_manager = StateManager()
            
            # 2. Data Manager
            self.data_manager = DataManager(self.config)
            await self.data_manager.initialize()
            
            # 3. Exchanges
            await self._initialize_exchanges()
            
            # 4. WebSockets
            await self._initialize_websockets()
            
            # 5. Risk Manager
            self.risk_manager = RiskManager(
                self.config['risk_management']
            )
            self.risk_manager.set_capital(
                self.config['portfolio']['total_capital']
            )
            
            # 6. Portfolio Manager
            self.portfolio_manager = CapitalAllocator(
                self.config['portfolio']
            )
            
            # 7. Order Manager
            self.order_manager = OrderManager(
                self.exchanges,
                self.risk_manager,
                self.portfolio_manager
            )
            
            # 8. Position Tracker
            self.position_tracker = PositionTracker(
                self.exchanges,
                self.risk_manager
            )
            
            # 9. Strategies
            await self._initialize_strategies()
            
            # 10. Signal Combiner
            self.signal_combiner = SignalCombiner(
                self.config['strategies'].get('signal_combination', {})
            )
            
            # 11. Notifications
            self.notification_manager = NotificationManager(
                self.config['notifications']
            )
            
            # Notificar inicio
            await self.notification_manager.notify_bot_started(self.mode)
            
            logger.success("TradingEngine inicializado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error inicializando TradingEngine: {e}")
            return False
    
    async def _initialize_exchanges(self):
        """Inicializar conexiones a exchanges"""
        logger.info("Inicializando exchanges...")
        
        exchange_configs = self.config['exchanges']
        testnet = self.mode == "testnet"
        
        for exchange_id in exchange_configs['enabled']:
            try:
                connector = CCXTConnector(
                    exchange_id=exchange_id,
                    config=exchange_configs[exchange_id],
                    testnet=testnet
                )
                
                self.exchanges[exchange_id] = connector
                logger.success(f"Exchange {exchange_id} inicializado")
                
            except Exception as e:
                logger.error(f"Error inicializando {exchange_id}: {e}")
    
    async def _initialize_websockets(self):
        """Inicializar WebSocket connections"""
        logger.info("Inicializando WebSockets...")
        
        # Binance WebSocket
        if 'binance' in self.exchanges:
            ws = BinanceWebSocket(
                market_type="futures",
                testnet=(self.mode == "testnet")
            )
            
            # Suscribirse a símbolos configurados
            symbols = self._get_all_symbols()
            for symbol in symbols:
                symbol_formatted = symbol.replace('/', '').lower()
                ws.subscribe_klines(
                    symbol_formatted,
                    "1m",
                    self._on_kline_update
                )
            
            ws.connect()
            self.websockets['binance'] = ws
            
            logger.success("WebSocket Binance conectado")
    
    async def _initialize_strategies(self):
        """Cargar y inicializar estrategias"""
        logger.info("Cargando estrategias...")
        
        loader = StrategyLoader(self.config['strategies'])
        self.strategies = loader.load_all_strategies()
        
        logger.success(f"Cargadas {len(self.strategies)} estrategias")
    
    def _get_all_symbols(self) -> List[str]:
        """Obtener todos los símbolos configurados"""
        symbols = set()
        for strategy_config in self.config['strategies'].values():
            if isinstance(strategy_config, dict) and 'symbols' in strategy_config:
                symbols.update(strategy_config['symbols'])
        return list(symbols)
    
    # ===================================
    # MAIN TRADING LOOP
    # ===================================
    
    async def run(self):
        """Loop principal de trading"""
        logger.info("Iniciando loop de trading...")
        self.running = True
        
        # Tasks concurrentes
        tasks = [
            self._market_data_loop(),
            self._strategy_analysis_loop(),
            self._position_management_loop(),
            self._risk_monitoring_loop(),
            self._performance_tracking_loop()
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error en loop principal: {e}")
            await self.notification_manager.notify_error(str(e), critical=True)
    
    async def _market_data_loop(self):
        """Loop de actualización de datos de mercado"""
        while self.running:
            try:
                # Actualizar datos desde exchanges
                for exchange_id, exchange in self.exchanges.items():
                    symbols = self._get_all_symbols()
                    
                    for symbol in symbols:
                        # Obtener datos OHLCV
                        df = await exchange.get_ohlcv(
                            symbol=symbol,
                            timeframe='5m',
                            limit=200
                        )
                        
                        if not df.empty:
                            self.market_data[symbol] = df
                
                await asyncio.sleep(5)  # Actualizar cada 5 segundos
                
            except Exception as e:
                logger.error(f"Error en market_data_loop: {e}")
                await asyncio.sleep(10)
    
    async def _strategy_analysis_loop(self):
        """Loop de análisis de estrategias"""
        while self.running:
            try:
                # Analizar cada estrategia
                for strategy in self.strategies:
                    if not strategy.is_active:
                        continue
                    
                    # Para cada símbolo de la estrategia
                    for symbol in strategy.symbols:
                        if symbol not in self.market_data:
                            continue
                        
                        # Obtener datos
                        data = self.market_data[symbol]
                        
                        # Generar señal
                        signal = strategy.analyze(data)
                        
                        # Guardar señal
                        key = f"{strategy.name}_{symbol}"
                        self.latest_signals[key] = signal
                        
                        # Procesar señal
                        await self._process_signal(signal)
                
                await asyncio.sleep(10)  # Analizar cada 10 segundos
                
            except Exception as e:
                logger.error(f"Error en strategy_analysis_loop: {e}")
                await asyncio.sleep(15)
    
    async def _process_signal(self, signal):
        """
        Procesar señal de trading
        
        Args:
            signal: TradingSignal
        """
        from strategies.base_strategy import SignalType
        
        # Ignorar señales HOLD o de baja confianza
        if signal.signal == SignalType.HOLD:
            return
        
        if signal.confidence < 0.5:
            logger.debug(f"Señal de baja confianza ignorada: {signal}")
            return
        
        # Combinar con otras señales si está habilitado
        if self.signal_combiner:
            combined_signal = self.signal_combiner.combine_signals(
                signal.symbol,
                self.latest_signals
            )
            if not combined_signal:
                return
            signal = combined_signal
        
        # Verificar si podemos operar
        symbol = signal.symbol
        
        # Si señal es de apertura (LONG/SHORT)
        if signal.signal in [SignalType.LONG, SignalType.SHORT]:
            await self._open_position(signal)
        
        # Si señal es de cierre
        elif signal.signal in [SignalType.CLOSE_LONG, SignalType.CLOSE_SHORT]:
            await self._close_position(signal)
    
    async def _open_position(self, signal):
        """Abrir nueva posición basada en señal"""
        try:
            symbol = signal.symbol
            side = 'long' if signal.signal.value == 'long' else 'short'
            
            # Verificar si ya hay posición abierta
            if self.position_tracker.has_position(symbol):
                logger.debug(f"Posición ya existe para {symbol}")
                return
            
            # Obtener precio actual
            price = signal.price
            
            # Calcular stop loss y take profit
            atr = self._calculate_atr(symbol)
            stop_loss = self.risk_manager.calcular_stop_loss(
                symbol, price, side, atr
            )
            take_profit = self.risk_manager.calcular_take_profit(
                price, stop_loss, side
            )
            
            # Calcular tamaño de posición
            quantity, value_usd = self.risk_manager.calcular_tamaño_posicion(
                symbol, price, stop_loss
            )
            
            # Verificar si podemos abrir
            puede_abrir, razon = self.risk_manager.puede_abrir_posicion(
                symbol, value_usd
            )
            
            if not puede_abrir:
                logger.warning(f"No se puede abrir posición: {razon}")
                return
            
            # Determinar tipo de mercado
            market_type = self._get_market_type_for_symbol(symbol)
            
            # Verificar capital disponible
            if not self.portfolio_manager.allocate_capital(market_type, value_usd):
                logger.warning(f"Capital insuficiente en {market_type.value}")
                return
            
            # Crear orden de entrada
            order = await self.order_manager.create_market_order(
                symbol=symbol,
                side='buy' if side == 'long' else 'sell',
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            if order:
                # Registrar posición
                self.position_tracker.add_position(
                    symbol=symbol,
                    side=side,
                    entry_price=price,
                    quantity=quantity,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    value_usd=value_usd,
                    market_type=market_type,
                    strategy=signal.strategy_name
                )
                
                # Notificar
                await self.notification_manager.notify_trade_entry(
                    symbol=symbol,
                    side=side,
                    price=price,
                    quantity=quantity,
                    strategy=signal.strategy_name
                )
                
                logger.success(
                    f"Posición abierta: {side.upper()} {quantity} {symbol} @ ${price}"
                )
            
        except Exception as e:
            logger.error(f"Error abriendo posición: {e}")
            await self.notification_manager.notify_error(str(e))
    
    async def _close_position(self, signal):
        """Cerrar posición existente"""
        try:
            symbol = signal.symbol
            
            if not self.position_tracker.has_position(symbol):
                return
            
            position = self.position_tracker.get_position(symbol)
            
            # Crear orden de cierre
            order = await self.order_manager.create_market_order(
                symbol=symbol,
                side='sell' if position.side == 'long' else 'buy',
                quantity=position.quantity
            )
            
            if order:
                # Calcular P&L
                exit_price = signal.price
                pnl, pnl_pct = self.position_tracker.calculate_pnl(
                    symbol, exit_price
                )
                
                # Liberar capital
                self.portfolio_manager.release_capital(
                    position.market_type,
                    position.value_usd,
                    pnl
                )
                
                # Registrar cierre en risk manager
                self.risk_manager.registrar_trade_cerrado(
                    symbol, pnl, pnl > 0
                )
                
                # Notificar
                await self.notification_manager.notify_trade_exit(
                    symbol=symbol,
                    side=position.side,
                    entry_price=position.entry_price,
                    exit_price=exit_price,
                    quantity=position.quantity,
                    pnl=pnl,
                    pnl_percentage=pnl_pct
                )
                
                # Remover posición
                self.position_tracker.remove_position(symbol)
                
                logger.success(
                    f"Posición cerrada: {symbol} P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%)"
                )
            
        except Exception as e:
            logger.error(f"Error cerrando posición: {e}")
            await self.notification_manager.notify_error(str(e))
    
    async def _position_management_loop(self):
        """Loop de gestión de posiciones abiertas"""
        while self.running:
            try:
                # Actualizar todas las posiciones
                await self.position_tracker.update_all_positions(
                    self.market_data
                )
                
                # Verificar stops y trailing stops
                for symbol in self.position_tracker.get_all_symbols():
                    position = self.position_tracker.get_position(symbol)
                    current_price = self.market_data[symbol]['close'].iloc[-1]
                    
                    # Trailing stop
                    if self.config['risk_management']['trailing_stop']['enabled']:
                        self.position_tracker.update_trailing_stop(
                            symbol, current_price
                        )
                    
                    # Break even
                    if self.config['risk_management']['break_even']['enabled']:
                        self.position_tracker.update_break_even(
                            symbol, current_price
                        )
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error en position_management_loop: {e}")
                await asyncio.sleep(10)
    
    async def _risk_monitoring_loop(self):
        """Loop de monitoreo de riesgo"""
        while self.running:
            try:
                # Verificar estado del risk manager
                status = self.risk_manager.get_status()
                
                # Si bot está pausado, intentar reanudar
                if status['pausado']:
                    logger.warning(f"Bot pausado: {status['razon_pausa']}")
                    # Aquí podrías implementar lógica para reanudar
                
                # Verificar rebalanceo de portfolio
                if self.portfolio_manager.check_rebalance_needed():
                    self.portfolio_manager.rebalance()
                
                await asyncio.sleep(60)  # Cada minuto
                
            except Exception as e:
                logger.error(f"Error en risk_monitoring_loop: {e}")
                await asyncio.sleep(60)
    
    async def _performance_tracking_loop(self):
        """Loop de seguimiento de rendimiento"""
        while self.running:
            try:
                # Guardar estado cada 5 minutos
                await self.state_manager.save_state({
                    'timestamp': datetime.now().isoformat(),
                    'positions': self.position_tracker.get_all_positions(),
                    'capital': self.portfolio_manager.get_allocation_summary(),
                    'risk_status': self.risk_manager.get_status()
                })
                
                await asyncio.sleep(300)  # Cada 5 minutos
                
            except Exception as e:
                logger.error(f"Error en performance_tracking_loop: {e}")
                await asyncio.sleep(300)
    
    # ===================================
    # UTILIDADES
    # ===================================
    
    def _on_kline_update(self, kline_data: Dict):
        """Callback para actualizaciones de kline via WebSocket"""
        if kline_data['is_closed']:
            symbol = kline_data['symbol']
            # Actualizar datos en memoria
            # Implementación según necesidad
    
    def _calculate_atr(self, symbol: str, period: int = 14) -> float:
        """Calcular ATR para un símbolo"""
        if symbol not in self.market_data:
            return 0.0
        
        df = self.market_data[symbol]
        if len(df) < period:
            return 0.0
        
        import pandas_ta as ta
        atr = ta.atr(df['high'], df['low'], df['close'], length=period)
        return atr.iloc[-1] if not atr.empty else 0.0
    
    def _get_market_type_for_symbol(self, symbol: str) -> MarketType:
        """Determinar tipo de mercado para un símbolo"""
        # Lógica simplificada - mejorar según necesidad
        if 'USDT' in symbol or 'BUSD' in symbol:
            return MarketType.FUTURES_USD
        elif any(coin in symbol for coin in ['BTC', 'ETH']):
            return MarketType.FUTURES_COIN
        else:
            return MarketType.SPOT
    
    # ===================================
    # CONTROL
    # ===================================
    
    async def pause(self):
        """Pausar operaciones"""
        self.risk_manager.pausar_bot("Pausa manual")
        logger.warning("Bot pausado manualmente")
    
    async def resume(self):
        """Reanudar operaciones"""
        self.risk_manager.reanudar_bot()
        logger.info("Bot reanudado")
    
    async def shutdown(self):
        """Apagado seguro del bot"""
        logger.info("Iniciando apagado del TradingEngine...")
        self.running = False
        
        # Cerrar todas las posiciones (opcional)
        # await self.position_tracker.close_all_positions()
        
        # Cerrar WebSockets
        for ws in self.websockets.values():
            ws.disconnect()
        
        # Cerrar exchanges
        for exchange in self.exchanges.values():
            await exchange.close()
        
        # Cerrar notificaciones
        await self.notification_manager.close()
        
        # Notificar
        await self.notification_manager.notify_bot_stopped()
        
        logger.success("TradingEngine detenido correctamente")