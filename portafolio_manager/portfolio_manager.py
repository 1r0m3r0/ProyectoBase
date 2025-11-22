"""
PORTFOLIO MANAGER - CAPITAL ALLOCATOR
Gestiona distribución de capital entre mercados (Spot, Futures USD/COIN)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger
from enum import Enum


class MarketType(Enum):
    """Tipos de mercado"""
    SPOT = "spot"
    FUTURES_USD = "futures_usd"
    FUTURES_COIN = "futures_coin"
    RESERVE = "reserve"


@dataclass
class MarketAllocation:
    """Asignación de capital por mercado"""
    market_type: MarketType
    percentage: float  # % del capital total
    capital_allocated: float  # USD asignados
    capital_available: float  # USD disponibles
    capital_in_use: float  # USD en posiciones
    enabled: bool = True


class CapitalAllocator:
    """
    Gestor de distribución de capital
    Controla asignación entre Spot, Futures USD-M, Futures COIN-M y Reserva
    """
    
    def __init__(self, config: Dict):
        """
        Inicializar allocator
        
        Args:
            config: Configuración de portfolio
        """
        self.config = config
        self.total_capital = config['total_capital']
        self.allocations = {}
        
        self._initialize_allocations()
        logger.info("CapitalAllocator inicializado")
    
    def _initialize_allocations(self):
        """Inicializar distribución de capital"""
        allocation_config = self.config['allocation']
        
        for market_str, percentage in allocation_config.items():
            market_type = self._str_to_market_type(market_str)
            capital = (self.total_capital * percentage) / 100
            
            self.allocations[market_type] = MarketAllocation(
                market_type=market_type,
                percentage=percentage,
                capital_allocated=capital,
                capital_available=capital,
                capital_in_use=0.0
            )
        
        self._log_allocations()
    
    def _str_to_market_type(self, market_str: str) -> MarketType:
        """Convertir string a MarketType"""
        mapping = {
            'spot': MarketType.SPOT,
            'futures_usd': MarketType.FUTURES_USD,
            'futures_coin': MarketType.FUTURES_COIN,
            'reserve': MarketType.RESERVE
        }
        return mapping.get(market_str, MarketType.RESERVE)
    
    # ===================================
    # GESTIÓN DE CAPITAL
    # ===================================
    
    def allocate_capital(
        self,
        market_type: MarketType,
        amount: float
    ) -> bool:
        """
        Asignar capital de un mercado para una operación
        
        Args:
            market_type: Tipo de mercado
            amount: Cantidad a asignar
            
        Returns:
            True si se pudo asignar, False si no hay suficiente
        """
        if market_type not in self.allocations:
            logger.error(f"Tipo de mercado {market_type} no existe")
            return False
        
        allocation = self.allocations[market_type]
        
        if not allocation.enabled:
            logger.warning(f"Mercado {market_type.value} deshabilitado")
            return False
        
        if amount > allocation.capital_available:
            logger.warning(
                f"Capital insuficiente en {market_type.value}: "
                f"Requerido ${amount:.2f}, Disponible ${allocation.capital_available:.2f}"
            )
            return False
        
        # Asignar
        allocation.capital_available -= amount
        allocation.capital_in_use += amount
        
        logger.info(
            f"Capital asignado en {market_type.value}: ${amount:.2f} "
            f"(Disponible: ${allocation.capital_available:.2f})"
        )
        
        return True
    
    def release_capital(
        self,
        market_type: MarketType,
        amount: float,
        pnl: float = 0.0
    ):
        """
        Liberar capital al cerrar posición
        
        Args:
            market_type: Tipo de mercado
            amount: Capital original de la posición
            pnl: Profit/Loss de la operación
        """
        if market_type not in self.allocations:
            return
        
        allocation = self.allocations[market_type]
        
        # Liberar capital + P&L
        returned_capital = amount + pnl
        allocation.capital_available += returned_capital
        allocation.capital_in_use -= amount
        
        # Actualizar capital total
        self.total_capital += pnl
        
        logger.info(
            f"Capital liberado en {market_type.value}: ${returned_capital:.2f} "
            f"(P&L: ${pnl:+.2f})"
        )
    
    def transfer_between_markets(
        self,
        from_market: MarketType,
        to_market: MarketType,
        amount: float
    ) -> bool:
        """
        Transferir capital entre mercados
        
        Args:
            from_market: Mercado origen
            to_market: Mercado destino
            amount: Cantidad a transferir
            
        Returns:
            True si exitoso
        """
        if from_market not in self.allocations or to_market not in self.allocations:
            logger.error("Mercados inválidos para transferencia")
            return False
        
        from_alloc = self.allocations[from_market]
        to_alloc = self.allocations[to_market]
        
        if amount > from_alloc.capital_available:
            logger.error("Capital insuficiente para transferencia")
            return False
        
        # Realizar transferencia
        from_alloc.capital_available -= amount
        from_alloc.capital_allocated -= amount
        to_alloc.capital_available += amount
        to_alloc.capital_allocated += amount
        
        # Actualizar porcentajes
        from_alloc.percentage = (from_alloc.capital_allocated / self.total_capital) * 100
        to_alloc.percentage = (to_alloc.capital_allocated / self.total_capital) * 100
        
        logger.info(
            f"Transferidos ${amount:.2f} de {from_market.value} a {to_market.value}"
        )
        
        return True
    
    # ===================================
    # REBALANCEO
    # ===================================
    
    def check_rebalance_needed(self) -> bool:
        """
        Verificar si se necesita rebalanceo
        
        Returns:
            True si las asignaciones actuales difieren del objetivo
        """
        if not self.config['rebalancing']['enabled']:
            return False
        
        threshold = self.config['rebalancing']['threshold_percentage']
        
        for market_type, allocation in self.allocations.items():
            target_pct = self.config['allocation'][market_type.value]
            current_pct = (allocation.capital_allocated / self.total_capital) * 100
            
            diff = abs(current_pct - target_pct)
            if diff > threshold:
                logger.info(
                    f"Rebalanceo necesario en {market_type.value}: "
                    f"Target {target_pct}%, Actual {current_pct:.2f}%"
                )
                return True
        
        return False
    
    def rebalance(self):
        """
        Rebalancear distribución de capital
        Ajusta asignaciones a porcentajes objetivo
        """
        logger.info("Iniciando rebalanceo de portfolio...")
        
        target_config = self.config['allocation']
        
        for market_str, target_pct in target_config.items():
            market_type = self._str_to_market_type(market_str)
            allocation = self.allocations[market_type]
            
            # Capital objetivo
            target_capital = (self.total_capital * target_pct) / 100
            
            # Diferencia
            diff = target_capital - allocation.capital_allocated
            
            if diff > 0:
                # Necesita más capital - tomar de reserve
                if self._can_take_from_reserve(diff):
                    self.transfer_between_markets(
                        MarketType.RESERVE,
                        market_type,
                        diff
                    )
            elif diff < 0:
                # Sobra capital - mover a reserve
                available_to_move = min(abs(diff), allocation.capital_available)
                if available_to_move > 0:
                    self.transfer_between_markets(
                        market_type,
                        MarketType.RESERVE,
                        available_to_move
                    )
        
        logger.success("Rebalanceo completado")
        self._log_allocations()
    
    def _can_take_from_reserve(self, amount: float) -> bool:
        """Verificar si hay suficiente en reserva"""
        reserve = self.allocations.get(MarketType.RESERVE)
        if reserve:
            return reserve.capital_available >= amount
        return False
    
    # ===================================
    # ENABLE/DISABLE MERCADOS
    # ===================================
    
    def enable_market(self, market_type: MarketType):
        """Habilitar mercado"""
        if market_type in self.allocations:
            self.allocations[market_type].enabled = True
            logger.info(f"Mercado {market_type.value} habilitado")
    
    def disable_market(self, market_type: MarketType):
        """Deshabilitar mercado"""
        if market_type in self.allocations:
            self.allocations[market_type].enabled = False
            logger.warning(f"Mercado {market_type.value} deshabilitado")
    
    def enable_spot(self):
        """Habilitar trading spot"""
        self.enable_market(MarketType.SPOT)
    
    def disable_spot(self):
        """Deshabilitar trading spot"""
        self.disable_market(MarketType.SPOT)
    
    def enable_futures_usd(self):
        """Habilitar futuros USD-M"""
        self.enable_market(MarketType.FUTURES_USD)
    
    def disable_futures_usd(self):
        """Deshabilitar futuros USD-M"""
        self.disable_market(MarketType.FUTURES_USD)
    
    def enable_futures_coin(self):
        """Habilitar futuros COIN-M"""
        self.enable_market(MarketType.FUTURES_COIN)
    
    def disable_futures_coin(self):
        """Deshabilitar futuros COIN-M"""
        self.disable_market(MarketType.FUTURES_COIN)
    
    # ===================================
    # REPORTING
    # ===================================
    
    def get_allocation_summary(self) -> Dict:
        """Obtener resumen de asignaciones"""
        summary = {
            'total_capital': self.total_capital,
            'markets': {}
        }
        
        for market_type, allocation in self.allocations.items():
            summary['markets'][market_type.value] = {
                'percentage': allocation.percentage,
                'allocated': allocation.capital_allocated,
                'available': allocation.capital_available,
                'in_use': allocation.capital_in_use,
                'enabled': allocation.enabled
            }
        
        return summary
    
    def _log_allocations(self):
        """Logging de distribución actual"""
        logger.info("=== DISTRIBUCIÓN DE CAPITAL ===")
        logger.info(f"Capital Total: ${self.total_capital:.2f}")
        
        for market_type, allocation in self.allocations.items():
            logger.info(
                f"{market_type.value.upper()}: "
                f"{allocation.percentage:.1f}% "
                f"(${allocation.capital_allocated:.2f}) - "
                f"Disponible: ${allocation.capital_available:.2f}, "
                f"En uso: ${allocation.capital_in_use:.2f} "
                f"[{'✓' if allocation.enabled else '✗'}]"
            )
    
    def get_available_capital(self, market_type: MarketType) -> float:
        """Obtener capital disponible en un mercado"""
        if market_type in self.allocations:
            return self.allocations[market_type].capital_available
        return 0.0
    
    def get_total_available(self) -> float:
        """Obtener capital total disponible (todas las asignaciones)"""
        return sum(
            alloc.capital_available 
            for alloc in self.allocations.values()
        )