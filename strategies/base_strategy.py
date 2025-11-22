"""
CLASE BASE PARA ESTRATEGIAS DE TRADING
Todas las estrategias personalizadas deben heredar de esta clase
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from loguru import logger


class SignalType(Enum):
    """Tipos de señales de trading"""
    LONG = "long"
    SHORT = "short"
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"


@dataclass
class TradingSignal:
    """
    Señal de trading generada por una estrategia
    """
    signal: SignalType
    symbol: str
    timeframe: str
    price: float
    timestamp: pd.Timestamp
    confidence: float  # 0.0 a 1.0
    strategy_name: str
    metadata: Dict = None  # Datos adicionales (indicadores, etc)
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseStrategy(ABC):
    """
    Clase base abstracta para estrategias de trading
    
    Ejemplo de uso:
    ```python
    class MyCustomStrategy(BaseStrategy):
        def __init__(self, params):
            super().__init__(name="MyStrategy", params=params)
            
        def calculate_indicators(self, df):
            df['rsi'] = ta.rsi(df['close'], length=self.params['rsi_period'])
            return df
            
        def generate_signal(self, df):
            if df['rsi'].iloc[-1] < 30:
                return self.create_signal(SignalType.LONG, df)
            elif df['rsi'].iloc[-1] > 70:
                return self.create_signal(SignalType.SHORT, df)
            return self.create_signal(SignalType.HOLD, df)
    ```
    """
    
    def __init__(
        self,
        name: str,
        params: Dict,
        timeframe: str = "5m",
        symbols: List[str] = None
    ):
        """
        Inicializar estrategia base
        
        Args:
            name: Nombre de la estrategia
            params: Parámetros de configuración
            timeframe: Temporalidad (1m, 5m, 15m, 1h, etc)
            symbols: Lista de símbolos a operar
        """
        self.name = name
        self.params = params
        self.timeframe = timeframe
        self.symbols = symbols or []
        self.is_active = True
        
        # Validar parámetros
        self.validate_params()
        
        logger.info(f"Estrategia {self.name} inicializada en {self.timeframe}")
    
    @abstractmethod
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcular indicadores técnicos
        
        Args:
            df: DataFrame con columnas OHLCV
            
        Returns:
            DataFrame con indicadores agregados
        """
        pass
    
    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> TradingSignal:
        """
        Generar señal de trading basada en datos actuales
        
        Args:
            df: DataFrame con OHLCV e indicadores
            
        Returns:
            TradingSignal con la decisión de trading
        """
        pass
    
    def validate_params(self) -> bool:
        """
        Validar que los parámetros sean correctos
        Override en estrategias específicas
        
        Returns:
            True si válidos, False caso contrario
        """
        return True
    
    def create_signal(
        self,
        signal_type: SignalType,
        df: pd.DataFrame,
        confidence: float = 1.0,
        metadata: Dict = None
    ) -> TradingSignal:
        """
        Helper para crear señales de trading
        
        Args:
            signal_type: Tipo de señal
            df: DataFrame con datos
            confidence: Nivel de confianza (0.0 - 1.0)
            metadata: Información adicional
            
        Returns:
            TradingSignal configurada
        """
        return TradingSignal(
            signal=signal_type,
            symbol=df.attrs.get('symbol', 'UNKNOWN'),
            timeframe=self.timeframe,
            price=df['close'].iloc[-1],
            timestamp=df.index[-1],
            confidence=confidence,
            strategy_name=self.name,
            metadata=metadata or {}
        )
    
    def analyze(self, df: pd.DataFrame) -> TradingSignal:
        """
        Pipeline completo de análisis
        
        Args:
            df: DataFrame con datos OHLCV
            
        Returns:
            Señal de trading generada
        """
        if not self.is_active:
            return self.create_signal(SignalType.HOLD, df, confidence=0.0)
        
        try:
            # Calcular indicadores
            df = self.calculate_indicators(df)
            
            # Generar señal
            signal = self.generate_signal(df)
            
            return signal
            
        except Exception as e:
            logger.error(f"Error en {self.name}: {e}")
            return self.create_signal(SignalType.HOLD, df, confidence=0.0)
    
    def enable(self):
        """Activar estrategia"""
        self.is_active = True
        logger.info(f"Estrategia {self.name} activada")
    
    def disable(self):
        """Desactivar estrategia"""
        self.is_active = False
        logger.info(f"Estrategia {self.name} desactivada")
    
    def update_params(self, new_params: Dict):
        """
        Actualizar parámetros en caliente
        
        Args:
            new_params: Diccionario con nuevos parámetros
        """
        self.params.update(new_params)
        self.validate_params()
        logger.info(f"Parámetros de {self.name} actualizados")
    
    def get_required_history(self) -> int:
        """
        Número de velas históricas requeridas
        Override en estrategias que necesiten más datos
        
        Returns:
            Número de períodos necesarios
        """
        return 100  # Default
    
    def __str__(self) -> str:
        return f"Strategy({self.name}, {self.timeframe}, active={self.is_active})"
    
    def __repr__(self) -> str:
        return self.__str__()


# ===================================
# EJEMPLO DE ESTRATEGIA PERSONALIZADA
# ===================================

class ExampleRSIStrategy(BaseStrategy):
    """
    Estrategia de ejemplo usando RSI
    """
    
    def __init__(self, params: Dict = None):
        default_params = {
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'min_confidence': 0.6
        }
        
        if params:
            default_params.update(params)
        
        super().__init__(
            name="RSI_Strategy",
            params=default_params,
            timeframe="5m"
        )
    
    def validate_params(self) -> bool:
        """Validar parámetros específicos"""
        assert 0 < self.params['rsi_oversold'] < 50
        assert 50 < self.params['rsi_overbought'] < 100
        return True
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular RSI"""
        import pandas_ta as ta
        
        # Calcular RSI
        df['rsi'] = ta.rsi(
            df['close'],
            length=self.params['rsi_period']
        )
        
        return df
    
    def generate_signal(self, df: pd.DataFrame) -> TradingSignal:
        """Generar señal basada en RSI"""
        rsi_current = df['rsi'].iloc[-1]
        rsi_prev = df['rsi'].iloc[-2]
        
        # Señal LONG: RSI sale de sobreventa
        if (rsi_prev < self.params['rsi_oversold'] and 
            rsi_current > self.params['rsi_oversold']):
            
            confidence = min(
                1.0,
                (self.params['rsi_oversold'] - rsi_current) / 20 + 0.5
            )
            
            return self.create_signal(
                SignalType.LONG,
                df,
                confidence=confidence,
                metadata={'rsi': rsi_current}
            )
        
        # Señal SHORT: RSI sale de sobrecompra
        elif (rsi_prev > self.params['rsi_overbought'] and 
              rsi_current < self.params['rsi_overbought']):
            
            confidence = min(
                1.0,
                (rsi_current - self.params['rsi_overbought']) / 20 + 0.5
            )
            
            return self.create_signal(
                SignalType.SHORT,
                df,
                confidence=confidence,
                metadata={'rsi': rsi_current}
            )
        
        # HOLD por defecto
        return self.create_signal(
            SignalType.HOLD,
            df,
            confidence=0.0,
            metadata={'rsi': rsi_current}
        )