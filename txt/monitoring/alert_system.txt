#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sistema de Alertas Predictivas Multi-Canal - EAS Híbrido 2025
Sistema de alertas proactivas con integración de métricas en tiempo real y múltiples canales
"""

import asyncio
import smtplib
import requests
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import logging

from infrastructure.structured_logger import get_eas_logger, log_eas_warning, log_eas_error, log_eas_info

logger = get_eas_logger("AlertSystem")

class AlertSeverity(Enum):
    """Niveles de severidad de alertas"""
    LOW = "LOW"
    MEDIUM = "MEDIUM" 
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AlertChannel(Enum):
    """Canales de notificación disponibles"""
    TELEGRAM = "telegram"
    EMAIL = "email"
    PUSH = "push"
    WEBHOOK = "webhook"
    CONSOLE = "console"
    DATABASE = "database"

@dataclass
class AlertConfig:
    """Configuración de umbrales para alertas predictivas"""
    # Umbrales de riesgo
    drawdown_alert: float = 0.6  # 60% del máximo permitido
    volatility_spike: float = 2.5  # ATR > 2.5
    error_spike: float = 0.05  # 5% tasa de errores
    ia_confidence_drop: float = 0.7  # Confianza IA < 70%
    execution_latency_spike: float = 100.0  # ms
    memory_usage_threshold: float = 0.8  # 80% uso de memoria
    cpu_usage_threshold: float = 0.7  # 70% uso de CPU
    
    # Configuración de ventanas temporales
    spike_window_minutes: int = 5
    cooldown_minutes: int = 10
    
    # Canales habilitados
    enabled_channels: List[AlertChannel] = field(default_factory=lambda: [
        AlertChannel.TELEGRAM, AlertChannel.CONSOLE
    ])

@dataclass
class AlertMessage:
    """Mensaje de alerta estructurado"""
    id: str
    severity: AlertSeverity
    title: str
    message: str
    metric: str
    current_value: float
    threshold: float
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "metric": self.metric,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "acknowledged": self.acknowledged
        }

class AlertSystem:
    """
    Sistema de alertas predictivas multi-canal para EAS Híbrido 2025
    """
    
    def __init__(self, config: AlertConfig):
        self.config = config
        self.active_alerts: Dict[str, AlertMessage] = {}
        self.alert_history: List[AlertMessage] = []
        self.cooldown_timers: Dict[str, datetime] = {}
        
        # Configuración de canales
        self.channels = self._setup_channels()
        
        # Métricas de alertas
        self.metrics = {
            "total_alerts_triggered": 0,
            "alerts_by_severity": {severity.value: 0 for severity in AlertSeverity},
            "alerts_by_channel": {channel.value: 0 for channel in AlertChannel},
            "last_alert_time": None
        }
        
        logger.log_structured("INFO", "ALERT_SYSTEM_INITIALIZED", {
            "enabled_channels": [channel.value for channel in config.enabled_channels],
            "thresholds": {
                "drawdown_alert": config.drawdown_alert,
                "volatility_spike": config.volatility_spike,
                "error_spike": config.error_spike,
                "ia_confidence_drop": config.ia_confidence_drop
            }
        })
    
    def _setup_channels(self) -> Dict[AlertChannel, Callable]:
        """Configurar handlers para cada canal"""
        channels = {}
        
        if AlertChannel.TELEGRAM in self.config.enabled_channels:
            channels[AlertChannel.TELEGRAM] = self._send_telegram_alert
        
        if AlertChannel.EMAIL in self.config.enabled_channels:
            channels[AlertChannel.EMAIL] = self._send_email_alert
        
        if AlertChannel.PUSH in self.config.enabled_channels:
            channels[AlertChannel.PUSH] = self._send_push_alert
        
        if AlertChannel.WEBHOOK in self.config.enabled_channels:
            channels[AlertChannel.WEBHOOK] = self._send_webhook_alert
        
        if AlertChannel.CONSOLE in self.config.enabled_channels:
            channels[AlertChannel.CONSOLE] = self._send_console_alert
        
        if AlertChannel.DATABASE in self.config.enabled_channels:
            channels[AlertChannel.DATABASE] = self._store_alert_database
        
        return channels
    
    async def check_predictive_alerts(self, current_metrics: Dict[str, Any]) -> List[AlertMessage]:
        """
        Verificar condiciones de alerta predictivas basadas en métricas actuales
        """
        alerts = []
        
        try:
            # 1. Alerta de Drawdown
            if self._check_drawdown_alert(current_metrics):
                alert = self._create_alert(
                    severity=AlertSeverity.HIGH,
                    title="Riesgo de Drawdown Detectado",
                    message=f"Drawdown actual接近 límite máximo permitido",
                    metric="drawdown_risk",
                    current_value=current_metrics.get('drawdown_risk', 0),
                    threshold=self.config.drawdown_alert,
                    context=current_metrics
                )
                alerts.append(alert)
            
            # 2. Alerta de Volatilidad
            if self._check_volatility_alert(current_metrics):
                alert = self._create_alert(
                    severity=AlertSeverity.MEDIUM,
                    title="Spike de Volatilidad",
                    message="Volatilidad del mercado por encima de umbral seguro",
                    metric="volatility",
                    current_value=current_metrics.get('volatility', 0),
                    threshold=self.config.volatility_spike,
                    context=current_metrics
                )
                alerts.append(alert)
            
            # 3. Alerta de Errores de Ejecución
            if self._check_error_alert(current_metrics):
                alert = self._create_alert(
                    severity=AlertSeverity.HIGH,
                    title="Spike en Tasa de Errores",
                    message="Tasa de errores de ejecución por encima del umbral",
                    metric="error_rate",
                    current_value=current_metrics.get('error_rate', 0),
                    threshold=self.config.error_spike,
                    context=current_metrics
                )
                alerts.append(alert)
            
            # 4. Alerta de Confianza IA
            if self._check_ia_confidence_alert(current_metrics):
                alert = self._create_alert(
                    severity=AlertSeverity.MEDIUM,
                    title="Caída en Confianza de IA",
                    message="Confianza de validación IA por debajo del umbral mínimo",
                    metric="ia_confidence",
                    current_value=current_metrics.get('ia_confidence', 0),
                    threshold=self.config.ia_confidence_drop,
                    context=current_metrics
                )
                alerts.append(alert)
            
            # 5. Alerta de Latencia
            if self._check_latency_alert(current_metrics):
                alert = self._create_alert(
                    severity=AlertSeverity.HIGH,
                    title="Spike de Latencia en Ejecución",
                    message="Latencia de ejecución por encima del límite para scalping",
                    metric="execution_latency",
                    current_value=current_metrics.get('execution_latency', 0),
                    threshold=self.config.execution_latency_spike,
                    context=current_metrics
                )
                alerts.append(alert)
            
            # 6. Alerta de Uso de Recursos
            if self._check_resource_alert(current_metrics):
                alert = self._create_alert(
                    severity=AlertSeverity.LOW,
                    title="Uso Elevado de Recursos",
                    message="Uso de CPU/Memoria接近 límites operativos",
                    metric="resource_usage",
                    current_value=current_metrics.get('cpu_usage', 0),
                    threshold=self.config.cpu_usage_threshold,
                    context=current_metrics
                )
                alerts.append(alert)
            
            # Procesar alertas detectadas
            for alert in alerts:
                await self._process_alert(alert)
                
        except Exception as e:
            log_eas_error("ALERT_CHECK_ERROR", {
                "error": str(e),
                "current_metrics": current_metrics
            })
        
        return alerts
    
    def _check_drawdown_alert(self, metrics: Dict[str, Any]) -> bool:
        """Verificar alerta de drawdown"""
        drawdown_risk = metrics.get('drawdown_risk', 0)
        return drawdown_risk > self.config.drawdown_alert
    
    def _check_volatility_alert(self, metrics: Dict[str, Any]) -> bool:
        """Verificar alerta de volatilidad"""
        volatility = metrics.get('volatility', 0)
        return volatility > self.config.volatility_spike
    
    def _check_error_alert(self, metrics: Dict[str, Any]) -> bool:
        """Verificar alerta de errores"""
        error_rate = metrics.get('error_rate', 0)
        return error_rate > self.config.error_spike
    
    def _check_ia_confidence_alert(self, metrics: Dict[str, Any]) -> bool:
        """Verificar alerta de confianza IA"""
        ia_confidence = metrics.get('ia_confidence', 1.0)
        return ia_confidence < self.config.ia_confidence_drop
    
    def _check_latency_alert(self, metrics: Dict[str, Any]) -> bool:
        """Verificar alerta de latencia"""
        execution_latency = metrics.get('execution_latency', 0)
        return execution_latency > self.config.execution_latency_spike
    
    def _check_resource_alert(self, metrics: Dict[str, Any]) -> bool:
        """Verificar alerta de recursos"""
        cpu_usage = metrics.get('cpu_usage', 0)
        memory_usage = metrics.get('memory_usage', 0)
        return (cpu_usage > self.config.cpu_usage_threshold or 
                memory_usage > self.config.memory_usage_threshold)
    
    def _create_alert(self, severity: AlertSeverity, title: str, message: str,
                     metric: str, current_value: float, threshold: float,
                     context: Dict[str, Any]) -> AlertMessage:
        """Crear mensaje de alerta estructurado"""
        alert_id = f"{metric}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        return AlertMessage(
            id=alert_id,
            severity=severity,
            title=title,
            message=message,
            metric=metric,
            current_value=current_value,
            threshold=threshold,
            timestamp=datetime.utcnow(),
            context=context
        )
    
    async def _process_alert(self, alert: AlertMessage):
        """Procesar una alerta detectada"""
        # Verificar cooldown
        if alert.metric in self.cooldown_timers:
            cooldown_end = self.cooldown_timers[alert.metric]
            if datetime.utcnow() < cooldown_end:
                return
        
        # Verificar si ya existe una alerta activa similar
        existing_alert = self.active_alerts.get(alert.metric)
        if existing_alert and existing_alert.severity == alert.severity:
            # Actualizar alerta existente
            self.active_alerts[alert.metric] = alert
        else:
            # Nueva alerta
            self.active_alerts[alert.metric] = alert
            self.alert_history.append(alert)
            self.metrics["total_alerts_triggered"] += 1
            self.metrics["alerts_by_severity"][alert.severity.value] += 1
            self.metrics["last_alert_time"] = alert.timestamp.isoformat()
            
            # Enviar a través de canales configurados
            await self._send_alert(alert)
            
            # Establecer cooldown
            cooldown_end = datetime.utcnow() + timedelta(minutes=self.config.cooldown_minutes)
            self.cooldown_timers[alert.metric] = cooldown_end
            
            # Log de alerta
            log_eas_warning("ALERT_TRIGGERED", alert.to_dict())
    
    async def _send_alert(self, alert: AlertMessage):
        """Enviar alerta a través de todos los canales habilitados"""
        for channel, handler in self.channels.items():
            if channel in self.config.enabled_channels:
                try:
                    await handler(alert)
                    self.metrics["alerts_by_channel"][channel.value] += 1
                except Exception as e:
                    log_eas_error("ALERT_SEND_ERROR", {
                        "channel": channel.value,
                        "alert_id": alert.id,
                        "error": str(e)
                    })
    
    async def _send_telegram_alert(self, alert: AlertMessage):
        """Enviar alerta por Telegram"""
        # Implementación básica - expandir con bot de Telegram real
        message = f"🚨 {alert.title}\n\n{alert.message}\n\nValor: {alert.current_value}\nUmbral: {alert.threshold}"
        
        # Aquí iría la integración con la API de Telegram
        log_eas_info("TELEGRAM_ALERT_SENT", {
            "alert_id": alert.id,
            "message_preview": message[:100] + "..."
        })
    
    async def _send_email_alert(self, alert: AlertMessage):
        """Enviar alerta por email"""
        # Implementación básica - expandir con SMTP real
        subject = f"[{alert.severity.value}] {alert.title}"
        body = f"""
        Alerta del Sistema EAS Híbrido 2025
        
        Severidad: {alert.severity.value}
        Métrica: {alert.metric}
        Valor Actual: {alert.current_value}
        Umbral: {alert.threshold}
        
        Mensaje: {alert.message}
        
        Timestamp: {alert.timestamp}
        """
        
        log_eas_info("EMAIL_ALERT_SENT", {
            "alert_id": alert.id,
            "subject": subject
        })
    
    async def _send_push_alert(self, alert: AlertMessage):
        """Enviar alerta push"""
        # Implementación para servicios push (Firebase, OneSignal, etc.)
        log_eas_info("PUSH_ALERT_SENT", {
            "alert_id": alert.id,
            "severity": alert.severity.value
        })
    
    async def _send_webhook_alert(self, alert: AlertMessage):
        """Enviar alerta por webhook"""
        try:
            webhook_url = "https://api.eas-hybrid-2025.com/alerts"  # Configurar
            response = requests.post(
                webhook_url,
                json=alert.to_dict(),
                timeout=5
            )
            response.raise_for_status()
        except Exception as e:
            raise Exception(f"Webhook failed: {e}")
    
    async def _send_console_alert(self, alert: AlertMessage):
        """Enviar alerta a consola (para desarrollo)"""
        color_codes = {
            AlertSeverity.LOW: "\033[94m",      # Azul
            AlertSeverity.MEDIUM: "\033[93m",   # Amarillo
            AlertSeverity.HIGH: "\033[91m",     # Rojo
            AlertSeverity.CRITICAL: "\033[95m"  # Magenta
        }
        reset_code = "\033[0m"
        
        color = color_codes.get(alert.severity, "\033[97m")
        print(f"{color}🚨 ALERTA {alert.severity.value}: {alert.title}{reset_code}")
        print(f"   📊 Métrica: {alert.metric}")
        print(f"   📈 Valor: {alert.current_value} | Umbral: {alert.threshold}")
        print(f"   💬 {alert.message}")
        print(f"   ⏰ {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    async def _store_alert_database(self, alert: AlertMessage):
        """Almacenar alerta en base de datos"""
        # Implementación para almacenar en BD (SQLite, PostgreSQL, etc.)
        log_eas_info("ALERT_STORED_DB", {
            "alert_id": alert.id,
            "metric": alert.metric
        })
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Marcar alerta como reconocida"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            log_eas_info("ALERT_ACKNOWLEDGED", {"alert_id": alert_id})
            return True
        return False
    
    def get_active_alerts(self) -> List[AlertMessage]:
        """Obtener alertas activas"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[AlertMessage]:
        """Obtener historial de alertas"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp >= cutoff_time]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtener métricas del sistema de alertas"""
        return self.metrics.copy()

