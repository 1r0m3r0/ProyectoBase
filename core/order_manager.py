"""
ORDER MANAGER
Gestiona creación y seguimiento de órdenes
"""

from typing import Dict, Optional
from loguru import logger
import asyncio


class OrderManager:
    """
    Gestor de órdenes de trading
    Maneja creación, modificación y cancelación de órdenes
    """
    
    def __init__(self, exchanges, risk_manager, portfolio_manager):
        """
        Inicializar order manager
        
        Args:
            exchanges: Dict de exchange connectors
            risk_manager: RiskManager instance
            portfolio_manager: CapitalAllocator instance
        """
        self.exchanges = exchanges
        self.risk_manager = risk_manager
        self.portfolio_manager = portfolio_manager
        
        self.active_orders = {}
        self.order_history = []
        
        logger.info("OrderManager inicializado")
    
    async def create_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        exchange_id: str = None
    ) -> Optional[Dict]:
        """
        Crear orden de mercado
        
        Args:
            symbol: Par de trading
            side: 'buy' o 'sell'
            quantity: Cantidad
            stop_loss: Precio de stop loss (opcional)
            take_profit: Precio de take profit (opcional)
            exchange_id: Exchange específico (None = primario)
            
        Returns:
            Información de la orden o None si falló
        """
        try:
            # Seleccionar exchange
            if exchange_id is None:
                exchange_id = list(self.exchanges.keys())[0]
            
            exchange = self.exchanges[exchange_id]
            
            # Crear orden principal
            order = await exchange.create_order(
                symbol=symbol,
                side=side,
                order_type='market',
                amount=quantity
            )
            
            if not order:
                logger.error("Fallo al crear orden de mercado")
                return None
            
            logger.info(
                f"Orden de mercado creada: {side.upper()} {quantity} {symbol}"
            )
            
            # Crear órdenes de stop loss y take profit
            if stop_loss:
                await self._create_stop_loss_order(
                    exchange, symbol, side, quantity, stop_loss
                )
            
            if take_profit:
                await self._create_take_profit_order(
                    exchange, symbol, side, quantity, take_profit
                )
            
            # Registrar orden
            self.active_orders[order['id']] = {
                'order': order,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }
            
            self.order_history.append(order)
            
            return order
            
        except Exception as e:
            logger.error(f"Error creando orden de mercado: {e}")
            return None
    
    async def create_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        exchange_id: str = None
    ) -> Optional[Dict]:
        """Crear orden límite"""
        try:
            if exchange_id is None:
                exchange_id = list(self.exchanges.keys())[0]
            
            exchange = self.exchanges[exchange_id]
            
            order = await exchange.create_order(
                symbol=symbol,
                side=side,
                order_type='limit',
                amount=quantity,
                price=price
            )
            
            if order:
                logger.info(
                    f"Orden límite creada: {side.upper()} {quantity} {symbol} @ ${price}"
                )
                self.active_orders[order['id']] = {
                    'order': order,
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'price': price
                }
            
            return order
            
        except Exception as e:
            logger.error(f"Error creando orden límite: {e}")
            return None
    
    async def _create_stop_loss_order(
        self,
        exchange,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float
    ):
        """Crear orden de stop loss"""
        try:
            # Invertir lado para cerrar posición
            sl_side = 'sell' if side == 'buy' else 'buy'
            
            order = await exchange.create_stop_loss(
                symbol=symbol,
                side=sl_side,
                amount=quantity,
                stop_price=stop_price
            )
            
            if order:
                logger.info(f"Stop loss establecido en ${stop_price}")
                return order
            
        except Exception as e:
            logger.error(f"Error creando stop loss: {e}")
            return None
    
    async def _create_take_profit_order(
        self,
        exchange,
        symbol: str,
        side: str,
        quantity: float,
        price: float
    ):
        """Crear orden de take profit"""
        try:
            # Invertir lado para cerrar posición
            tp_side = 'sell' if side == 'buy' else 'buy'
            
            order = await exchange.create_take_profit(
                symbol=symbol,
                side=tp_side,
                amount=quantity,
                price=price
            )
            
            if order:
                logger.info(f"Take profit establecido en ${price}")
                return order
            
        except Exception as e:
            logger.error(f"Error creando take profit: {e}")
            return None
    
    async def cancel_order(
        self,
        order_id: str,
        symbol: str,
        exchange_id: str = None
    ) -> bool:
        """Cancelar orden"""
        try:
            if exchange_id is None:
                exchange_id = list(self.exchanges.keys())[0]
            
            exchange = self.exchanges[exchange_id]
            
            success = await exchange.cancel_order(order_id, symbol)
            
            if success and order_id in self.active_orders:
                del self.active_orders[order_id]
                logger.info(f"Orden {order_id} cancelada")
            
            return success
            
        except Exception as e:
            logger.error(f"Error cancelando orden: {e}")
            return False
    
    async def modify_stop_loss(
        self,
        symbol: str,
        new_stop_price: float,
        exchange_id: str = None
    ):
        """Modificar stop loss de posición abierta"""
        # Encontrar orden de stop loss activa para el símbolo
        # Cancelar y crear nueva
        pass
    
    async def get_order_status(
        self,
        order_id: str,
        symbol: str,
        exchange_id: str = None
    ) -> Optional[Dict]:
        """Obtener estado de orden"""
        try:
            if exchange_id is None:
                exchange_id = list(self.exchanges.keys())[0]
            
            exchange = self.exchanges[exchange_id]
            
            # CCXT no tiene método directo, usar fetch_open_orders
            orders = await exchange.get_open_orders(symbol)
            
            for order in orders:
                if order['id'] == order_id:
                    return order
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo estado de orden: {e}")
            return None
    
    def get_active_orders(self) -> Dict:
        """Obtener órdenes activas"""
        return self.active_orders.copy()
    
    def get_order_history(self) -> list:
        """Obtener historial de órdenes"""
        return self.order_history.copy()