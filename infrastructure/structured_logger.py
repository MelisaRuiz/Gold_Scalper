##!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Structured Logger Mejorado - EAS Híbrido 2025 Compliance
Mejoras: Métricas de trading específicas, guardrails de seguridad, integración con monitoreo predictivo
"""

import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
import gzip
import threading
import asyncio
import numpy as np
from dataclasses import dataclass, asdict

# Try to import cloud dependencies (optional)
try:
    import boto3
    CLOUDWATCH_AVAILABLE = True
except ImportError:
    CLOUDWATCH_AVAILABLE = False

try:
    import requests
    ELK_AVAILABLE = True
except ImportError:
    ELK_AVAILABLE = False

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING" 
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    TRADE = "TRADE"  # Nivel específico para operaciones de trading
    VALIDATION = "VALIDATION"  # Nivel para validaciones IA

@dataclass
class TradingMetrics:
    """Métricas específicas de trading para monitoreo EAS"""
    daily_pnl: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    current_risk_exposure: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    kill_switch_status: str = "INACTIVE"

@dataclass
class ExecutionMetrics:
    """Métricas de ejecución para scalping de alta frecuencia"""
    avg_execution_time: float = 0.0
    slippage_avg: float = 0.0
    error_rate: float = 0.0
    requote_rate: float = 0.0
    latency_ms: float = 0.0

@dataclass
class IAMetrics:
    """Métricas específicas de los agentes IA"""
    validation_accuracy: float = 0.0
    response_time_ms: float = 0.0
    consensus_score: float = 0.0
    guardrail_triggers: int = 0
    safety_score: float = 1.0

class StructuredLogger:
    def __init__(self, name: str = "HECTAGoldStructured", log_dir: str = "logs",
                 max_file_size_mb: int = 100, backup_count: int = 10, 
                 enable_compression: bool = True, enable_cloudwatch: bool = False, 
                 enable_elk: bool = False, enable_predictive_alerts: bool = True):
        
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.backup_count = backup_count
        self.enable_compression = enable_compression
        self.enable_cloudwatch = enable_cloudwatch and CLOUDWATCH_AVAILABLE
        self.enable_elk = enable_elk and ELK_AVAILABLE
        self.enable_predictive_alerts = enable_predictive_alerts
        
        # Configurar logger base
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            self._setup_handlers()
        
        # Buffer y estado
        self.memory_buffer: List[Dict[str, Any]] = []
        self.buffer_lock = threading.Lock()
        self.max_buffer_size = 5000  # Aumentado para trading HFT
        
        # Métricas EAS específicas
        self.trading_metrics = TradingMetrics()
        self.execution_metrics = ExecutionMetrics()
        self.ia_metrics = IAMetrics()
        
        # Estadísticas avanzadas
        self.stats = {
            'total_logs': 0, 
            'logs_by_level': {level.value: 0 for level in LogLevel},
            'last_log_time': None, 
            'error_count': 0, 
            'warning_count': 0,
            'trade_count': 0,
            'validation_count': 0,
            'anomaly_count': 0
        }
        
        # Sistema de alertas predictivas
        self.alert_thresholds = {
            "drawdown_alert": 0.6,
            "volatility_spike": 2.5,
            "error_spike": 0.05,
            "ia_confidence_drop": 0.7,
            "execution_latency_spike": 100.0  # ms
        }
        
        # Callbacks para alertas
        self.alert_callbacks: List[Callable] = []
        
        # Inicializar servicios cloud
        if self.enable_cloudwatch:
            self.cloudwatch = boto3.client('logs')
        if self.enable_elk:
            self.elk_url = "http://localhost:9200/hecta-logs"
            
        self.logger.info(f"📝 Logger EAS '{name}' inicializado (ELK: {enable_elk}, CloudWatch: {enable_cloudwatch})")

    def _setup_handlers(self):
        """Configurar handlers de logging con formatos EAS específicos"""
        
        # Handler consola para desarrollo
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s', 
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # Handler JSON para producción
        json_handler = logging.FileHandler(self.log_dir / f"{self.name.lower()}.json")
        json_handler.setFormatter(EASJsonFormatter())
        self.logger.addHandler(json_handler)
        
        # Handler específico para trades
        trade_handler = logging.FileHandler(self.log_dir / f"{self.name.lower()}_trades.json")
        trade_handler.setFormatter(EASJsonFormatter())
        trade_handler.addFilter(TradeFilter())
        self.logger.addHandler(trade_handler)

    def log_structured(self, level: LogLevel, event_type: str, data: Dict[str, Any], 
                      context: Optional[Dict[str, Any]] = None, 
                      metrics_update: Optional[Dict[str, Any]] = None):
        """
        Log estructurado mejorado con capacidades EAS
        """
        timestamp = datetime.utcnow()
        
        # Crear entrada con metadata EAS
        entry = {
            "timestamp": timestamp.isoformat(),
            "level": level.value,
            "event_type": event_type,
            "data": data,
            "context": context or {},
            "system_metadata": {
                "version": "EAS_Hybrid_2025",
                "component": self.name,
                "session_id": context.get('session_id', 'default') if context else 'default'
            },
            "anomaly_flag": self._detect_anomaly(data),
            "predictive_risk_score": self._calculate_predictive_risk(data, context)
        }
        
        # Actualizar métricas si se proporcionan
        if metrics_update:
            self._update_metrics(metrics_update)
            entry["current_metrics"] = {
                "trading": asdict(self.trading_metrics),
                "execution": asdict(self.execution_metrics),
                "ia": asdict(self.ia_metrics)
            }

        # Gestión de buffer y estadísticas
        with self.buffer_lock:
            self.memory_buffer.append(entry)
            if len(self.memory_buffer) > self.max_buffer_size:
                self.memory_buffer.pop(0)
            
            self._update_stats(level, timestamp)
            
            # Detección de spikes para alertas predictivas
            if self.enable_predictive_alerts:
                alerts = self._check_predictive_alerts(entry)
                if alerts:
                    self._trigger_alerts(alerts, entry)

        # Logging tradicional
        log_method = getattr(self.logger, level.value.lower(), self.logger.info)
        extra_fields = {'extra_fields': entry}
        log_method(json.dumps(entry, default=str), extra=extra_fields)
        
        # Exportar a servicios externos
        if self.enable_cloudwatch:
            self._export_to_cloudwatch(entry)
        if self.enable_elk:
            self._export_to_elk(entry)

    def _detect_anomaly(self, data: Dict[str, Any]) -> bool:
        """Detección de anomalías mejorada para trading"""
        try:
            # Extraer valores numéricos
            nums = []
            for value in data.values():
                if isinstance(value, (int, float)):
                    nums.append(value)
                elif isinstance(value, dict):
                    # Buscar en sub-diccionarios para métricas anidadas
                    nums.extend([v for v in value.values() if isinstance(v, (int, float))])
            
            if len(nums) < 3:  # Mínimo para análisis significativo
                return False
                
            arr = np.array(nums, dtype=np.float64)
            z_scores = np.abs((arr - arr.mean()) / arr.std()) if arr.std() > 0 else np.zeros_like(arr)
            
            # Umbral adaptativo basado en volatilidad histórica
            anomaly_threshold = 3.5 if len(self.memory_buffer) > 100 else 4.0
            is_anomaly = (z_scores > anomaly_threshold).any()
            
            if is_anomaly:
                self.stats['anomaly_count'] += 1
                
            return is_anomaly
            
        except Exception as e:
            self.logger.error(f"Anomaly detection error: {e}")
            return False

    def _calculate_predictive_risk(self, data: Dict[str, Any], context: Optional[Dict[str, Any]]) -> float:
        """Calcular score de riesgo predictivo para EAS"""
        risk_score = 0.0
        
        try:
            # Factores de riesgo para trading
            risk_factors = []
            
            # Factor 1: Volatilidad en datos
            if 'volatility' in data:
                volatility = data['volatility']
                if volatility > 2.0:
                    risk_factors.append(0.3)
                    
            # Factor 2: Métricas de ejecución
            if 'execution_time' in data:
                exec_time = data['execution_time']
                if exec_time > 50:  # ms
                    risk_factors.append(0.2)
                    
            # Factor 3: Confianza IA
            if 'confidence' in data:
                confidence = data['confidence']
                if confidence < 0.8:
                    risk_factors.append(0.4)
                    
            # Factor 4: Drawdown actual
            if hasattr(self.trading_metrics, 'max_drawdown'):
                if self.trading_metrics.max_drawdown > 5.0:
                    risk_factors.append(0.5)
                    
            # Calcular score compuesto
            if risk_factors:
                risk_score = sum(risk_factors) / len(risk_factors)
                
        except Exception as e:
            self.logger.warning(f"Risk calculation error: {e}")
            
        return min(risk_score, 1.0)

    def _update_metrics(self, metrics_update: Dict[str, Any]):
        """Actualizar métricas EAS específicas"""
        for metric_type, values in metrics_update.items():
            if metric_type == "trading" and hasattr(self.trading_metrics, 'daily_pnl'):
                for key, value in values.items():
                    if hasattr(self.trading_metrics, key):
                        setattr(self.trading_metrics, key, value)
            elif metric_type == "execution" and hasattr(self.execution_metrics, 'avg_execution_time'):
                for key, value in values.items():
                    if hasattr(self.execution_metrics, key):
                        setattr(self.execution_metrics, key, value)
            elif metric_type == "ia" and hasattr(self.ia_metrics, 'validation_accuracy'):
                for key, value in values.items():
                    if hasattr(self.ia_metrics, key):
                        setattr(self.ia_metrics, key, value)

    def _update_stats(self, level: LogLevel, timestamp: datetime):
        """Actualizar estadísticas internas"""
        self.stats['total_logs'] += 1
        self.stats['logs_by_level'][level.value] += 1
        self.stats['last_log_time'] = timestamp.isoformat()
        
        if level == LogLevel.ERROR:
            self.stats['error_count'] += 1
        elif level == LogLevel.WARNING:
            self.stats['warning_count'] += 1
        elif level == LogLevel.TRADE:
            self.stats['trade_count'] += 1
        elif level == LogLevel.VALIDATION:
            self.stats['validation_count'] += 1

    def _check_predictive_alerts(self, entry: Dict[str, Any]) -> List[str]:
        """Sistema de alertas predictivas EAS"""
        alerts = []
        
        try:
            # Alerta 1: Drawdown risk
            if (hasattr(self.trading_metrics, 'daily_pnl') and 
                hasattr(self.trading_metrics, 'max_drawdown') and
                self.trading_metrics.max_drawdown > 0):
                
                drawdown_risk = abs(self.trading_metrics.daily_pnl) / self.trading_metrics.max_drawdown
                if drawdown_risk > self.alert_thresholds["drawdown_alert"]:
                    alerts.append("ALERTA: Riesgo de drawdown detectado")
            
            # Alerta 2: Latencia de ejecución
            if (hasattr(self.execution_metrics, 'latency_ms') and
                self.execution_metrics.latency_ms > self.alert_thresholds["execution_latency_spike"]):
                alerts.append("ALERTA: Spike de latencia en ejecución")
                
            # Alerta 3: Confianza IA
            if (hasattr(self.ia_metrics, 'validation_accuracy') and
                self.ia_metrics.validation_accuracy < self.alert_thresholds["ia_confidence_drop"]):
                alerts.append("ALERTA: Caída en confianza de validación IA")
                
            # Alerta 4: Tasa de errores
            if (hasattr(self.execution_metrics, 'error_rate') and
                self.execution_metrics.error_rate > self.alert_thresholds["error_spike"]):
                alerts.append("ALERTA: Spike en tasa de errores")
                
        except Exception as e:
            self.logger.error(f"Predictive alert error: {e}")
            
        return alerts

    def _trigger_alerts(self, alerts: List[str], entry: Dict[str, Any]):
        """Disparar alertas a través de callbacks registrados"""
        for alert in alerts:
            for callback in self.alert_callbacks:
                try:
                    callback(alert, entry)
                except Exception as e:
                    self.logger.error(f"Alert callback error: {e}")

    def register_alert_callback(self, callback: Callable):
        """Registrar callback para alertas predictivas"""
        self.alert_callbacks.append(callback)

    def log_trade_execution(self, trade_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """Log especializado para ejecución de trades"""
        metrics_update = {
            "trading": {
                "daily_pnl": trade_data.get('pnl', 0),
                "current_risk_exposure": trade_data.get('risk_exposure', 0)
            },
            "execution": {
                "avg_execution_time": trade_data.get('execution_time', 0),
                "slippage_avg": trade_data.get('slippage', 0)
            }
        }
        
        self.log_structured(LogLevel.TRADE, "TRADE_EXECUTION", trade_data, context, metrics_update)

    def log_ia_validation(self, validation_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """Log especializado para validaciones IA"""
        metrics_update = {
            "ia": {
                "validation_accuracy": validation_data.get('confidence', 0),
                "response_time_ms": validation_data.get('response_time', 0),
                "safety_score": validation_data.get('safety_score', 1.0)
            }
        }
        
        self.log_structured(LogLevel.VALIDATION, "IA_VALIDATION", validation_data, context, metrics_update)

    def _export_to_elk(self, entry: Dict[str, Any]):
        """Exportar a ELK Stack"""
        if not ELK_AVAILABLE:
            return
            
        try:
            requests.post(self.elk_url, json=entry, timeout=2)  # Timeout reducido para HFT
        except Exception as e:
            self.logger.debug(f"ELK export failed: {e}")

    def _export_to_cloudwatch(self, entry: Dict[str, Any]):
        """Exportar a AWS CloudWatch"""
        if not CLOUDWATCH_AVAILABLE:
            return
            
        try:
            self.cloudwatch.put_log_events(
                logGroupName=f"/eas-hybrid-2025/{self.name}",
                logStreamName="structured-logs",
                logEvents=[{
                    'timestamp': int(datetime.fromisoformat(entry['timestamp']).timestamp() * 1000), 
                    'message': json.dumps(entry)
                }]
            )
        except Exception as e:
            self.logger.debug(f"CloudWatch export failed: {e}")

    def rotate_logs(self):
        """Rotación de logs con compresión para EAS"""
        json_file = self.log_dir / f"{self.name.lower()}.json"
        if json_file.exists() and json_file.stat().st_size > self.max_file_size:
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            gz_file = self.log_dir / f"{self.name.lower()}_{timestamp}.json.gz"
            
            try:
                with open(json_file, 'rb') as f_in, gzip.open(gz_file, 'wb') as f_out:
                    f_out.write(f_in.read())
                json_file.unlink()
                
                # Gestión de backups
                backups = sorted(self.log_dir.glob(f"{self.name.lower()}_*.json.gz"))
                if len(backups) > self.backup_count:
                    for old in backups[:-self.backup_count]:
                        old.unlink()
                        
                self.logger.info("📦 Logs EAS rotados y comprimidos")
                
            except Exception as e:
                self.logger.error(f"Log rotation failed: {e}")

    def get_eas_metrics(self) -> Dict[str, Any]:
        """Obtener métricas EAS consolidadas"""
        return {
            "trading_metrics": asdict(self.trading_metrics),
            "execution_metrics": asdict(self.execution_metrics),
            "ia_metrics": asdict(self.ia_metrics),
            "system_stats": self.stats
        }

    def export_trading_report(self, start_time: datetime, end_time: datetime) -> Path:
        """Exportar reporte específico de trading"""
        with self.buffer_lock:
            trading_logs = [
                log for log in self.memory_buffer 
                if (log['level'] == 'TRADE' and 
                    start_time <= datetime.fromisoformat(log['timestamp']) <= end_time)
            ]
            
        report_file = self.log_dir / f"trading_report_{start_time.strftime('%Y%m%d')}_{end_time.strftime('%Y%m%d')}.json"
        
        report = {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "summary": {
                "total_trades": len(trading_logs),
                "metrics": self.get_eas_metrics()
            },
            "detailed_trades": trading_logs
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
            
        return report_file

# =============================================================================
# Clases auxiliares
# =============================================================================

class EASJsonFormatter(logging.Formatter):
    """Formateador JSON específico para EAS"""
    
    def format(self, record):
        entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
            
        if hasattr(record, 'extra_fields'):
            entry.update(record.extra_fields)
            
        return json.dumps(entry, default=str)

class TradeFilter(logging.Filter):
    """Filtro para logs de trading"""
    
    def filter(self, record):
        if hasattr(record, 'extra_fields'):
            return record.extra_fields.get('level') == 'TRADE'
        return False

# =============================================================================
# Instancia global y funciones helper
# =============================================================================

global_eas_logger = None

def get_eas_logger(name: str = "HECTAGoldStructured") -> StructuredLogger:
    global global_eas_logger
    if global_eas_logger is None:
        global_eas_logger = StructuredLogger(name)
    return global_eas_logger

def log_trade(trade_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
    get_eas_logger().log_trade_execution(trade_data, context)

def log_validation(validation_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
    get_eas_logger().log_ia_validation(validation_data, context)

def log_eas_info(event_type: str, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
    get_eas_logger().log_structured(LogLevel.INFO, event_type, data, context)

def log_eas_warning(event_type: str, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
    get_eas_logger().log_structured(LogLevel.WARNING, event_type, data, context)

def log_eas_error(event_type: str, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
    get_eas_logger().log_structured(LogLevel.ERROR, event_type, data, context)