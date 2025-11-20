# 🤖 Trading Bot Algorítmico Profesional

Bot de trading automatizado para criptomonedas con soporte para múltiples exchanges, estrategias personalizables, gestión avanzada de riesgo y visualización en tiempo real.

## 📋 Características Principales

### ✅ **Exchanges Soportados**
- Binance (Spot, Futures USD-M, Futures COIN-M)
- Bybit (Spot, Futures)
- Conexión via CCXT (REST API)
- WebSocket para datos en tiempo real
- Testnet y Producción

### ✅ **Estrategias de Trading**
- Sistema modular de estrategias
- Máximo 5 estrategias simultáneas
- Combinación de señales múltiples
- Ejemplos incluidos: RSI, EMA Crossover, Bollinger Bands
- Fácil creación de estrategias personalizadas

### ✅ **Gestión de Riesgo**
- **Position Sizing**: Porcentaje, Fijo, Kelly Criterion, Volatilidad
- **Stop Loss**: Fijo y Dinámico (ATR)
- **Take Profit**: Fijo y basado en Risk/Reward
- **Trailing Stop**: Automático con activación configurable
- **Break Even**: Movimiento automático de stop loss
- **Límites Diarios/Semanales**: Pérdidas y número de trades
- **Max Drawdown**: Pausa automática
- **Circuit Breaker**: Detención por pérdidas consecutivas

### ✅ **Gestión de Portfolio**
- Distribución de capital entre Spot/Futures USD/COIN
- Rebalanceo automático
- Transferencias entre mercados
- Control de correlaciones
- Activación/desactivación de mercados en caliente

### ✅ **Base de Datos**
- **CSV** (por defecto)
- **JSON**
- **MongoDB**
- **PostgreSQL**
- Descarga de hasta 10 años de datos históricos
- Múltiples temporalidades (1m, 5m, 15m, 1h, 4h, 1d)

### ✅ **Backtesting Robusto**
- Simulación realista con slippage
- Comisiones configurables
- Latencia simulada
- Optimización de parámetros
- Walk-forward analysis
- Métricas completas (Sharpe, Sortino, Drawdown, etc.)

### ✅ **Notificaciones**
- **Telegram**: Alertas instantáneas
- **Email**: Reportes detallados
- **SMS**: Alertas críticas (Twilio)
- **WhatsApp**: Notificaciones importantes (Twilio)
- Eventos configurables (entradas, salidas, errores, resumen diario)

### ✅ **Visualización**
- **Dashboard Streamlit**: Tiempo real en navegador
- **API REST**: FastAPI para aplicación móvil
- Gráficos interactivos (Plotly)
- Monitoreo de rendimiento
- Historial de trades

---

## 🚀 Instalación Rápida

### Opción 1: Local (Windows/Linux/Mac)

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/trading-bot.git
cd trading-bot

# Crear entorno virtual
python -m venv venv

# Activar entorno
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys

# Inicializar base de datos
python scripts/setup_database.py

# Descargar datos históricos (opcional)
python scripts/download_historical.py

# Ejecutar en modo testnet
python main.py --mode testnet
```

### Opción 2: Docker (Recomendado para VPS)

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/trading-bot.git
cd trading-bot

# Configurar .env
cp .env.example .env
# Editar con tus credenciales

# Construir y ejecutar
docker-compose up -d

# Ver logs
docker-compose logs -f trading-bot

# Acceder al dashboard
# http://localhost:8501

# Detener
docker-compose down
```

---

## ⚙️ Configuración

### 1. API Keys de Exchange

**Binance:**
1. Ir a https://www.binance.com/en/my/settings/api-management
2. Crear nueva API Key
3. **Importante**: Habilitar permisos de trading
4. Whitelist de IP (recomendado)
5. Copiar API Key y Secret a `.env`

**Para Testnet Binance:**
- Futures Testnet: https://testnet.binancefuture.com

### 2. Configurar Estrategias

Editar `config/strategies.yaml`:

```yaml
strategies:
  max_concurrent: 5
  enabled:
    - my_custom_strategy
  
  my_custom_strategy:
    name: "MyScalpingStrategy"
    type: "scalping"
    timeframe: "5m"
    symbols:
      - BTC/USDT
      - ETH/USDT
    parameters:
      rsi_period: 14
      # ... tus parámetros
```

### 3. Ajustar Gestión de Riesgo

Editar `config/risk_management.yaml`:

