```markdown
# Gold Scalper – EAS Híbrido 2025
**AI-Powered High-Frequency Trading Bot for XAUUSD**  
*MQL5 + Python Multi-Agent Architecture | Deterministic Discipline | Risk 0.3%*


## 📋 Resumen Ejecutivo
El **Sistema EAS Híbrido 2025** combina arquitectura de agentes IA con disciplina rígida de trading. Especializado en **scalping de alta frecuencia en XAUUSD** durante la sesión de Nueva York (09:30–11:30 ET). Basado en las mejores prácticas de OpenAI para agentes y técnicas avanzadas de prompt engineering, establece un sistema determinista con capacidades de validación inteligente.

## 🎯 Características Principales
- **Arquitectura Multi-Agente**: Orchestrator, Macro, Signal, Liquidity agents  
- **Disciplina Rígida**: Reglas inmutables (MQL5 `SignalGeneratorCore`)  
- **Validación IA**: LLM agents con `temperature=0.0` para determinismo  
- **Gestión de Riesgo**: 0.3% riesgo fijo + kill switch (2 pérdidas consecutivas)  
- **Timeframes**: M15 (40%), H1 (30%), D1 (30%)  
- **RR_RATIO**: 2.0 (inmutable)  
- **Monitoreo**: Dashboard en tiempo real (planned)  
- **Infraestructura**: Circuit breakers, exponential backoff, health monitoring  
- **Cumplimiento EAS**: Documento consolidado con núcleo inmutable y validación BO5_REST  

## ⚙️ Ejemplo: Núcleo Inmutable (MQL5)
```mql5
// signal_generator.mq5 - Núcleo Inmutable EAS Híbrido 2025
#property strict

class SignalGeneratorCore {
private:
    const double RISK_PERCENT = 0.3;      // Inmutable
    const int MAX_CONSECUTIVE_LOSSES = 2; // Kill Switch
    const string TRADING_SESSION = "NY_OPEN";
    int consecutive_losses = 0;
    
public:
    bool validateBOS_RETEST(double rsi, double macd, bool break_confirmed, bool retest_successful) {
        // Lógica completa: Chequea RSI > 30 for oversold retest, MACD crossover
        if (rsi > 30 && macd > 0 && break_confirmed && retest_successful) {
            return true; // Válida
        }
        return false; // Rechazada
    }
    
    void recordTradeResult(bool is_win) {
        if (is_win) {
            consecutive_losses = 0;
        } else {
            consecutive_losses++;
            if (consecutive_losses >= MAX_CONSECUTIVE_LOSSES) {
                Print("Kill Switch Activated!");
                // ExpertRemove(); // Stop EA
            }
        }
    }
};

SignalGeneratorCore core;

// OnTick function for EA execution
void OnTick() {
    // Example call
    double rsi = iRSI(NULL, 0, 14, PRICE_CLOSE, 0); // RSI current
    double macd = iMACD(NULL, 0, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 0); // MACD main
    if (core.validateBOS_RETEST(rsi, macd, true, true)) {
        // Open order
        Print("Valid Signal - Open Trade");
    }
}
```

## 📄 Documentación
- [Cumplimiento EAS Híbrido 2025](docs/Cumplimiento_EAS.pdf)
- [Arquitectura Sistema](docs/Aquitectura.pdf)
- [Instalación y Configuración](Instalacion_y_Configuracion.txt)
- [Requirements](requirements.txt)

## ⚙️ Instalación y Configuración
### Prerrequisitos
- Python 3.9 o superior
- 8GB RAM mínimo (16GB recomendado)
- Conexión a internet estable
- Acceso a datos de mercado (MT5/IBKR/Polygon)

### Instalación
1. **Clonar y configurar entorno**:
```bash
git clone <repository-url>
cd hecta_gold_scalper
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

## 📄 Licensing
This project is **dual-licensed**:
- **Open Source**: [GPL v3](LICENSE) – Free for non-commercial use; derivatives must be open-source.
- **Commercial**: [Commercial License](COMMERCIAL_LICENSE.md) – For proprietary/premium use (contact dianaruizn10@gmail.com).

> Premium features: MT5 integration, proprietary ML models, enterprise dashboard.

---
*Developed by Melisa Ruiz | Self-Directed | 2025*
```
