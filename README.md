````markdown
# Gold Scalper – EAS Híbrido 2025
**AI-Powered High-Frequency Trading Bot for XAUUSD**  
*MQL5 + Python Multi-Agent Architecture | Deterministic Discipline | Risk 0.3%*

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://python.org)  
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)  
[![Commercial](https://img.shields.io/badge/License-Commercial-red)](COMMERCIAL_LICENSE.md)  

---

## 📋 Resumen Ejecutivo
El **Sistema EAS Híbrido 2025** combina arquitectura de agentes IA con disciplina rígida de trading. Especializado en **scalping de alta frecuencia en XAUUSD** durante la sesión de Nueva York (09:30–11:30 ET). Basado en prácticas avanzadas de OpenAI para agentes y técnicas de prompt engineering, establece un sistema **determinista** con validación inteligente.

> **Cumplimiento EAS consolidado** – Núcleo inmutable + validación BO5_REST  
> [Ver documento](docs/Cumplimiento_EAS_Hibrido.pdf)

---

## 🎯 Características Principales
- **Arquitectura Multi-Agente**: Orchestrator, Macro, Signal, Liquidity agents  
- **Disciplina Rígida**: Reglas inmutables en MQL5 (`SignalGeneratorCore`)  
- **Validación IA**: LLM agents con `temperature=0.0` para determinismo  
- **Gestión de Riesgo**: 0.3% riesgo fijo + kill switch (2 pérdidas consecutivas)  
- **Timeframes**: M15 (40%), H1 (30%), D1 (30%)  
- **RR_RATIO**: 2.0 (inmutable)  
- **Monitoreo**: Dashboard en tiempo real (planned)  
- **Infraestructura**: Circuit breakers, exponential backoff, health monitoring  
- **Cumplimiento EAS**: Documento consolidado con núcleo inmutable y validación BO5_REST  

---

## 🏗️ Estructura del Proyecto
```bash
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
│   ├── agents_config.py
│   ├── risk_config.py
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
│   └── ...
├── data/
├── monitoring/
├── tests/
├── scripts/
└── docs/
    ├── Cumplimiento_EAS_Hibrido.pdf
    ├── Arquitectura.pdf
    └── arqui.png
````

---

## ⚙️ Núcleo Inmutable (MQL5)

// signal_generator.mq5

```mql5
#property copyright "© 2025 Melisa Ruiz | HECTA"
#property link      "https://github.com/MelisaRuiz/Gold_Scalper"
#property version   "1.0"
#property strict

class SignalGeneratorCore {
private:
    const double RISK_PERCENT = 0.3;
    const int    MAX_CONSECUTIVE_LOSSES = 2;
    const string TRADING_SESSION = "NY_OPEN";
    int consecutive_losses = 0;

public:
    bool validateBOS_RETEST(double rsi, double macd, bool break_confirmed, bool retest_successful) {
        return (rsi > 30.0 && macd > 0.0 && break_confirmed && retest_successful);
    }

    void recordTradeResult(bool is_win) {
        if (!is_win) {
            consecutive_losses++;
            if (consecutive_losses >= MAX_CONSECUTIVE_LOSSES) ExpertRemove();
        } else consecutive_losses = 0;
    }
};

SignalGeneratorCore core;

void OnTick() {
    double rsi  = iRSI(_Symbol, PERIOD_M15, 14, PRICE_CLOSE, 0);
    double macd = iMACD(_Symbol, PERIOD_M15, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 0);
    bool break_confirmed = true;
    bool retest_successful = true;

    if (core.validateBOS_RETEST(rsi, macd, break_confirmed, retest_successful)) {
        Print("SEÑAL VÁLIDA: Abrir operación XAUUSD");
    }
}
```

---

## 📄 Documentación

* [Cumplimiento EAS Híbrido 2025](docs/Cumplimiento_EAS_Hibrido.pdf)
* [Arquitectura del Sistema](docs/Arquitectura.pdf)
* [Instalación y Configuración](Instalacion_y_Configuracion.txt)
* [Requirements](requirements.txt)

---

## ⚙️ Instalación

```bash
git clone https://github.com/MelisaRuiz/Gold_Scalper.git
cd Gold_Scalper
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate    # Windows
pip install -r requirements.txt
cp .env.example .env
```

---

## 🔐 Seguridad y Configuración

* `.env.example` → copia a `.env` (nunca subir `.env`)
* `.gitignore` protege: venv/, **pycache**/, .env, PDFs, logs
* Credenciales locales: MT5, IBKR, Anthropic, AWS, Polygon

---

## 📄 Licencias

Este proyecto tiene **dual-license**:

| Tipo        | Uso                                 | Archivo                                        |
| ----------- | ----------------------------------- | ---------------------------------------------- |
| Open Source | No comercial, derivados open        | [GPL v3](LICENSE)                              |
| Comercial   | Propietario, MT5, fondos, dashboard | [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md) |

> Premium features: MT5 integration, proprietary ML models, enterprise dashboard.

---

*Developed by Melisa Ruiz | Self-Directed | 2025*

```

