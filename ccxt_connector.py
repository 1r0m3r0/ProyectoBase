"""
CONECTOR CCXT PARA EXCHANGES
Maneja conexión REST API con múltiples exchanges
"""

import ccxt
from typing import Dict, List, Optional, Tuple
from loguru import logger
import asyncio
from datetime import datetime
import pandas as pd


class CCXTConnector:
    """
    Conector unificado para exchanges usando CCXT
    Soporta Binance, Bybit, OKX, etc.
    """
    
    def __init__(
        self,
        exchange_id: str,
        config: Dict,
        testnet: bool = True
    ):
        """
        Inicializar conector
        
        Args:
            exchange_id: 'binance', 'bybit', etc
            config: Configuración del exchange
            testnet: True para testnet, False para producción
        """
        self.exchange_id = exchange_id
        self.config = config
        self.testnet = testnet
        self.exchange = None
        self.markets = {}
        self.tickers = {}
        
        self._initialize_exchange()
    
    def _initialize_exchange(self):
        """Inicializar instancia de CCXT"""
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
            
            config = {
                'apiKey': self.config.get('api_key'),
                'secret': self.config.get('api_secret'),
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',  # spot, future, margin
                }
            }
            
            # URLs de testnet
            if self.testnet:
                if self.exchange_id == 'binance':
                    config['urls'] = {
                        'api': {
                            'public': 'https://testnet.binancefuture.com',
                            'private': 'https://testnet.binancefuture.com',
                        }
                    }
                elif self.exchange_id == 'bybit':
                    config['urls'] = {
                        'api': 'https://api-testnet.bybit.com'
                    }
            
            self.exchange = exchange_class(config)
            
            # Cargar mercados
            self.markets = self.exchange.load_markets()
            
            logger.success(
                f"{self.exchange_id.upper()} conectado "
                f"({'TESTNET' if self.testnet else 'PRODUCCIÓN'})"
            )
            
        except Exception as e:
            logger.error(f"Error conectando a {self.exchange_id}: {e}")
            raise
    
    # ===================================
    # MARKET DATA
    # ===================================
    
    async def get_ticker(self, symbol: str) -> Dict:
        """
        Obtener ticker actual
        
        Args:
            symbol: Par (ej: 'BTC/USDT')
            
        Returns:
            Diccionario con datos del ticker
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            self.tickers[symbol] = ticker
            return ticker
        except Exception as e:
            logger.error(f"Error obteniendo ticker {symbol}: {e}")
            return {}
    
    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = '5m',
        limit: int = 100,
        since: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Obtener datos OHLCV
        
        Args:
            symbol: Par de trading
            timeframe: Temporalidad (1m, 5m, 15m, 1h, etc)
            limit: Número de velas
            since: Timestamp inicial (ms)
            
        Returns:
            DataFrame con columnas: timestamp, open, high, low, close, volume
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                limit=limit,
                since=since
            )
            
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df.attrs['symbol'] = symbol
            
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo OHLCV {symbol}: {e}")
            return pd.DataFrame()
    
    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Descargar datos históricos completos
        
        Args:
            symbol: Par de trading
            timeframe: Temporalidad
            start_date: Fecha inicial
            end_date: Fecha final (opcional, default=ahora)
            
        Returns:
            DataFrame con datos históricos
        """
        if end_date is None:
            end_date = datetime.now()
        
        all_data = []
        since = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)
        
        timeframe_ms = self._timeframe_to_ms(timeframe)
        
        logger.info(f"Descargando histórico {symbol} {timeframe}...")
        
        while since < end_ts:
            try:
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol,
                    timeframe=timeframe,
                    since=since,
                    limit=1000
                )
                
                if not ohlcv:
                    break
                
                all_data.extend(ohlcv)
                since = ohlcv[-1][0] + timeframe_ms
                
                # Rate limiting
                await asyncio.sleep(self.exchange.rateLimit / 1000)
                
            except Exception as e:
                logger.error(f"Error en descarga histórica: {e}")
                break
        
        if all_data:
            df = pd.DataFrame(
                all_data,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df = df[~df.index.duplicated(keep='first')]
            
            logger.success(
                f"Descargados {len(df)} registros de {symbol} {timeframe}"
            )
            return df
        
        return pd.DataFrame()
    
    def _timeframe_to_ms(self, timeframe: str) -> int:
        """Convertir timeframe a milisegundos"""
        timeframes = {
            '1m': 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000,
        }
        return timeframes.get(timeframe, 60 * 1000)
    
    # ===================================
    # TRADING OPERATIONS
    # ===================================
    
    async def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        amount: float,
        price: Optional[float] = None,
        params: Dict = None
    ) -> Dict:
        """
        Crear orden
        
        Args:
            symbol: Par de trading
            side: 'buy' o 'sell'
            order_type: 'market', 'limit', 'stop_loss', etc
            amount: Cantidad
            price: Precio (para limit orders)
            params: Parámetros adicionales
            
        Returns:
            Información de la orden creada
        """
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
                params=params or {}
            )
            
            logger.info(
                f"Orden creada: {side.upper()} {amount} {symbol} "
                f"@ {price or 'MARKET'}"
            )
            
            return order
            
        except Exception as e:
            logger.error(f"Error creando orden: {e}")
            raise
    
    async def create_stop_loss(
        self,
        symbol: str,
        side: str,
        amount: float,
        stop_price: float
    ) -> Dict:
        """
        Crear orden de stop loss
        
        Args:
            symbol: Par
            side: 'buy' o 'sell'
            amount: Cantidad
            stop_price: Precio de activación
            
        Returns:
            Información de la orden
        """
        params = {
            'stopPrice': stop_price,
            'type': 'STOP_MARKET'
        }
        
        return await self.create_order(
            symbol=symbol,
            side=side,
            order_type='stop_loss',
            amount=amount,
            params=params
        )
    
    async def create_take_profit(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float
    ) -> Dict:
        """Crear orden de take profit"""
        params = {
            'stopPrice': price,
            'type': 'TAKE_PROFIT_MARKET'
        }
        
        return await self.create_order(
            symbol=symbol,
            side=side,
            order_type='take_profit',
            amount=amount,
            params=params
        )
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancelar orden"""
        try:
            self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Orden {order_id} cancelada")
            return True
        except Exception as e:
            logger.error(f"Error cancelando orden: {e}")
            return False
    
    async def get_balance(self) -> Dict:
        """Obtener balance de cuenta"""
        try:
            balance = self.exchange.fetch_balance()
            return balance
        except Exception as e:
            logger.error(f"Error obteniendo balance: {e}")
            return {}
    
    async def get_positions(self) -> List[Dict]:
        """Obtener posiciones abiertas"""
        try:
            positions = self.exchange.fetch_positions()
            return [p for p in positions if float(p['contracts']) > 0]
        except Exception as e:
            logger.error(f"Error obteniendo posiciones: {e}")
            return []
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Obtener órdenes abiertas"""
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            return orders
        except Exception as e:
            logger.error(f"Error obteniendo órdenes: {e}")
            return []
    
    # ===================================
    # MARKET TYPES
    # ===================================
    
    def set_market_type(self, market_type: str):
        """
        Cambiar tipo de mercado
        
        Args:
            market_type: 'spot', 'future', 'margin'
        """
        self.exchange.options['defaultType'] = market_type
        logger.info(f"Tipo de mercado cambiado a: {market_type}")
    
    def enable_futures_usd(self):
        """Habilitar futuros USD-M"""
        self.set_market_type('future')
        logger.info("Futuros USD-M habilitados")
    
    def enable_futures_coin(self):
        """Habilitar futuros COIN-M"""
        self.set_market_type('delivery')
        logger.info("Futuros COIN-M habilitados")
    
    def enable_spot(self):
        """Habilitar spot"""
        self.set_market_type('spot')
        logger.info("Spot habilitado")
    
    # ===================================
    # UTILITIES
    # ===================================
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """Obtener información del símbolo"""
        return self.markets.get(symbol, {})
    
    def is_connected(self) -> bool:
        """Verificar conexión"""
        try:
            self.exchange.fetch_time()
            return True
        except:
            return False
    
    async def close(self):
        """Cerrar conexión"""
        if self.exchange:
            await self.exchange.close()
            logger.info(f"{self.exchange_id} desconectado")