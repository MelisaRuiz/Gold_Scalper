```markdown
# Gold Scalper – EAS Híbrido 2025
**AI-Powered High-Frequency Trading Bot for XAUUSD**  
*MQL5 + Python Multi-Agent Architecture | Deterministic Discipline | Risk 0.3%*


## Resumen Ejecutivo
El Sistema EAS Híbrido 2025 combina arquitectura de agentes IA con disciplina rígida de trading. Especializado en scalping de alta frecuencia en XAUUSD durante la sesión de Nueva York (09:30–11:30 ET). Basado en las mejores prácticas de OpenAI para agentes y técnicas avanzadas de prompt engineering, establece un sistema determinista con capacidades de validación inteligente.
Cumplimiento EAS consolidado – Núcleo inmutable + validación BO5_REST (ver Cumplimiento_EAS_Hibrido.pdf)


## Características Principales
- **Arquitectura Multi-Agente**: Orchestrator, Macro, Signal, Liquidity agents  
- **Disciplina Rígida**: Reglas inmutables (MQL5 `SignalGeneratorCore`)  
- **Validación IA**: LLM agents con `temperature=0.0` para determinismo  
- **Gestión de Riesgo**: 0.3% riesgo fijo + kill switch (2 pérdidas consecutivas)  
- **Timeframes**: M15 (40%), H1 (30%), D1 (30%)  
- **RR_RATIO**: 2.0 (inmutable)  
- **Monitoreo**: Dashboard en tiempo real (planned)  
- **Infraestructura**: Circuit breakers, exponential backoff, health monitoring  
- **Cumplimiento EAS**: Documento consolidado con núcleo inmutable y validación BO5_REST  

## Arquitectura del Sistema
gold_scalper/
├── __init__.py
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
├── config/
│   ├── __init__.py
│   ├── trading_config.json
│   ├── agents_config.json
│   ├── risk_config.json
│   ├── migration_log.json
│   └── legacy/
│       ├── __init__.py
│       ├── ea_settings.json
│       └── hecta_gold_config.json
├── agents/
│   ├── __init__.py
│   ├── agent_orchestrator.py
│   ├── macro_analysis_agent.py
│   ├── signal_validation_agent.py
│   └── liquidity_analysis_agent.py
├── core/
│   ├── __init__.py
│   ├── risk_manager.py
│   ├── signal_generator.mq5
│   ├── signal_generator.py
│   ├── execution_engine.py
│   ├── session_manager.py
│   ├── immutable_core.py
│   └── immutable_config.py
├── infrastructure/
│   ├── __init__.py
│   ├── circuit_breaker.py
│   ├── exponential_backoff.py
│   ├── structured_logger.py
│   ├── config_manager.py
│   ├── health_monitor.py
│   ├── guardrails.py
│   └── infrastructure_manager.py
├── data/
│   ├── __init__.py
│   ├── market_data_collector.py
│   ├── news_analyzer.py
│   └── data_quality_validator.py
├── monitoring/
│   ├── __init__.py
│   ├── performance_tracker.py
│   ├── alert_system.py
│   └── metrics_dashboard.py
├── tests/
│   ├── __init__.py
│   ├── test_agents.py
│   ├── test_core.py
│   └── test_infrastructure.py
├── scripts/
│   ├── __init__.py
│   └── emergency_rollback.py
└── docs/
    ├── Cumplimiento_EAS_Hibrido.pdf
    ├── Arquitectura.pdf


## ⚙️ Ejemplo: Núcleo Inmutable (MQL5)
// signal_generator.mq5 - Núcleo Inmutable EAS Híbrido 2025
#property copyright "© 2025 Melisa Ruiz | HECTA"
#property link      "https://github.com/MelisaRuiz/Gold_Scalper"
#property version   "1.0"
#property strict

class SignalGeneratorCore {
private:
    const double RISK_PERCENT = 0.3;           // Inmutable
    const int    MAX_CONSECUTIVE_LOSSES = 2;   // Kill Switch
    const string TRADING_SESSION = "NY_OPEN";  // 09:30-11:30 ET
    int          consecutive_losses = 0;

public:
    // Validación BO5_REST: Break of Structure + Retest
    bool validateBOS_RETEST(double rsi, double macd, bool break_confirmed, bool retest_successful) {
        // Lógica determinista: RSI > 30 (oversold retest), MACD crossover, estructura confirmada
        if (rsi > 30.0 && macd > 0.0 && break_confirmed && retest_successful) {
            return true;  // Señal válida
        }
        return false;     // Rechazada
    }

    void recordTradeResult(bool is_win) {
        if (is_win) {
            consecutive_losses = 0;
        } else {
            consecutive_losses++;
            if (consecutive_losses >= MAX_CONSECUTIVE_LOSSES) {
                Print("KILL SWITCH ACTIVADO: 2 pérdidas consecutivas");
                ExpertRemove();  // Detiene el EA
            }
        }
    }
};

SignalGeneratorCore core;

// OnTick: Ejecución en tiempo real
void OnTick() {
    double rsi  = iRSI(_Symbol, PERIOD_M15, 14, PRICE_CLOSE, 0);
    double macd = iMACD(_Symbol, PERIOD_M15, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 0);
    
    // Simulación de confirmación BO5 (en producción: análisis de estructura)
    bool break_confirmed = true;
    bool retest_successful = true;

    if (core.validateBOS_RETEST(rsi, macd, break_confirmed, retest_successful)) {
        Print("SEÑAL VÁLIDA: Abrir operación XAUUSD");
        // OrderSend(...)
    }
}


## 📄 Documentación
- [Cumplimiento EAS Híbrido 2025](docs/Cumplimiento_EAS.pdf)
- [Arquitectura Sistema](docs/Aquitectura.pdf)
- [Instalación y Configuración](Instalacion_y_Configuracion.txt)
- [Requirements](requirements.txt)

## Instalación y Configuración
Prerrequisitos
Python 3.9+
8GB RAM mínimo (16GB recomendado)
Conexión a internet estable
Acceso a datos de mercado (MT5/IBKR/Polygon)

## Instalación
git clone https://github.com/MelisaRuiz/Gold_Scalper.git
cd Gold_Scalper
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env

## Seguridad y Configuración
- Usa .env.example → copia a .env (nunca subas .env)
- .gitignore protege: venv/, __pycache__/, .env, PDFs, logs
- Credenciales: MT5, IBKR, Anthropic, AWS, etc.


## 📄 Licensing
This project is **dual-licensed**:
- **Open Source**: [GPL v3](LICENSE) – Free for non-commercial use; derivatives must be open-source.
- **Commercial**: [Commercial License](COMMERCIAL_LICENSE.md) – For proprietary/premium use (contact dianaruizn10@gmail.com).

> Premium features: MT5 integration, proprietary ML models, enterprise dashboard.

---
*Developed by Melisa Ruiz | Self-Directed | 2025*
```
