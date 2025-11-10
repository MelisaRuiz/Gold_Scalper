#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Dashboard de Métricas en Tiempo Real - EAS Híbrido 2025
Sistema de visualización y agregación de métricas para monitoreo empresarial
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import statistics
from collections import deque

from infrastructure.structured_logger import get_eas_logger, log_eas_info

logger = get_eas_logger("MetricsDashboard")

class MetricType(Enum):
    """Tipos de métricas soportados"""
    GAUGE = "gauge"           # Valor instantáneo
    COUNTER = "counter"       # Valor acumulativo
    HISTOGRAM = "histogram"   # Distribución de valores
    SUMMARY = "summary"       # Resumen estadístico

@dataclass
class MetricDefinition:
    """Definición de una métrica del dashboard"""
    name: str
    type: MetricType
    description: str
    unit: str = ""
    labels: List[str] = field(default_factory=list)
    retention_hours: int = 24
    aggregation_window: int = 60  # segundos
    
    # Umbrales para alertas
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None

@dataclass
class MetricValue:
    """Valor de métrica con timestamp"""
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)

@dataclass 
class MetricSeries:
    """Serie temporal de una métrica"""
    definition: MetricDefinition
    values: deque = field(default_factory=deque)
    
    def __post_init__(self):
        max_values = (self.definition.retention_hours * 3600) // self.definition.aggregation_window
        self.values = deque(maxlen=max_values)
    
    def add_value(self, value: MetricValue):
        """Agregar valor a la serie"""
        self.values.append(value)
    
    def get_recent_values(self, minutes: int = 60) -> List[MetricValue]:
        """Obtener valores recientes"""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return [v for v in self.values if v.timestamp >= cutoff]
    
    def get_statistics(self, minutes: int = 60) -> Dict[str, float]:
        """Obtener estadísticas de la serie"""
        recent_values = self.get_recent_values(minutes)
        if not recent_values:
            return {}
        
        values = [v.value for v in recent_values]
        
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stddev": statistics.stdev(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values),
            "latest": values[-1]
        }

