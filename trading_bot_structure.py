"""
ESTRUCTURA COMPLETA DEL BOT DE TRADING ALGORÍTMICO
===================================================

trading_bot/
│
├── main.py                          # Punto de entrada principal
├── requirements.txt                 # Dependencias del proyecto
├── Dockerfile                       # Containerización
├── docker-compose.yml               # Orquestación multi-servicio
├── .env.example                     # Template de variables de entorno
├── README.md                        # Documentación principal
│
├── config/                          # ⚙️ CONFIGURACIONES
│   ├── __init__.py
│   ├── config.yaml                  # Configuración principal
│   ├── exchanges.yaml               # Configuración de exchanges
│   ├── strategies.yaml              # Parámetros de estrategias
│   ├── risk_management.yaml         # Reglas de riesgo
│   ├── notifications.yaml           # Configuración de alertas
│   └── secrets.py                   # Gestor de credenciales encriptadas
│
├── core/                            # 🎯 MOTOR PRINCIPAL
│   ├── __init__.py
│   ├── engine.py                    # Motor de ejecución principal
│   ├── order_manager.py             # Gestor de órdenes
│   ├── position_tracker.py          # Seguimiento de posiciones
│   ├── state_manager.py             # Estado del bot (activo/pausado)
│   └── health_monitor.py            # Monitor de salud del sistema
│
├── exchange_connector/              # 🔌 CONECTORES DE EXCHANGES
│   ├── __init__.py
│   ├── base_connector.py            # Clase base abstracta
│   ├── ccxt_connector.py            # Implementación CCXT (REST API)
│   ├── binance_websocket.py         # WebSocket Binance
│   ├── bybit_websocket.py           # WebSocket Bybit
│   ├── exchange_factory.py          # Factory pattern para exchanges
│   └── rate_limiter.py              # Control de rate limits
│
├── data_handler/                    # 📊 GESTIÓN DE DATOS
│   ├── __init__.py
│   ├── data_manager.py              # Coordinador principal de datos
│   ├── database/
│   │   ├── __init__.py
│   │   ├── base_db.py               # Interface base de datos
│   │   ├── csv_handler.py           # Almacenamiento CSV
│   │   ├── json_handler.py          # Almacenamiento JSON
│   │   ├── mongodb_handler.py       # Integración MongoDB
│   │   └── postgresql_handler.py    # Integración PostgreSQL
│   ├── historical_downloader.py     # Descarga de datos históricos
│   ├── live_data_feed.py            # Feed de datos en tiempo real
│   └── data_preprocessor.py         # Limpieza y preparación de datos
│
├── strategies/                      # 📈 ESTRATEGIAS DE TRADING
│   ├── __init__.py
│   ├── base_strategy.py             # Clase base abstracta
│   ├── strategy_loader.py           # Cargador dinámico de estrategias
│   ├── signal_combiner.py           # Combinador de múltiples señales
│   ├── examples/                    # Estrategias de ejemplo
│   │   ├── __init__.py
│   │   ├── rsi_strategy.py
│   │   ├── ema_crossover.py
│   │   ├── bollinger_bands.py
│   │   ├── volume_profile.py
│   │   └── custom_scalping.py
│   └── user_strategies/             # Carpeta para estrategias personalizadas
│       └── __init__.py
│
├── risk_management/                 # 🛡️ GESTIÓN DE RIESGO
│   ├── __init__.py
│   ├── risk_manager.py              # Coordinador de riesgo
│   ├── position_sizer.py            # Cálculo de tamaño de posición
│   ├── stop_loss_manager.py         # Gestión de stop loss
│   ├── take_profit_manager.py       # Gestión de take profit
│   ├── trailing_stop.py             # Trailing stop dinámico
│   ├── break_even.py                # Break even automático
│   ├── drawdown_monitor.py          # Monitor de drawdown
│   ├── daily_limits.py              # Límites diarios/semanales
│   └── circuit_breaker.py           # Sistema de parada de emergencia
│
├── portfolio_manager/               # 💼 GESTIÓN DE PORTAFOLIO
│   ├── __init__.py
│   ├── capital_allocator.py         # Distribución de capital
│   ├── multi_market_manager.py      # Gestor spot/futures USD/COIN
│   ├── rebalancer.py                # Rebalanceo automático
│   ├── correlation_analyzer.py      # Análisis de correlaciones
│   └── exposure_calculator.py       # Cálculo de exposición total
│
├── backtesting/                     # 🔬 BACKTESTING
│   ├── __init__.py
│   ├── backtest_engine.py           # Motor de backtesting
│   ├── event_simulator.py           # Simulador de eventos de mercado
│   ├── slippage_model.py            # Modelo de slippage
│   ├── commission_model.py          # Modelo de comisiones
│   ├── performance_analyzer.py      # Análisis de rendimiento
│   └── optimization/
│       ├── __init__.py
│       ├── parameter_optimizer.py   # Optimización de parámetros
│       └── walk_forward.py          # Walk-forward optimization
│
├── visualization/                   # 📱 VISUALIZACIÓN
│   ├── __init__.py
│   ├── dashboard.py                 # Dashboard principal (Streamlit)
│   ├── charts/
│   │   ├── __init__.py
│   │   ├── price_chart.py           # Gráficos de precio
│   │   ├── performance_chart.py     # Gráficos de rendimiento
│   │   └── risk_metrics_chart.py    # Gráficos de métricas de riesgo
│   └── mobile_api/                  # API para app móvil
│       ├── __init__.py
│       ├── fastapi_server.py        # Servidor FastAPI
│       └── endpoints.py             # Endpoints REST
│
├── notifications/                   # 🔔 SISTEMA DE NOTIFICACIONES
│   ├── __init__.py
│   ├── notification_manager.py      # Coordinador de notificaciones
│   ├── telegram_notifier.py         # Integración Telegram
│   ├── email_notifier.py            # Integración Email
│   ├── sms_notifier.py              # Integración SMS (Twilio)
│   ├── whatsapp_notifier.py         # Integración WhatsApp
│   └── notification_queue.py        # Cola de notificaciones
│
├── utils/                           # 🔧 UTILIDADES
│   ├── __init__.py
│   ├── logger.py                    # Sistema de logging avanzado
│   ├── encryption.py                # Encriptación de credenciales
│   ├── validators.py                # Validadores de datos
│   ├── time_utils.py                # Utilidades de tiempo/timezone
│   └── math_utils.py                # Funciones matemáticas
│
├── tests/                           # 🧪 PRUEBAS
│   ├── __init__.py
│   ├── unit/                        # Pruebas unitarias
│   ├── integration/                 # Pruebas de integración
│   └── fixtures/                    # Datos de prueba
│
├── scripts/                         # 📜 SCRIPTS AUXILIARES
│   ├── setup_database.py            # Inicialización de DB
│   ├── download_historical.py       # Descarga de datos históricos
│   ├── encrypt_credentials.py       # Encriptación de API keys
│   └── health_check.py              # Verificación de sistema
│
├── logs/                            # 📝 LOGS (generados)
│   ├── trades/
│   ├── errors/
│   └── system/
│
├── data/                            # 💾 DATOS (generados)
│   ├── historical/                  # Datos históricos
│   ├── cache/                       # Cache temporal
│   └── backtest_results/            # Resultados de backtesting
│
└── mobile_app/                      # 📱 APLICACIÓN MÓVIL (opcional)
    ├── flutter_app/                 # App Flutter para iOS/Android
    │   ├── lib/
    │   ├── android/
    │   └── ios/
    └── api_documentation.md         # Documentación de API

"""