# Instancia global del sistema de alertas
global_alert_system: Optional[AlertSystem] = None

def get_alert_system() -> AlertSystem:
    """Obtener instancia global del sistema de alertas"""
    global global_alert_system
    if global_alert_system is None:
        config = AlertConfig()
        global_alert_system = AlertSystem(config)
    return global_alert_system

async def check_system_alerts(metrics: Dict[str, Any]) -> List[AlertMessage]:
    """Función de conveniencia para verificar alertas del sistema"""
    alert_system = get_alert_system()
    return await alert_system.check_predictive_alerts(metrics)

# Ejemplo de uso
async def example_usage():
    """Ejemplo de uso del sistema de alertas"""
    alert_system = get_alert_system()
    
    # Métricas de ejemplo que dispararían alertas
    test_metrics = {
        'drawdown_risk': 0.75,  # Por encima del umbral 0.6
        'volatility': 3.2,      # Por encima del umbral 2.5
        'error_rate': 0.08,     # Por encima del umbral 0.05
        'ia_confidence': 0.65,  # Por debajo del umbral 0.7
        'execution_latency': 150.0,  # Por encima del umbral 100.0
        'cpu_usage': 0.85       # Por encima del umbral 0.7
    }
    
    alerts = await alert_system.check_predictive_alerts(test_metrics)
    print(f"Se dispararon {len(alerts)} alertas")
    
    # Mostrar métricas
    metrics = alert_system.get_metrics()
    print(f"Métricas del sistema: {metrics}")

if __name__ == "__main__":
    asyncio.run(example_usage())