class MetricsDashboard:
    """
    Dashboard de métricas en tiempo real para EAS Híbrido 2025
    """
    
    def __init__(self):
        self.metrics: Dict[str, MetricSeries] = {}
        self.subscribers: List[Callable] = []
        self.last_update = datetime.utcnow()
        
        # Inicializar métricas EAS estándar
        self._initialize_eas_metrics()
        
        logger.log_structured("INFO", "METRICS_DASHBOARD_INITIALIZED", {
            "initial_metrics_count": len(self.metrics)
        })
    
    def _initialize_eas_metrics(self):
        """Inicializar métricas estándar del sistema EAS"""
        
        # Métricas de Trading
        self.register_metric(MetricDefinition(
            name="trading.daily_pnl",
            type=MetricType.GAUGE,
            description="Profit & Loss diario",
            unit="USD",
            retention_hours=48
        ))
        
        self.register_metric(MetricDefinition(
            name="trading.win_rate",
            type=MetricType.GAUGE,
            description="Tasa de operaciones ganadoras",
            unit="percent",
            warning_threshold=0.6,
            critical_threshold=0.5
        ))
        
        self.register_metric(MetricDefinition(
            name="trading.profit_factor",
            type=MetricType.GAUGE,
            description="Ratio de profit factor",
            unit="ratio",
            warning_threshold=1.5,
            critical_threshold=1.0
        ))
        
        self.register_metric(MetricDefinition(
            name="trading.sharpe_ratio",
            type=MetricType.GAUGE,
            description="Ratio de Sharpe",
            unit="ratio",
            warning_threshold=1.5
        ))
        
        self.register_metric(MetricDefinition(
            name="trading.max_drawdown",
            type=MetricType.GAUGE,
            description="Drawdown máximo actual",
            unit="percent",
            warning_threshold=5.0,
            critical_threshold=7.0
        ))
        
        self.register_metric(MetricDefinition(
            name="trading.current_risk_exposure",
            type=MetricType.GAUGE,
            description="Exposición actual al riesgo",
            unit="percent",
            warning_threshold=0.4,
            critical_threshold=0.5
        ))
        
        # Métricas de Ejecución
        self.register_metric(MetricDefinition(
            name="execution.avg_execution_time",
            type=MetricType.GAUGE,
            description="Tiempo promedio de ejecución",
            unit="milliseconds",
            warning_threshold=80.0,
            critical_threshold=100.0
        ))
        
        self.register_metric(MetricDefinition(
            name="execution.slippage_avg",
            type=MetricType.GAUGE,
            description="Deslizamiento promedio",
            unit="pips",
            warning_threshold=0.5,
            critical_threshold=1.0
        ))
        
        self.register_metric(MetricDefinition(
            name="execution.error_rate",
            type=MetricType.GAUGE,
            description="Tasa de errores de ejecución",
            unit="percent",
            warning_threshold=0.03,
            critical_threshold=0.05
        ))
        
        self.register_metric(MetricDefinition(
            name="execution.requote_rate",
            type=MetricType.GAUGE,
            description="Tasa de requotes",
            unit="percent",
            warning_threshold=0.1,
            critical_threshold=0.2
        ))
        
        # Métricas de IA
        self.register_metric(MetricDefinition(
            name="ia.validation_accuracy",
            type=MetricType.GAUGE,
            description="Precisión de validación IA",
            unit="percent",
            warning_threshold=0.8,
            critical_threshold=0.7
        ))
        
        self.register_metric(MetricDefinition(
            name="ia.response_time_ms",
            type=MetricType.GAUGE,
            description="Tiempo de respuesta de IA",
            unit="milliseconds",
            warning_threshold=300.0,
            critical_threshold=500.0
        ))
        
        self.register_metric(MetricDefinition(
            name="ia.consensus_score",
            type=MetricType.GAUGE,
            description="Score de consenso entre agentes",
            unit="score",
            warning_threshold=0.7
        ))
        
        self.register_metric(MetricDefinition(
            name="ia.guardrail_triggers",
            type=MetricType.COUNTER,
            description="Total de triggers de guardrails",
            unit="count"
        ))
        
        # Métricas de Sistema
        self.register_metric(MetricDefinition(
            name="system.memory_usage",
            type=MetricType.GAUGE,
            description="Uso de memoria del sistema",
            unit="percent",
            warning_threshold=0.7,
            critical_threshold=0.85
        ))
        
        self.register_metric(MetricDefinition(
            name="system.cpu_usage",
            type=MetricType.GAUGE,
            description="Uso de CPU del sistema",
            unit="percent",
            warning_threshold=0.6,
            critical_threshold=0.8
        ))
        
        self.register_metric(MetricDefinition(
            name="system.latency_ms",
            type=MetricType.GAUGE,
            description="Latencia general del sistema",
            unit="milliseconds",
            warning_threshold=50.0,
            critical_threshold=100.0
        ))
    
    def register_metric(self, definition: MetricDefinition):
        """Registrar una nueva métrica en el dashboard"""
        self.metrics[definition.name] = MetricSeries(definition)
        
        log_eas_info("METRIC_REGISTERED", {
            "metric_name": definition.name,
            "metric_type": definition.type.value,
            "description": definition.description
        })
    
    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Registrar un valor de métrica"""
        if name not in self.metrics:
            logger.log_structured("WARNING", "METRIC_NOT_REGISTERED", {
                "metric_name": name,
                "value": value
            })
            return
        
        metric_value = MetricValue(
            value=value,
            timestamp=datetime.utcnow(),
            labels=labels or {}
        )
        
        self.metrics[name].add_value(metric_value)
        self.last_update = datetime.utcnow()
        
        # Notificar a suscriptores
        self._notify_subscribers(name, metric_value)
    
    def record_eas_metrics(self, metrics_data: Dict[str, Any]):
        """
        Registrar métricas EAS consolidadas desde el sistema
        """
        try:
            # Métricas de Trading
            trading_metrics = metrics_data.get('trading_metrics', {})
            self.record_metric("trading.daily_pnl", trading_metrics.get('daily_pnl', 0))
            self.record_metric("trading.win_rate", trading_metrics.get('win_rate', 0))
            self.record_metric("trading.profit_factor", trading_metrics.get('profit_factor', 0))
            self.record_metric("trading.sharpe_ratio", trading_metrics.get('sharpe_ratio', 0))
            self.record_metric("trading.max_drawdown", trading_metrics.get('max_drawdown', 0))
            self.record_metric("trading.current_risk_exposure", 
                             trading_metrics.get('current_risk_exposure', 0))
            
            # Métricas de Ejecución
            execution_metrics = metrics_data.get('execution_metrics', {})
            self.record_metric("execution.avg_execution_time", 
                             execution_metrics.get('avg_execution_time', 0))
            self.record_metric("execution.slippage_avg", 
                             execution_metrics.get('slippage_avg', 0))
            self.record_metric("execution.error_rate", 
                             execution_metrics.get('error_rate', 0))
            self.record_metric("execution.requote_rate", 
                             execution_metrics.get('requote_rate', 0))
            
            # Métricas de IA
            ia_metrics = metrics_data.get('ia_metrics', {})
            self.record_metric("ia.validation_accuracy", 
                             ia_metrics.get('validation_accuracy', 0))
            self.record_metric("ia.response_time_ms", 
                             ia_metrics.get('response_time_ms', 0))
            self.record_metric("ia.consensus_score", 
                             ia_metrics.get('consensus_score', 0))
            self.record_metric("ia.guardrail_triggers", 
                             ia_metrics.get('guardrail_triggers', 0))
            
        except Exception as e:
            logger.log_structured("ERROR", "METRICS_RECORDING_ERROR", {
                "error": str(e),
                "metrics_data": metrics_data
            })
    
    def get_metric_statistics(self, name: str, minutes: int = 60) -> Dict[str, Any]:
        """Obtener estadísticas de una métrica específica"""
        if name not in self.metrics:
            return {}
        
        series = self.metrics[name]
        stats = series.get_statistics(minutes)
        
        # Agregar información de la definición
        result = {
            "definition": {
                "name": series.definition.name,
                "type": series.definition.type.value,
                "description": series.definition.description,
                "unit": series.definition.unit
            },
            "statistics": stats,
            "thresholds": {
                "warning": series.definition.warning_threshold,
                "critical": series.definition.critical_threshold
            }
        }
        
        # Determinar estado actual basado en umbrales
        latest_value = stats.get('latest', 0)
        result["current_status"] = self._evaluate_metric_status(
            series.definition, latest_value
        )
        
        return result
    
    def _evaluate_metric_status(self, definition: MetricDefinition, value: float) -> str:
        """Evaluar el estado de una métrica basado en umbrales"""
        if definition.critical_threshold is not None:
            if (definition.type == MetricType.GAUGE and value >= definition.critical_threshold):
                return "CRITICAL"
            elif (definition.type in [MetricType.COUNTER, MetricType.HISTOGRAM] and 
                  value <= definition.critical_threshold):
                return "CRITICAL"
        
        if definition.warning_threshold is not None:
            if (definition.type == MetricType.GAUGE and value >= definition.warning_threshold):
                return "WARNING"
            elif (definition.type in [MetricType.COUNTER, MetricType.HISTOGRAM] and 
                  value <= definition.warning_threshold):
                return "WARNING"
        
        return "HEALTHY"
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """Obtener resumen de salud del sistema"""
        health_summary = {
            "overall_status": "HEALTHY",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }
        
        component_statuses = {}
        
        # Evaluar métricas por componente
        for metric_name, series in self.metrics.items():
            component = metric_name.split('.')[0]
            if component not in component_statuses:
                component_statuses[component] = []
            
            stats = series.get_statistics(30)  # Últimos 30 minutos
            latest_value = stats.get('latest', 0)
            status = self._evaluate_metric_status(series.definition, latest_value)
            
            component_statuses[component].append(status)
        
        # Determinar estado por componente
        for component, statuses in component_statuses.items():
            if any(status == "CRITICAL" for status in statuses):
                component_status = "CRITICAL"
            elif any(status == "WARNING" for status in statuses):
                component_status = "WARNING"
            else:
                component_status = "HEALTHY"
            
            health_summary["components"][component] = {
                "status": component_status,
                "metrics_count": len(statuses),
                "critical_count": statuses.count("CRITICAL"),
                "warning_count": statuses.count("WARNING")
            }
        
        # Determinar estado general
        component_statuses = [comp["status"] for comp in health_summary["components"].values()]
        if any(status == "CRITICAL" for status in component_statuses):
            health_summary["overall_status"] = "CRITICAL"
        elif any(status == "WARNING" for status in component_statuses):
            health_summary["overall_status"] = "WARNING"
        
        return health_summary
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Obtener datos completos para el dashboard"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system_health": self.get_system_health_summary(),
            "key_metrics": {
                name: self.get_metric_statistics(name, 60)
                for name in self.metrics.keys()
            },
            "last_update": self.last_update.isoformat()
        }
    
    def subscribe(self, callback: Callable):
        """Suscribirse a actualizaciones de métricas"""
        self.subscribers.append(callback)
    
    def _notify_subscribers(self, metric_name: str, value: MetricValue):
        """Notificar a suscriptores sobre nueva métrica"""
        for callback in self.subscribers:
            try:
                callback(metric_name, value)
            except Exception as e:
                logger.log_structured("ERROR", "METRIC_SUBSCRIBER_ERROR", {
                    "metric_name": metric_name,
                    "error": str(e)
                })
    
    def export_metrics_report(self, hours: int = 24) -> Dict[str, Any]:
        """Exportar reporte completo de métricas"""
        report = {
            "period": {
                "start": (datetime.utcnow() - timedelta(hours=hours)).isoformat(),
                "end": datetime.utcnow().isoformat()
            },
            "summary": self.get_system_health_summary(),
            "detailed_metrics": {}
        }
        
        for metric_name in self.metrics.keys():
            report["detailed_metrics"][metric_name] = self.get_metric_statistics(
                metric_name, hours * 60
            )
        
        return report

# Instancia global del dashboard
global_dashboard: Optional[MetricsDashboard] = None

def get_metrics_dashboard() -> MetricsDashboard:
    """Obtener instancia global del dashboard de métricas"""
    global global_dashboard
    if global_dashboard is None:
        global_dashboard = MetricsDashboard()
    return global_dashboard

def record_system_metrics(metrics_data: Dict[str, Any]):
    """Función de conveniencia para registrar métricas del sistema"""
    dashboard = get_metrics_dashboard()
    dashboard.record_eas_metrics(metrics_data)

# Ejemplo de uso
async def example_usage():
    """Ejemplo de uso del dashboard de métricas"""
    dashboard = get_metrics_dashboard()
    
    # Registrar algunas métricas de ejemplo
    dashboard.record_metric("trading.win_rate", 0.72)
    dashboard.record_metric("execution.avg_execution_time", 45.2)
    dashboard.record_metric("ia.validation_accuracy", 0.88)
    dashboard.record_metric("system.memory_usage", 0.65)
    
    # Obtener datos del dashboard
    dashboard_data = dashboard.get_dashboard_data()
    print("Dashboard Data:")
    print(json.dumps(dashboard_data, indent=2, default=str))
    
    # Obtener resumen de salud
    health_summary = dashboard.get_system_health_summary()
    print(f"\nSystem Health: {health_summary['overall_status']}")
    
    # Exportar reporte
    report = dashboard.export_metrics_report(1)  # Última hora
    print(f"\nReport exported with {len(report['detailed_metrics'])} metrics")

if __name__ == "__main__":
    asyncio.run(example_usage())