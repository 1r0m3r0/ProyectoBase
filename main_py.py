"""
TRADING BOT - MAIN ENTRY POINT
Punto de entrada principal del bot de trading
"""

import asyncio
import signal
import sys
from pathlib import Path
from loguru import logger
from typing import Optional

# Importar módulos del bot
from config.secrets import load_config
from core.engine import TradingEngine
from utils.logger import setup_logger
from visualization.dashboard import run_dashboard

class TradingBot:
    """
    Clase principal del bot de trading
    """
    
    def __init__(self, mode: str = "production", config_path: Optional[str] = None):
        """
        Inicializar el bot
        
        Args:
            mode: 'production', 'testnet', 'backtest', 'paper'
            config_path: Ruta al archivo de configuración
        """
        self.mode = mode
        self.config_path = config_path or "config/config.yaml"
        self.engine: Optional[TradingEngine] = None
        self.running = False
        
        # Setup logging
        setup_logger(mode)
        logger.info(f"Iniciando Trading Bot en modo: {mode}")
        
    async def initialize(self):
        """Inicializar componentes del bot"""
        try:
            # Cargar configuración
            config = load_config(self.config_path)
            logger.info("Configuración cargada exitosamente")
            
            # Validar modo
            if self.mode == "production" and not config.get("production_enabled", False):
                logger.error("Modo producción no habilitado en config")
                return False
            
            # Inicializar motor de trading
            self.engine = TradingEngine(config, self.mode)
            await self.engine.initialize()
            
            logger.success("Bot inicializado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al inicializar bot: {e}")
            return False
    
    async def start(self):
        """Iniciar el bot"""
        if not await self.initialize():
            logger.error("Fallo en inicialización, abortando")
            return
        
        self.running = True
        logger.info("🚀 Bot iniciado y operando")
        
        try:
            # Loop principal
            await self.engine.run()
            
        except KeyboardInterrupt:
            logger.warning("Interrupción manual detectada")
        except Exception as e:
            logger.error(f"Error crítico en loop principal: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Apagado seguro del bot"""
        logger.info("Iniciando apagado seguro...")
        self.running = False
        
        if self.engine:
            await self.engine.shutdown()
        
        logger.success("Bot detenido correctamente")
    
    def handle_signal(self, signum, frame):
        """Manejar señales del sistema"""
        logger.warning(f"Señal {signum} recibida, iniciando apagado...")
        asyncio.create_task(self.shutdown())


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Trading Bot Algorítmico")
    parser.add_argument(
        "--mode",
        choices=["production", "testnet", "paper", "backtest"],
        default="testnet",
        help="Modo de operación"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Ruta al archivo de configuración"
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Iniciar dashboard de visualización"
    )
    parser.add_argument(
        "--no-trading",
        action="store_true",
        help="Solo monitoreo, sin trading"
    )
    
    args = parser.parse_args()
    
    # Crear instancia del bot
    bot = TradingBot(mode=args.mode, config_path=args.config)
    
    # Configurar manejadores de señales
    signal.signal(signal.SIGINT, bot.handle_signal)
    signal.signal(signal.SIGTERM, bot.handle_signal)
    
    # Iniciar dashboard en proceso separado si se solicita
    if args.dashboard:
        import multiprocessing
        dashboard_process = multiprocessing.Process(target=run_dashboard)
        dashboard_process.start()
    
    # Iniciar bot
    try:
        asyncio.run(bot.start())
    except Exception as e:
        logger.critical(f"Error fatal: {e}")
        sys.exit(1)
    finally:
        if args.dashboard:
            dashboard_process.terminate()


if __name__ == "__main__":
    main()