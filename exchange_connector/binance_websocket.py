"""
BINANCE WEBSOCKET CONNECTOR
Conexión WebSocket para datos en tiempo real de Binance
"""

import websocket
import json
import threading
from typing import Callable, Dict, List, Optional
from loguru import logger
import time


class BinanceWebSocket:
    """
    Cliente WebSocket para Binance
    Soporta klines, trades, book ticker, etc. en tiempo real
    """
    
    # URLs
    SPOT_WS = "wss://stream.binance.com:9443/ws"
    FUTURES_WS = "wss://fstream.binance.com/ws"
    TESTNET_FUTURES_WS = "wss://stream.binancefuture.com/ws"
    
    def __init__(
        self,
        market_type: str = "futures",
        testnet: bool = True
    ):
        """
        Inicializar WebSocket
        
        Args:
            market_type: 'spot' o 'futures'
            testnet: True para testnet
        """
        self.market_type = market_type
        self.testnet = testnet
        
        # Seleccionar URL
        if testnet and market_type == "futures":
            self.base_url = self.TESTNET_FUTURES_WS
        elif market_type == "futures":
            self.base_url = self.FUTURES_WS
        else:
            self.base_url = self.SPOT_WS
        
        self.ws = None
        self.thread = None
        self.running = False
        self.subscriptions = []
        
        # Callbacks
        self.callbacks = {
            'kline': [],
            'trade': [],
            'ticker': [],
            'depth': [],
            'book_ticker': []
        }
        
        logger.info(f"BinanceWebSocket inicializado ({market_type})")
    
    # ===================================
    # CONEXIÓN
    # ===================================
    
    def connect(self):
        """Iniciar conexión WebSocket"""
        if self.running:
            logger.warning("WebSocket ya está corriendo")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        
        logger.success("WebSocket conectado")
    
    def _run(self):
        """Loop principal de WebSocket"""
        while self.running:
            try:
                # Construir URL con suscripciones
                streams = "/".join(self.subscriptions)
                url = f"{self.base_url}/{streams}" if streams else self.base_url
                
                self.ws = websocket.WebSocketApp(
                    url,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open
                )
                
                self.ws.run_forever()
                
                if self.running:
                    logger.warning("WebSocket desconectado, reconectando en 5s...")
                    time.sleep(5)
                    
            except Exception as e:
                logger.error(f"Error en WebSocket: {e}")
                time.sleep(5)
    
    def disconnect(self):
        """Cerrar conexión WebSocket"""
        self.running = False
        if self.ws:
            self.ws.close()
        logger.info("WebSocket desconectado")
    
    # ===================================
    # CALLBACKS
    # ===================================
    
    def _on_open(self, ws):
        """Callback al abrir conexión"""
        logger.success("WebSocket abierto")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Callback al cerrar"""
        logger.warning(f"WebSocket cerrado: {close_status_code} - {close_msg}")
    
    def _on_error(self, ws, error):
        """Callback de error"""
        logger.error(f"WebSocket error: {error}")
    
    def _on_message(self, ws, message):
        """
        Callback al recibir mensaje
        Distribuye a callbacks registrados
        """
        try:
            data = json.loads(message)
            
            # Identificar tipo de stream
            if 'e' in data:
                event_type = data['e']
                
                if event_type == 'kline':
                    self._handle_kline(data)
                elif event_type == 'aggTrade':
                    self._handle_trade(data)
                elif event_type == '24hrTicker':
                    self._handle_ticker(data)
                elif event_type == 'depthUpdate':
                    self._handle_depth(data)
                elif event_type == 'bookTicker':
                    self._handle_book_ticker(data)
                    
        except Exception as e:
            logger.error(f"Error procesando mensaje WS: {e}")
    
    # ===================================
    # HANDLERS DE DATOS
    # ===================================
    
    def _handle_kline(self, data: Dict):
        """Procesar datos de vela"""
        kline = data['k']
        
        processed = {
            'symbol': kline['s'],
            'timestamp': kline['t'],
            'open': float(kline['o']),
            'high': float(kline['h']),
            'low': float(kline['l']),
            'close': float(kline['c']),
            'volume': float(kline['v']),
            'is_closed': kline['x']
        }
        
        # Ejecutar callbacks
        for callback in self.callbacks['kline']:
            callback(processed)
    
    def _handle_trade(self, data: Dict):
        """Procesar trade"""
        processed = {
            'symbol': data['s'],
            'price': float(data['p']),
            'quantity': float(data['q']),
            'timestamp': data['T'],
            'is_buyer_maker': data['m']
        }
        
        for callback in self.callbacks['trade']:
            callback(processed)
    
    def _handle_ticker(self, data: Dict):
        """Procesar ticker 24h"""
        processed = {
            'symbol': data['s'],
            'price_change': float(data['p']),
            'price_change_percent': float(data['P']),
            'last_price': float(data['c']),
            'volume': float(data['v']),
            'high': float(data['h']),
            'low': float(data['l'])
        }
        
        for callback in self.callbacks['ticker']:
            callback(processed)
    
    def _handle_depth(self, data: Dict):
        """Procesar order book update"""
        processed = {
            'symbol': data['s'],
            'bids': [[float(p), float(q)] for p, q in data['b']],
            'asks': [[float(p), float(q)] for p, q in data['a']]
        }
        
        for callback in self.callbacks['depth']:
            callback(processed)
    
    def _handle_book_ticker(self, data: Dict):
        """Procesar best bid/ask"""
        processed = {
            'symbol': data['s'],
            'best_bid': float(data['b']),
            'best_bid_qty': float(data['B']),
            'best_ask': float(data['a']),
            'best_ask_qty': float(data['A'])
        }
        
        for callback in self.callbacks['book_ticker']:
            callback(processed)
    
    # ===================================
    # SUSCRIPCIONES
    # ===================================
    
    def subscribe_klines(
        self,
        symbol: str,
        interval: str,
        callback: Callable
    ):
        """
        Suscribirse a klines (velas)
        
        Args:
            symbol: Par (ej: 'btcusdt')
            interval: Temporalidad (1m, 5m, 1h, etc)
            callback: Función a ejecutar al recibir datos
        """
        stream = f"{symbol.lower()}@kline_{interval}"
        self.subscriptions.append(stream)
        self.callbacks['kline'].append(callback)
        
        logger.info(f"Suscrito a klines: {symbol} {interval}")
        
        # Reiniciar conexión si ya está activa
        if self.running:
            self._restart_connection()
    
    def subscribe_trades(self, symbol: str, callback: Callable):
        """Suscribirse a trades"""
        stream = f"{symbol.lower()}@aggTrade"
        self.subscriptions.append(stream)
        self.callbacks['trade'].append(callback)
        
        logger.info(f"Suscrito a trades: {symbol}")
        
        if self.running:
            self._restart_connection()
    
    def subscribe_ticker(self, symbol: str, callback: Callable):
        """Suscribirse a ticker 24h"""
        stream = f"{symbol.lower()}@ticker"
        self.subscriptions.append(stream)
        self.callbacks['ticker'].append(callback)
        
        logger.info(f"Suscrito a ticker: {symbol}")
        
        if self.running:
            self._restart_connection()
    
    def subscribe_book_ticker(self, symbol: str, callback: Callable):
        """Suscribirse a best bid/ask"""
        stream = f"{symbol.lower()}@bookTicker"
        self.subscriptions.append(stream)
        self.callbacks['book_ticker'].append(callback)
        
        logger.info(f"Suscrito a book ticker: {symbol}")
        
        if self.running:
            self._restart_connection()
    
    def subscribe_depth(
        self,
        symbol: str,
        callback: Callable,
        speed: str = "100ms"
    ):
        """
        Suscribirse a order book depth
        
        Args:
            symbol: Par
            callback: Función callback
            speed: '100ms' o '1000ms'
        """
        stream = f"{symbol.lower()}@depth@{speed}"
        self.subscriptions.append(stream)
        self.callbacks['depth'].append(callback)
        
        logger.info(f"Suscrito a depth: {symbol}")
        
        if self.running:
            self._restart_connection()
    
    def unsubscribe_all(self):
        """Cancelar todas las suscripciones"""
        self.subscriptions = []
        for key in self.callbacks:
            self.callbacks[key] = []
        
        logger.info("Todas las suscripciones canceladas")
        
        if self.running:
            self._restart_connection()
    
    def _restart_connection(self):
        """Reiniciar conexión con nuevas suscripciones"""
        if self.ws:
            self.ws.close()
        time.sleep(1)
    
    # ===================================
    # UTILIDADES
    # ===================================
    
    def get_subscriptions(self) -> List[str]:
        """Obtener lista de suscripciones activas"""
        return self.subscriptions.copy()
    
    def is_connected(self) -> bool:
        """Verificar si está conectado"""
        return self.running and self.ws is not None


# ===================================
# EJEMPLO DE USO
# ===================================

if __name__ == "__main__":
    
    def on_kline(data):
        print(f"Kline: {data['symbol']} - Close: {data['close']}")
    
    def on_trade(data):
        print(f"Trade: {data['symbol']} - Price: {data['price']}")
    
    # Crear instancia
    ws = BinanceWebSocket(market_type="futures", testnet=True)
    
    # Suscribirse
    ws.subscribe_klines("BTCUSDT", "1m", on_kline)
    ws.subscribe_trades("BTCUSDT", on_trade)
    
    # Conectar
    ws.connect()
    
    try:
        # Mantener vivo
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        ws.disconnect()