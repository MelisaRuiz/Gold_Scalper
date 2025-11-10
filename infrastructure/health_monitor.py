"""
Sistema avanzado de Monitoreo de Salud para EAS Híbrido 2025
Monitorea métricas en tiempo real, genera alertas predictivas y gestiona el estado del sistema
CORREGIDO Y FUNCIONAL
"""

import asyncio
import time
import json
import statistics
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import threading
from collections import deque

# ===== IMPLEMENTACIONES MÍNIMAS DE INFRAESTRUCTURA (si no existen) =====

class StructuredLogger:
    def __init__(self, name: str):
        import logging
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def info(self, msg: str, extra: Dict = None):
        self.logger.info(msg, extra=extra or {})

    def warning(self, msg: str, extra: Dict = None):
        self.logger.warning(msg, extra=extra or {})

    def error(self, msg: str, extra: Dict = None):
        self.logger.error(msg, extra=extra or {})

class CircuitBreaker:
    def __init__(self, max_failures: int = 5, reset_timeout: int = 300):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = None
        self._lock = threading.Lock()

    def allow_request(self) -> bool:
        with self._lock:
            if self.failures >= self.max_failures:
                if time.time() - (self.last_failure_time or 0) > self.reset_timeout:
                    self.failures = 0
                    return True
                return False
            return True

    def record_success(self):
        with self._lock:
            self.failures = 0

    def record_failure(self):
        with self._lock:
            self.failures += 1
            self.last_failure_time = time.time()

    def get_error_rate(self) -> float:
        # Placeholder: en producción, calcular tasa real de errores
        return 0.01

    def get_status(self) -> str:
        return "OPEN" if self.allow_request() else "CLOSED"

def guardrail_orchestrator_get_validation_report():
    return {"critical_violations": 0}

# Reemplazar con la implementación real si existe
try:
    from infrastructure.structured_logger import StructuredLogger
    from infrastructure.circuit_breaker import CircuitBreaker
    from infrastructure.guardrails import guardrail_orchestrator
    guardrail_orchestrator_get_validation_report = guardrail_orchestrator.get_validation_report
except ImportError:
    pass

# ===== FIN DE IMPLEMENTACIONES DE RESPALDO =====

class SystemStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"

