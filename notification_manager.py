"""
NOTIFICATION MANAGER
Sistema unificado de notificaciones (Telegram, Email, SMS, WhatsApp)
"""

from typing import Dict, List, Optional
from enum import Enum
from loguru import logger
import asyncio
from datetime import datetime


class NotificationPriority(Enum):
    """Prioridad de notificaciones"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationEvent(Enum):
    """Tipos de eventos notificables"""
    TRADE_ENTRY = "trade_entry"
    TRADE_EXIT = "trade_exit"
    STOP_LOSS_HIT = "stop_loss_hit"
    TAKE_PROFIT_HIT = "take_profit_hit"
    DAILY_SUMMARY = "daily_summary"
    ERROR = "error"
    CRITICAL_ERROR = "critical_error"
    BOT_STARTED = "bot_started"
    BOT_STOPPED = "bot_stopped"
    CAPITAL_WARNING = "capital_warning"
    DRAWDOWN_WARNING = "drawdown_warning"


class NotificationManager:
    """
    Gestor centralizado de notificaciones
    Coordina envío por múltiples canales
    """
    
    def __init__(self, config: Dict):
        """
        Inicializar notification manager
        
        Args:
            config: Configuración de notificaciones
        """
        self.config = config
        self.notifiers = {}
        
        self._initialize_notifiers()
        logger.info("NotificationManager inicializado")
    
    def _initialize_notifiers(self):
        """Inicializar notificadores activos"""
        # Telegram
        if self.config.get('telegram', {}).get('enabled'):
            from .telegram_notifier import TelegramNotifier
            self.notifiers['telegram'] = TelegramNotifier(
                self.config['telegram']
            )
        
        # Email
        if self.config.get('email', {}).get('enabled'):
            from .email_notifier import EmailNotifier
            self.notifiers['email'] = EmailNotifier(
                self.config['email']
            )
        
        # SMS
        if self.config.get('sms', {}).get('enabled'):
            from .sms_notifier import SMSNotifier
            self.notifiers['sms'] = SMSNotifier(
                self.config['sms']
            )
        
        # WhatsApp
        if self.config.get('whatsapp', {}).get('enabled'):
            from .whatsapp_notifier import WhatsAppNotifier
            self.notifiers['whatsapp'] = WhatsAppNotifier(
                self.config['whatsapp']
            )
        
        logger.info(f"Notificadores activos: {list(self.notifiers.keys())}")
    
    # ===================================
    # ENVÍO DE NOTIFICACIONES
    # ===================================
    
    async def send(
        self,
        event: NotificationEvent,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: Optional[Dict] = None
    ):
        """
        Enviar notificación por todos los canales configurados
        
        Args:
            event: Tipo de evento
            message: Mensaje a enviar
            priority: Prioridad
            data: Datos adicionales
        """
        # Verificar si el evento está habilitado
        if not self._should_notify(event):
            return
        
        # Formatear mensaje con prioridad
        formatted_message = self._format_message(message, priority, event)
        
        # Enviar por todos los notificadores
        tasks = []
        for name, notifier in self.notifiers.items():
            task = notifier.send(formatted_message, data)
            tasks.append(task)
        
        # Ejecutar en paralelo
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def _should_notify(self, event: NotificationEvent) -> bool:
        """Verificar si evento debe notificarse"""
        # Verificar en configuración de cada notificador
        for notifier_config in self.config.values():
            if isinstance(notifier_config, dict) and 'events' in notifier_config:
                if event.value in notifier_config['events']:
                    return True
        return False
    
    def _format_message(
        self,
        message: str,
        priority: NotificationPriority,
        event: NotificationEvent
    ) -> str:
        """Formatear mensaje con iconos y timestamp"""
        # Iconos según prioridad
        icons = {
            NotificationPriority.LOW: "ℹ️",
            NotificationPriority.NORMAL: "📊",
            NotificationPriority.HIGH: "⚠️",
            NotificationPriority.CRITICAL: "🚨"
        }
        
        icon = icons.get(priority, "📊")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return f"{icon} [{event.value.upper()}] {timestamp}\n{message}"
    
    # ===================================
    # NOTIFICACIONES ESPECÍFICAS
    # ===================================
    
    async def notify_trade_entry(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: float,
        strategy: str
    ):
        """Notificar entrada a operación"""
        message = (
            f"🔵 ENTRADA DE POSICIÓN\n"
            f"Par: {symbol}\n"
            f"Lado: {side.upper()}\n"
            f"Precio: ${price:.4f}\n"
            f"Cantidad: {quantity:.6f}\n"
            f"Estrategia: {strategy}"
        )
        
        await self.send(
            NotificationEvent.TRADE_ENTRY,
            message,
            NotificationPriority.NORMAL,
            {
                'symbol': symbol,
                'side': side,
                'price': price,
                'quantity': quantity
            }
        )
    
    async def notify_trade_exit(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        pnl: float,
        pnl_percentage: float
    ):
        """Notificar salida de operación"""
        emoji = "🟢" if pnl > 0 else "🔴"
        
        message = (
            f"{emoji} CIERRE DE POSICIÓN\n"
            f"Par: {symbol}\n"
            f"Lado: {side.upper()}\n"
            f"Entrada: ${entry_price:.4f}\n"
            f"Salida: ${exit_price:.4f}\n"
            f"Cantidad: {quantity:.6f}\n"
            f"P&L: ${pnl:+.2f} ({pnl_percentage:+.2f}%)"
        )
        
        priority = (NotificationPriority.HIGH if abs(pnl_percentage) > 5
                   else NotificationPriority.NORMAL)
        
        await self.send(
            NotificationEvent.TRADE_EXIT,
            message,
            priority,
            {
                'symbol': symbol,
                'pnl': pnl,
                'pnl_percentage': pnl_percentage
            }
        )
    
    async def notify_stop_loss(
        self,
        symbol: str,
        price: float,
        loss: float
    ):
        """Notificar activación de stop loss"""
        message = (
            f"🛑 STOP LOSS ACTIVADO\n"
            f"Par: {symbol}\n"
            f"Precio: ${price:.4f}\n"
            f"Pérdida: ${loss:.2f}"
        )
        
        await self.send(
            NotificationEvent.STOP_LOSS_HIT,
            message,
            NotificationPriority.HIGH,
            {'symbol': symbol, 'loss': loss}
        )
    
    async def notify_take_profit(
        self,
        symbol: str,
        price: float,
        profit: float
    ):
        """Notificar activación de take profit"""
        message = (
            f"✅ TAKE PROFIT ALCANZADO\n"
            f"Par: {symbol}\n"
            f"Precio: ${price:.4f}\n"
            f"Ganancia: ${profit:.2f}"
        )
        
        await self.send(
            NotificationEvent.TAKE_PROFIT_HIT,
            message,
            NotificationPriority.NORMAL,
            {'symbol': symbol, 'profit': profit}
        )
    
    async def notify_daily_summary(
        self,
        total_trades: int,
        winning_trades: int,
        losing_trades: int,
        total_pnl: float,
        win_rate: float
    ):
        """Notificar resumen diario"""
        message = (
            f"📊 RESUMEN DIARIO\n"
            f"Trades totales: {total_trades}\n"
            f"Ganadores: {winning_trades}\n"
            f"Perdedores: {losing_trades}\n"
            f"Win Rate: {win_rate:.1f}%\n"
            f"P&L Total: ${total_pnl:+.2f}"
        )
        
        priority = (NotificationPriority.HIGH if total_pnl < -100
                   else NotificationPriority.NORMAL)
        
        await self.send(
            NotificationEvent.DAILY_SUMMARY,
            message,
            priority
        )
    
    async def notify_error(self, error_message: str, critical: bool = False):
        """Notificar error"""
        event = (NotificationEvent.CRITICAL_ERROR if critical
                else NotificationEvent.ERROR)
        
        priority = (NotificationPriority.CRITICAL if critical
                   else NotificationPriority.HIGH)
        
        message = f"❌ ERROR\n{error_message}"
        
        await self.send(event, message, priority)
    
    async def notify_bot_started(self, mode: str):
        """Notificar inicio del bot"""
        message = (
            f"🚀 BOT INICIADO\n"
            f"Modo: {mode.upper()}\n"
            f"Timestamp: {datetime.now()}"
        )
        
        await self.send(
            NotificationEvent.BOT_STARTED,
            message,
            NotificationPriority.NORMAL
        )
    
    async def notify_bot_stopped(self, reason: Optional[str] = None):
        """Notificar detención del bot"""
        message = f"🛑 BOT DETENIDO"
        if reason:
            message += f"\nRazón: {reason}"
        
        await self.send(
            NotificationEvent.BOT_STOPPED,
            message,
            NotificationPriority.HIGH
        )
    
    async def notify_capital_warning(self, available: float, threshold: float):
        """Notificar advertencia de capital bajo"""
        message = (
            f"⚠️ ADVERTENCIA DE CAPITAL\n"
            f"Capital disponible: ${available:.2f}\n"
            f"Por debajo del umbral: ${threshold:.2f}"
        )
        
        await self.send(
            NotificationEvent.CAPITAL_WARNING,
            message,
            NotificationPriority.HIGH
        )
    
    async def notify_drawdown_warning(self, current_dd: float, max_dd: float):
        """Notificar advertencia de drawdown"""
        message = (
            f"⚠️ ADVERTENCIA DE DRAWDOWN\n"
            f"Drawdown actual: {current_dd:.2f}%\n"
            f"Límite máximo: {max_dd:.2f}%"
        )
        
        await self.send(
            NotificationEvent.DRAWDOWN_WARNING,
            message,
            NotificationPriority.CRITICAL
        )
    
    # ===================================
    # GESTIÓN
    # ===================================
    
    async def test_notifications(self):
        """Enviar notificación de prueba"""
        message = "🧪 Prueba de notificaciones - Sistema funcionando correctamente"
        
        for name, notifier in self.notifiers.items():
            try:
                await notifier.send(message)
                logger.success(f"Notificación de prueba enviada via {name}")
            except Exception as e:
                logger.error(f"Error enviando prueba via {name}: {e}")
    
    def get_active_channels(self) -> List[str]:
        """Obtener canales activos"""
        return list(self.notifiers.keys())
    
    async def close(self):
        """Cerrar todos los notificadores"""
        for notifier in self.notifiers.values():
            if hasattr(notifier, 'close'):
                await notifier.close()
        
        logger.info("Notificadores cerrados")