```yaml
risk_management:
  position_sizing:
    method: "percentage"  # o "fixed", "kelly"
    percentage_per_trade: 2.0  # 2% por trade
  
  stop_loss:
    enabled: true
    type: "dynamic"  # o "fixed"
    fixed_percentage: 2.0
  
  daily_limits:
    max_daily_loss_percentage: 5.0
    max_daily_trades: 20
```

### 4. Configurar Notificaciones

**Telegram:**
1. Crear bot con @BotFather
2. Obtener token y chat_id
3. Configurar en `config/notifications.yaml`

```yaml
notifications:
  telegram:
    enabled: true
    bot_token: "YOUR_BOT_TOKEN"
    chat_id: "YOUR_CHAT_ID"
    events:
      - trade_entry
      - trade_exit
      - stop_loss_hit
      - daily_summary
```

---

## 📊 Crear Estrategias Personalizadas

### Ejemplo: Estrategia Simple

Crear archivo `strategies/user_strategies/my_strategy.py`:

```python
from strategies.base_strategy import BaseStrategy, SignalType, TradingSignal
import pandas as pd
import pandas_ta as ta

class MyCustomStrategy(BaseStrategy):
    """Mi estrategia personalizada"""
    
    def __init__(self, params=None):
        default_params = {
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70
        }
        if params:
            default_params.update(params)
        
        super().__init__(
            name="MyCustomStrategy",
            params=default_params,
            timeframe="5m"
        )
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular indicadores"""
        # RSI
        df['rsi'] = ta.rsi(df['close'], length=self.params['rsi_period'])
        
        # EMA
        df['ema_20'] = ta.ema(df['close'], length=20)
        
        return df
    
    def generate_signal(self, df: pd.DataFrame) -> TradingSignal:
        """Generar señal de trading"""
        rsi = df['rsi'].iloc[-1]
        close = df['close'].iloc[-1]
        ema = df['ema_20'].iloc[-1]
        
        # Condiciones LONG
        if rsi < self.params['rsi_oversold'] and close > ema:
            return self.create_signal(
                SignalType.LONG,
                df,
                confidence=0.8,
                metadata={'rsi': rsi, 'ema': ema}
            )
        
        # Condiciones SHORT
        elif rsi > self.params['rsi_overbought'] and close < ema:
            return self.create_signal(
                SignalType.SHORT,
                df,
                confidence=0.8,
                metadata={'rsi': rsi, 'ema': ema}
            )
        
        # HOLD
        return self.create_signal(SignalType.HOLD, df)
```

### Registrar Estrategia

Agregar a `config/strategies.yaml`:

```yaml
strategies:
  enabled:
    - my_custom_strategy
  
  my_custom_strategy:
    name: "MyCustomStrategy"
    type: "scalping"
    timeframe: "5m"
    symbols:
      - BTC/USDT
    parameters:
      rsi_period: 14
      rsi_oversold: 30
      rsi_overbought: 70
```

---

## 🧪 Backtesting

### Ejecutar Backtest

```python
from backtesting.backtest_engine import BacktestEngine
from strategies.user_strategies.my_strategy import MyCustomStrategy
from data_handler.data_manager import DataManager
from datetime import datetime, timedelta

# Cargar datos históricos
data_manager = DataManager(config)
data = data_manager.get_historical_data(
    symbol='BTC/USDT',
    timeframe='5m',
    start_date=datetime.now() - timedelta(days=365)
)

# Crear estrategia
strategy = MyCustomStrategy()

# Ejecutar backtest
engine = BacktestEngine(
    initial_capital=10000,
    commission_rate=0.0004,
    slippage_pct=0.05
)

results = engine.run(
    strategy=strategy,
    data=data,
    position_size_pct=2.0
)

# Ver resultados
engine.print_results(results)
```

### Optimización de Parámetros

```python
from backtesting.optimization.parameter_optimizer import ParameterOptimizer

# Definir rango de parámetros
param_grid = {
    'rsi_period': [10, 14, 20],
    'rsi_oversold': [25, 30, 35],
    'rsi_overbought': [65, 70, 75]
}

# Optimizar
optimizer = ParameterOptimizer(engine, strategy, data)
best_params = optimizer.optimize(param_grid)

print(f"Mejores parámetros: {best_params}")
```

---

## 📱 Aplicación Móvil

### API REST

El bot expone una API REST para integración con apps móviles:

**Endpoints principales:**