class ComponentStatus(Enum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"

@dataclass
class SystemMetrics:
    """Métricas del sistema en tiempo real"""
    # Performance
    daily_pnl: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    
    # Execution
    avg_execution_time: float = 0.0
    slippage_avg: float = 0.0
    error_rate: float = 0.0
    requote_rate: float = 0.0
    orders_executed: int = 0
    orders_failed: int = 0
    
    # IA Metrics
    validation_accuracy: float = 0.0
    response_time_ms: float = 0.0
    consensus_score: float = 0.0
    guardrail_triggers: int = 0
    ia_confidence: float = 0.0
    
    # Risk Metrics
    current_risk_exposure: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    daily_loss_percent: float = 0.0
    risk_multiplier: float = 1.0
    
    # System Health
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    latency_mt5: float = 0.0
    uptime_minutes: float = 0.0

@dataclass
class Alert:
    """Estructura de alerta del sistema"""
    level: str
    component: str
    message: str
    timestamp: datetime
    metadata: Dict[str, Any]
    is_predictive: bool = False

class PredictiveAlertSystem:
    """
    Sistema de alertas predictivas basado en métricas en tiempo real
    """
    
    def __init__(self):
        self.alert_channels = ["TELEGRAM", "EMAIL", "PUSH"]
        self.risk_thresholds = {
            "drawdown_alert": 0.6,  # 60% del máximo permitido
            "volatility_spike": 2.5,  # ATR > 2.5
            "error_spike": 0.05,  # 5% tasa de errores
            "ia_confidence_drop": 0.7,  # Confianza IA < 70%
            "latency_spike": 100.0,  # Latencia > 100ms
            "memory_alert": 85.0,  # Uso memoria > 85%
        }
        
        self.metric_history = {
            "drawdown": deque(maxlen=100),
            "error_rate": deque(maxlen=50),
            "latency": deque(maxlen=50),
            "ia_confidence": deque(maxlen=50)
        }
        
        self.zscore_thresholds = {
            "drawdown_zscore": 2.0,
            "error_zscore": 2.5,
            "latency_zscore": 3.0
        }

    def calculate_zscore(self, current_value: float, metric_history: deque) -> float:
        """Calcula Z-score para detección de anomalías"""
        if len(metric_history) < 10:
            return 0.0
        
        try:
            mean = statistics.mean(metric_history)
            stdev = statistics.stdev(metric_history) if len(metric_history) > 1 else 0.1
            return (current_value - mean) / stdev if stdev > 0 else 0.0
        except statistics.StatisticsError:
            return 0.0

    def check_predictive_alerts(self, current_metrics: SystemMetrics) -> List[Alert]:
        """Verifica condiciones para alertas predictivas"""
        alerts = []
        
        # Actualizar historial de métricas
        self.metric_history["drawdown"].append(current_metrics.current_drawdown)
        self.metric_history["error_rate"].append(current_metrics.error_rate)
        self.metric_history["latency"].append(current_metrics.avg_execution_time)
        self.metric_history["ia_confidence"].append(current_metrics.ia_confidence)
        
        # Alerta predictiva de drawdown usando Z-score
        drawdown_zscore = self.calculate_zscore(
            current_metrics.current_drawdown, 
            self.metric_history["drawdown"]
        )
        
        if drawdown_zscore > self.zscore_thresholds["drawdown_zscore"]:
            alerts.append(Alert(
                level="HIGH",
                component="RiskManager",
                message=f"ALERTA PREDICTIVA: Riesgo de drawdown detectado (Z-score: {drawdown_zscore:.2f})",
                timestamp=datetime.now(),
                metadata={
                    "zscore": drawdown_zscore,
                    "current_drawdown": current_metrics.current_drawdown,
                    "threshold": self.zscore_thresholds["drawdown_zscore"]
                },
                is_predictive=True
            ))

        # Alerta de volatilidad en ejecución
        if current_metrics.avg_execution_time > self.risk_thresholds["latency_spike"]:
            alerts.append(Alert(
                level="MEDIUM",
                component="ExecutionEngine",
                message=f"ALERTA: Spike de latencia detectado ({current_metrics.avg_execution_time:.1f}ms)",
                timestamp=datetime.now(),
                metadata={
                    "current_latency": current_metrics.avg_execution_time,
                    "threshold": self.risk_thresholds["latency_spike"]
                },
                is_predictive=False
            ))

        # Alerta de confianza IA
        if current_metrics.ia_confidence < self.risk_thresholds["ia_confidence_drop"]:
            alerts.append(Alert(
                level="MEDIUM",
                component="IA_Validation",
                message=f"ALERTA: Confianza IA por debajo del umbral ({current_metrics.ia_confidence:.1%})",
                timestamp=datetime.now(),
                metadata={
                    "current_confidence": current_metrics.ia_confidence,
                    "threshold": self.risk_thresholds["ia_confidence_drop"]
                },
                is_predictive=False
            ))

        # Alerta de uso de memoria
        if current_metrics.memory_usage > self.risk_thresholds["memory_alert"]:
            alerts.append(Alert(
                level="HIGH",
                component="System",
                message=f"ALERTA: Uso de memoria crítico ({current_metrics.memory_usage:.1f}%)",
                timestamp=datetime.now(),
                metadata={
                    "memory_usage": current_metrics.memory_usage,
                    "threshold": self.risk_thresholds["memory_alert"]
                },
                is_predictive=False
            ))

        # Alerta de tasa de errores usando Z-score
        error_zscore = self.calculate_zscore(
            current_metrics.error_rate,
            self.metric_history["error_rate"]
        )
        
        if error_zscore > self.zscore_thresholds["error_zscore"]:
            alerts.append(Alert(
                level="HIGH",
                component="ExecutionEngine",
                message=f"ALERTA PREDICTIVA: Spike en tasa de errores (Z-score: {error_zscore:.2f})",
                timestamp=datetime.now(),
                metadata={
                    "zscore": error_zscore,
                    "current_error_rate": current_metrics.error_rate,
                    "threshold": self.zscore_thresholds["error_zscore"]
                },
                is_predictive=True
            ))

        return alerts

    async def send_alerts(self, alerts: List[Alert]):
        """Envía alertas a través de los canales configurados"""
        for alert in alerts:
            for channel in self.alert_channels:
                await self.send_alert(channel, alert)

    async def send_alert(self, channel: str, alert: Alert):
        """Envía una alerta individual a un canal específico"""
        # Implementación específica del canal
        message = f"[{alert.level}] {alert.component}: {alert.message}"
        
        if channel == "TELEGRAM":
            await self._send_telegram_alert(message, alert.metadata)
        elif channel == "EMAIL":
            await self._send_email_alert(message, alert.metadata)
        elif channel == "PUSH":
            await self._send_push_alert(message, alert.metadata)

    async def _send_telegram_alert(self, message: str, metadata: Dict[str, Any]):
        """Envía alerta a Telegram"""
        # Placeholder: implementar con tu bot de Telegram
        print(f"TELEGRAM ALERT: {message}")

    async def _send_email_alert(self, message: str, metadata: Dict[str, Any]):
        """Envía alerta por email"""
        # Placeholder: implementar con tu servicio de email
        print(f"EMAIL ALERT: {message}")

    async def _send_push_alert(self, message: str, metadata: Dict[str, Any]):
        """Envía alerta push"""
        # Placeholder: implementar con tu servicio de push
        print(f"PUSH ALERT: {message}")

class HealthMonitor:
    """
    Monitor principal de salud del sistema EAS Híbrido 2025
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = StructuredLogger(__name__)
        self.circuit_breaker = CircuitBreaker()
        
        # Sistemas internos
        self.alert_system = PredictiveAlertSystem()
        self.metrics = SystemMetrics()
        
        # Estado del sistema
        self.system_status = SystemStatus.HEALTHY
        self.component_status = {
            "ExecutionEngine": ComponentStatus.OPERATIONAL,
            "RiskManager": ComponentStatus.OPERATIONAL,
            "IA_Validation": ComponentStatus.OPERATIONAL,
            "DataCollector": ComponentStatus.OPERATIONAL,
            "MarketData": ComponentStatus.OPERATIONAL
        }
        
        # Histórico de métricas
        self.metrics_history = deque(maxlen=1000)
        self.alert_history = deque(maxlen=100)
        
        # Tiempos de referencia
        self.start_time = datetime.now()
        self.last_health_check = datetime.now()
        
        # Callbacks para componentes externos
        self.health_callbacks: List[Callable] = []
        
        # Thread de monitoreo en background
        self._monitoring_thread = None
        self._stop_monitoring = False
        self._monitoring_lock = threading.Lock()

    def start_monitoring(self):
        """Inicia el monitoreo en background"""
        self._stop_monitoring = False
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
        self.logger.info("Health monitoring started")

    def stop_monitoring(self):
        """Detiene el monitoreo en background"""
        self._stop_monitoring = True
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5.0)
        self.logger.info("Health monitoring stopped")

    def _monitoring_loop(self):
        """Loop principal de monitoreo"""
        while not self._stop_monitoring:
            try:
                self._perform_health_check()
                time.sleep(5)  # Check cada 5 segundos
            except Exception as e:
                self.logger.error(f"Error en monitoring loop: {str(e)}")
                time.sleep(10)  # Esperar más en caso de error

    def _perform_health_check(self):
        """Realiza chequeo completo de salud"""
        with self._monitoring_lock:
            try:
                # Actualizar métricas del sistema
                self._update_system_metrics()
                
                # Verificar estado de componentes
                self._check_component_health()
                
                # Verificar alertas predictivas
                alerts = self.alert_system.check_predictive_alerts(self.metrics)
                
                # Procesar alertas
                if alerts:
                    self._process_alerts(alerts)
                
                # Actualizar estado general del sistema
                self._update_system_status()
                
                # Ejecutar callbacks de salud
                self._execute_health_callbacks()
                
                self.last_health_check = datetime.now()
                
            except Exception as e:
                self.logger.error(f"Error en health check: {str(e)}")
                self.system_status = SystemStatus.CRITICAL

    def _update_system_metrics(self):
        """Actualiza las métricas del sistema desde diferentes fuentes"""
        # Métricas de performance
        self.metrics.uptime_minutes = (datetime.now() - self.start_time).total_seconds() / 60
        
        # Métricas de guardrails
        try:
            guardrail_report = guardrail_orchestrator_get_validation_report()
            self.metrics.guardrail_triggers = guardrail_report.get("critical_violations", 0)
        except Exception as e:
            self.logger.warning(f"Could not get guardrail report: {e}")
        
        # Métricas de circuit breaker
        self.metrics.error_rate = self.circuit_breaker.get_error_rate()
        
        # Guardar en histórico
        metrics_dict = asdict(self.metrics)
        metrics_dict['timestamp'] = datetime.now().isoformat()
        self.metrics_history.append(metrics_dict)

    def _check_component_health(self):
        """Verifica la salud de cada componente"""
        # Verificar ExecutionEngine (latencia)
        if self.metrics.avg_execution_time > 100.0:  # 100ms threshold
            self.component_status["ExecutionEngine"] = ComponentStatus.DEGRADED
        else:
            self.component_status["ExecutionEngine"] = ComponentStatus.OPERATIONAL
        
        # Verificar IA_Validation (confianza)
        if self.metrics.ia_confidence < 0.7:  # 70% confidence threshold
            self.component_status["IA_Validation"] = ComponentStatus.DEGRADED
        else:
            self.component_status["IA_Validation"] = ComponentStatus.OPERATIONAL
        
        # Verificar RiskManager (drawdown)
        if self.metrics.current_drawdown > 5.0:  # 5% drawdown threshold
            self.component_status["RiskManager"] = ComponentStatus.DEGRADED
        else:
            self.component_status["RiskManager"] = ComponentStatus.OPERATIONAL

    def _process_alerts(self, alerts: List[Alert]):
        """Procesa y envía alertas"""
        for alert in alerts:
            self.alert_history.append(alert)
            
            # Log de alerta
            self.logger.warning(
                f"Health Alert - {alert.component}: {alert.message}",
                extra=alert.metadata
            )
            
            # Envío asíncrono de alertas
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.alert_system.send_alerts([alert]))
                else:
                    asyncio.run(self.alert_system.send_alerts([alert]))
            except RuntimeError:
                # Si no hay loop, crear uno nuevo
                asyncio.run(self.alert_system.send_alerts([alert]))

    def _update_system_status(self):
        """Actualiza el estado general del sistema"""
        critical_components = [
            status for status in self.component_status.values() 
            if status == ComponentStatus.FAILED
        ]
        
        degraded_components = [
            status for status in self.component_status.values() 
            if status == ComponentStatus.DEGRADED
        ]
        
        if critical_components:
            self.system_status = SystemStatus.CRITICAL
        elif degraded_components:
            self.system_status = SystemStatus.DEGRADED
        else:
            self.system_status = SystemStatus.HEALTHY

    def _execute_health_callbacks(self):
        """Ejecuta callbacks registrados para eventos de salud"""
        for callback in self.health_callbacks:
            try:
                callback(self.system_status, self.metrics)
            except Exception as e:
                self.logger.error(f"Error en health callback: {str(e)}")

    def register_health_callback(self, callback: Callable):
        """Registra un callback para eventos de salud"""
        self.health_callbacks.append(callback)

    def update_metrics(self, component: str, values: Dict[str, Any]):
        """Actualiza métricas específicas desde componentes externos"""
        # Actualización directa de atributos
        for key, value in values.items():
            if hasattr(self.metrics, key):
                setattr(self.metrics, key, value)
            else:
                # Si no existe el atributo, ignorar o loggear
                self.logger.warning(f"Métrica desconocida: {key} = {value}")

    def get_system_health_report(self) -> Dict[str, Any]:
        """Genera reporte completo de salud del sistema"""
        return {
            "system_status": self.system_status.value,
            "component_status": {
                comp: status.value for comp, status in self.component_status.items()
            },
            "current_metrics": asdict(self.metrics),
            "uptime_minutes": self.metrics.uptime_minutes,
            "alerts_last_hour": len([
                alert for alert in self.alert_history 
                if (datetime.now() - alert.timestamp).total_seconds() < 3600
            ]),
            "guardrail_report": guardrail_orchestrator_get_validation_report(),
            "circuit_breaker_status": self.circuit_breaker.get_status(),
            "last_health_check": self.last_health_check.isoformat()
        }

    def force_system_check(self):
        """Fuerza un chequeo inmediato del sistema"""
        self._perform_health_check()

    def get_historical_metrics(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Obtiene métricas históricas de los últimos N minutos"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [
            metrics for metrics in self.metrics_history
            if datetime.fromisoformat(metrics.get('timestamp', datetime.now().isoformat())) > cutoff_time
        ]

# Instancia global para uso en el sistema
_health_monitor_instance: Optional[HealthMonitor] = None

def initialize_health_monitor(config: Dict[str, Any]) -> HealthMonitor:
    """Inicializa el monitor de salud global"""
    global _health_monitor_instance
    _health_monitor_instance = HealthMonitor(config)
    _health_monitor_instance.start_monitoring()
    return _health_monitor_instance

def get_health_monitor() -> HealthMonitor:
    """Obtiene la instancia global del monitor de salud"""
    global _health_monitor_instance
    if _health_monitor_instance is None:
        raise RuntimeError("HealthMonitor no ha sido inicializado")
    return _health_monitor_instance

# Ejemplo de uso
if __name__ == "__main__":
    # Configuración de ejemplo
    config = {
        "alert_channels": ["TELEGRAM"],
        "risk_thresholds": {
            "drawdown_alert": 0.6,
            "volatility_spike": 2.5,
            "error_spike": 0.05
        }
    }
    
    # Inicialización
    monitor = initialize_health_monitor(config)
    
    # Simular actualización de métricas
    monitor.update_metrics("ExecutionEngine", {
        "avg_execution_time": 85.5,
        "slippage_avg": 2.3,
        "orders_executed": 12,
        "orders_failed": 1
    })
    
    monitor.update_metrics("IA_Validation", {
        "ia_confidence": 0.82,
        "validation_accuracy": 0.88,
        "response_time_ms": 45.2
    })
    
    monitor.update_metrics("RiskManager", {
        "current_drawdown": 1.8,
        "daily_pnl": 250.75,
        "win_rate": 0.68
    })
    
    # Obtener reporte
    report = monitor.get_system_health_report()
    print("System Health Report:")
    print(json.dumps(report, indent=2))
    
    # Mantener el sistema corriendo para pruebas
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop_monitoring()