```
GET  /api/status          - Estado del bot
GET  /api/positions       - Posiciones abiertas
GET  /api/trades          - Historial de trades
GET  /api/performance     - Métricas de rendimiento
POST /api/pause           - Pausar bot
POST /api/resume          - Reanudar bot
GET  /api/strategies      - Estrategias activas
```

### Ejemplo de uso (Python):

```python
import requests

BASE_URL = "http://your-vps-ip:8000"

# Obtener estado
response = requests.get(f"{BASE_URL}/api/status")
print(response.json())

# Pausar bot
requests.post(f"{BASE_URL}/api/pause")
```

### Flutter App (próximamente)

En desarrollo: App móvil con Flutter para iOS/Android.

---

## 🖥️ Dashboard en Tiempo Real

### Acceso Local

```bash
# Si corriendo localmente
python main.py --dashboard

# Abrir navegador en:
http://localhost:8501
```

### Acceso Remoto (VPS)

1. Configurar reverse proxy (Nginx):

```nginx
server {
    listen 80;
    server_name tu-dominio.com;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

2. Acceder desde cualquier lugar: `http://tu-dominio.com`

---

## 🔒 Seguridad

### Mejores Prácticas

1. **API Keys**:
   - Usar solo permisos necesarios (trading, lectura)
   - NO habilitar withdrawals
   - Whitelist de IPs
   - Rotar keys regularmente

2. **VPS**:
   - Firewall configurado (solo puertos necesarios)
   - SSH con clave pública
   - Fail2ban activo
   - Updates automáticos

3. **Encriptación**:
   ```python
   # Encriptar credenciales
   python scripts/encrypt_credentials.py
   ```

4. **Testnet Primero**:
   - Probar SIEMPRE en testnet antes de producción
   - Validar estrategias con backtest
   - Empezar con capital pequeño

---

## 📈 Monitoreo y Logging

### Logs

Los logs se guardan en `logs/`:
- `trades/` - Historial de operaciones
- `errors/` - Errores del sistema
- `system/` - Estado general

### Visualizar Logs

```bash
# Tiempo real
tail -f logs/system/bot.log

# Con Docker
docker-compose logs -f trading-bot

# Filtrar errores
grep "ERROR" logs/system/bot.log
```

### Integración Sentry (Opcional)

Para monitoreo de errores en producción:

```yaml
# config/config.yaml
logging:
  sentry:
    enabled: true
    dsn: "your_sentry_dsn"
```

---

## 🛠️ Troubleshooting

### Problema: Bot no conecta a exchange

```bash
# Verificar API keys
python scripts/test_connection.py

# Revisar logs
tail -f logs/errors/error.log
```

### Problema: Estrategia no genera señales

```python
# Debug de estrategia
from strategies.user_strategies.my_strategy import MyCustomStrategy

strategy = MyCustomStrategy()
strategy.enable()  # Asegurarse que esté activa

# Probar con datos
signal = strategy.analyze(data)
print(signal)
```

### Problema: Backtesting muy lento

- Reducir rango de fechas
- Usar temporalidad mayor (15m en vez de 1m)
- Optimizar cálculo de indicadores

---

## 📞 Soporte

- **Issues**: GitHub Issues
- **Telegram**: @tu-grupo-telegram
- **Email**: support@tu-email.com
- **Documentación**: Wiki completo en `/docs`

---

## 📜 Licencia

MIT License - Ver `LICENSE` para detalles

---

## ⚠️ Disclaimer

**IMPORTANTE**: El trading de criptomonedas conlleva riesgos significativos. Este bot es una herramienta que puede ayudar en la automatización, pero:

- No garantiza ganancias
- Puedes perder tu capital
- Usa bajo tu propia responsabilidad
- Prueba exhaustivamente antes de usar capital real
- Empieza con cantidades pequeñas

**El desarrollador NO se hace responsable de pérdidas financieras.**

---

## 🙏 Agradecimientos

- CCXT - Exchange connectivity
- Pandas TA - Technical indicators
- Streamlit - Dashboard framework
- FastAPI - API framework

---

## 📚 Recursos Adicionales

- [CCXT Documentation](https://docs.ccxt.com)
- [Pandas TA](https://github.com/twopirllc/pandas-ta)
- [Backtesting.py](https://kernc.github.io/backtesting.py/)
- [Trading View](https://www.tradingview.com/) - Para análisis

---

**¡Buena suerte con tu trading!** 🚀📈