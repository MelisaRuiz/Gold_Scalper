#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Performance Tracker v3.0 - EAS Híbrido 2025 Integration
Sistema especializado para métricas de trading con integración HealthMonitor y arquitectura de agentes
"""

import asyncio
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd
import psutil
from prometheus_client import start_http_server, Gauge, Counter, Histogram, generate_latest
import aiohttp

# Importaciones de la nueva arquitectura
from infrastructure.structured_logger import StructuredLogger
from infrastructure.health_monitor import get_health_monitor
from infrastructure.circuit_breaker import CircuitBreaker

logger = StructuredLogger("HECTAGold.PerformanceTracker")

class TradingPhase(Enum):
    """Fases del trading según EAS Híbrido 2025"""
    MARKET_ANALYSIS = "market_analysis"
    SIGNAL_VALIDATION = "signal_validation"
    RISK_ASSESSMENT = "risk_assessment"
    ORDER_EXECUTION = "order_execution"
    POSITION_MANAGEMENT = "position_management"
    PERFORMANCE_REVIEW = "performance_review"

class MetricCategory(Enum):
    """Categorías de métricas especializadas"""
    TRADING_PERFORMANCE = "trading_performance"
    RISK_METRICS = "risk_metrics"
    EXECUTION_QUALITY = "execution_quality"
    IA_VALIDATION = "ia_validation"
    SYSTEM_HEALTH = "system_health"
    MARKET_CONDITIONS = "market_conditions"

@dataclass
class TradingMetric:
    """Métrica especializada para trading EAS Híbrido 2025"""
    name: str
    value: float
    category: MetricCategory
    timestamp: datetime
    phase: TradingPhase
    unit: str = ""
    threshold_min: Optional[float] = None
    threshold_max: Optional[float] = None
    status: str = "normal"  # normal, warning, critical
    confidence: float = 1.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class TradeRecord:
    """Registro completo de trade para análisis"""
    trade_id: str
    symbol: str
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    position_size: float
    pnl: Optional[float]
    pnl_percent: Optional[float]
    risk_multiplier: float
    signal_confidence: float
    ia_validation_score: float
    execution_quality: float
    phase_durations: Dict[TradingPhase, float]
    metadata: Dict[str, Any]

class EASPerformanceMetrics:
    """Métricas Prometheus especializadas para EAS Híbrido 2025"""
    
    def __init__(self, port: int = 8000):
        self.port = port
        
        # Trading Performance Gauges
        self.trading_gauges = {
            'daily_pnl': Gauge('eas_daily_pnl_usd', 'Daily P&L in USD'),
            'win_rate': Gauge('eas_win_rate_percent', 'Win rate percentage'),
            'profit_factor': Gauge('eas_profit_factor', 'Profit factor ratio'),
            'sharpe_ratio': Gauge('eas_sharpe_ratio', 'Sharpe ratio'),
            'max_drawdown': Gauge('eas_max_drawdown_percent', 'Maximum drawdown percentage'),
            'current_drawdown': Gauge('eas_current_drawdown_percent', 'Current drawdown percentage'),
            'active_positions': Gauge('eas_active_positions', 'Active trading positions'),
            'daily_trades': Gauge('eas_daily_trades_count', 'Daily trades count')
        }
        
        # Risk Metrics
        self.risk_gauges = {
            'risk_multiplier': Gauge('eas_risk_multiplier', 'Current risk multiplier'),
            'risk_exposure': Gauge('eas_risk_exposure_percent', 'Current risk exposure percentage'),
            'consecutive_wins': Gauge('eas_consecutive_wins', 'Consecutive wins count'),
            'consecutive_losses': Gauge('eas_consecutive_losses', 'Consecutive losses count'),
            'kill_switch_status': Gauge('eas_kill_switch_active', 'Kill switch status (1=active)')
        }
        
        # Execution Quality
        self.execution_gauges = {
            'avg_execution_time': Gauge('eas_avg_execution_time_ms', 'Average execution time in ms'),
            'slippage_avg': Gauge('eas_avg_slippage_pips', 'Average slippage in pips'),
            'error_rate': Gauge('eas_execution_error_rate', 'Execution error rate percentage'),
            'requote_rate': Gauge('eas_requote_rate', 'Requote rate percentage')
        }
        
        # IA Validation Metrics
        self.ia_gauges = {
            'validation_accuracy': Gauge('eas_validation_accuracy', 'IA validation accuracy'),
            'response_time_ms': Gauge('eas_ia_response_time_ms', 'IA response time in ms'),
            'consensus_score': Gauge('eas_consensus_score', 'IA consensus score'),
            'guardrail_triggers': Gauge('eas_guardrail_triggers', 'Guardrail triggers count')
        }
        
        # Counters
        self.trades_counter = Counter('eas_trades_total', 'Total trades executed', ['symbol', 'outcome'])
        self.signals_counter = Counter('eas_signals_total', 'Total signals generated', ['type', 'decision'])
        self.alerts_counter = Counter('eas_alerts_total', 'Total alerts', ['level', 'component'])
        self.errors_counter = Counter('eas_errors_total', 'Total system errors', ['component'])
        
        # Histograms
        self.execution_time_histogram = Histogram('eas_execution_time_distribution', 'Trade execution time distribution')
        self.ia_response_histogram = Histogram('eas_ia_response_time_distribution', 'IA response time distribution')
        self.slippage_histogram = Histogram('eas_slippage_distribution', 'Slippage distribution')

    def start_server(self):
        """Inicia servidor Prometheus"""
        try:
            start_http_server(self.port)
            logger.info(f"📈 Servidor Prometheus EAS iniciado en puerto {self.port}")
        except Exception as e:
            logger.error(f"❌ Error iniciando servidor Prometheus: {e}")

    def record_trade(self, symbol: str, outcome: str, execution_time: float, slippage: float):
        """Registra un trade ejecutado"""
        self.trades_counter.labels(symbol=symbol, outcome=outcome).inc()
        self.execution_time_histogram.observe(execution_time)
        self.slippage_histogram.observe(slippage)

    def record_signal(self, signal_type: str, decision: str, response_time: float):
        """Registra una señal procesada"""
        self.signals_counter.labels(type=signal_type, decision=decision).inc()
        self.ia_response_histogram.observe(response_time)

    def record_alert(self, level: str, component: str):
        """Registra una alerta"""
        self.alerts_counter.labels(level=level, component=component).inc()

    def record_error(self, component: str):
        """Registra un error"""
        self.errors_counter.labels(component=component).inc()

class PerformanceTracker:
    """
    Sistema de tracking de performance especializado para EAS Híbrido 2025
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el tracker de performance
        
        Args:
            config: Configuración del sistema EAS
        """
        self.config = config
        self.tracking_config = config.get('performance_tracking', {})
        
        # Métricas Prometheus
        self.prometheus_port = self.tracking_config.get('prometheus_port', 8000)
        self.prometheus = EASPerformanceMetrics(self.prometheus_port)
        
        # Base de datos especializada
        self.db_path = Path("data/performance.db")
        self.db_path.parent.mkdir(exist_ok=True)
        
        # Estado del tracker
        self.is_running = False
        self.metrics: Dict[str, TradingMetric] = {}
        self.trade_records: List[TradeRecord] = []
        
        # Configuraciones específicas EAS
        self.risk_config = config.get('risk_config', {})
        self.trading_sessions = config.get('trading_sessions', {})
        
        # Umbrales EAS Híbrido 2025
        self.thresholds = {
            'max_drawdown': 6.0,  # 6% máximo
            'daily_loss_limit': 1.0,  # 1% diario
            'consecutive_losses': 2,  # Kill switch
            'min_win_rate': 60.0,  # 60% mínimo
            'max_execution_time': 100.0,  # 100ms máximo
            'min_ia_confidence': 0.7  # 70% confianza IA mínima
        }
        
        # Históricos para análisis
        self.metrics_history: Dict[str, List[TradingMetric]] = {}
        self.performance_history = []
        self.max_history_size = 5000
        
        # Análisis predictivo
        self.zscore_thresholds = {
            'drawdown_risk': 0.5,
            'volatility_spike': 2.0,
            'performance_anomaly': 2.5
        }
        
        # Circuit breaker para protección
        self.circuit_breaker = CircuitBreaker(max_failures=3, reset_timeout=300)
        
        # Inicializar componentes
        self._init_database()
        self.prometheus.start_server()
        
        logger.info("🎯 PerformanceTracker EAS Híbrido 2025 inicializado")

    async def start(self):
        """Inicia el tracker de performance"""
        self.is_running = True
        
        # Iniciar tareas en segundo plano
        asyncio.create_task(self._metrics_collection_loop())
        asyncio.create_task(self._performance_analysis_loop())
        asyncio.create_task(self._risk_monitoring_loop())
        asyncio.create_task(self._reporting_loop())
        
        # Integración con HealthMonitor
        health_monitor = get_health_monitor()
        health_monitor.register_health_callback(self._health_callback)
        
        logger.info("🚀 PerformanceTracker iniciado con integración HealthMonitor")

    def stop(self):
        """Detiene el tracker"""
        self.is_running = False
        logger.info("🛑 PerformanceTracker detenido")

    def record_trade_execution(self, trade_data: Dict[str, Any]):
        """
        Registra la ejecución de un trade con métricas EAS
        
        Args:
            trade_data: Datos completos del trade
        """
        try:
            # Crear registro de trade
            trade_record = TradeRecord(
                trade_id=trade_data.get('trade_id', f"trade_{int(time.time())}"),
                symbol=trade_data.get('symbol', 'XAUUSD'),
                entry_time=trade_data.get('entry_time', datetime.utcnow()),
                exit_time=trade_data.get('exit_time'),
                entry_price=trade_data.get('entry_price', 0.0),
                exit_price=trade_data.get('exit_price'),
                position_size=trade_data.get('position_size', 0.0),
                pnl=trade_data.get('pnl'),
                pnl_percent=trade_data.get('pnl_percent'),
                risk_multiplier=trade_data.get('risk_multiplier', 1.0),
                signal_confidence=trade_data.get('signal_confidence', 0.0),
                ia_validation_score=trade_data.get('ia_validation_score', 0.0),
                execution_quality=trade_data.get('execution_quality', 0.0),
                phase_durations=trade_data.get('phase_durations', {}),
                metadata=trade_data.get('metadata', {})
            )
            
            self.trade_records.append(trade_record)
            
            # Actualizar Prometheus
            outcome = "win" if (trade_record.pnl or 0) > 0 else "loss"
            execution_time = trade_record.phase_durations.get(TradingPhase.ORDER_EXECUTION, 0)
            slippage = trade_record.metadata.get('slippage', 0)
            
            self.prometheus.record_trade(
                trade_record.symbol, 
                outcome, 
                execution_time, 
                slippage
            )
            
            # Guardar en base de datos
            self._save_trade_to_db(trade_record)
            
            # Actualizar métricas derivadas
            self._update_performance_metrics()
            
            logger.debug(
                f"💰 Trade registrado: {trade_record.symbol} | "
                f"PNL: {trade_record.pnl:.2f} | "
                f"Confianza: {trade_record.signal_confidence:.3f}",
                extra=asdict(trade_record)
            )
            
        except Exception as e:
            logger.error(f"❌ Error registrando trade: {e}")
            self.prometheus.record_error("trade_recording")

    def record_signal_validation(self, signal_data: Dict[str, Any]):
        """
        Registra validación de señal por IA
        
        Args:
            signal_data: Datos de validación de señal
        """
        try:
            signal_type = signal_data.get('signal_type', 'BOS_RETEST')
            decision = signal_data.get('decision', 'REJECT')
            response_time = signal_data.get('response_time', 0.0)
            confidence = signal_data.get('confidence', 0.0)
            
            # Registrar en Prometheus
            self.prometheus.record_signal(signal_type, decision, response_time)
            
            # Crear métrica de validación
            metric = TradingMetric(
                name="ia_validation_score",
                value=confidence,
                category=MetricCategory.IA_VALIDATION,
                timestamp=datetime.utcnow(),
                phase=TradingPhase.SIGNAL_VALIDATION,
                unit="score",
                threshold_min=self.thresholds['min_ia_confidence'],
                status="critical" if confidence < self.thresholds['min_ia_confidence'] else "normal",
                confidence=confidence,
                metadata=signal_data
            )
            
            self._register_metric(metric)
            
        except Exception as e:
            logger.error(f"❌ Error registrando validación de señal: {e}")
            self.prometheus.record_error("signal_validation")

    def record_risk_assessment(self, risk_data: Dict[str, Any]):
        """
        Registra evaluación de riesgo
        
        Args:
            risk_data: Datos de evaluación de riesgo
        """
        try:
            risk_multiplier = risk_data.get('risk_multiplier', 1.0)
            exposure = risk_data.get('risk_exposure', 0.0)
            
            # Métrica de multiplicador de riesgo
            risk_metric = TradingMetric(
                name="risk_multiplier",
                value=risk_multiplier,
                category=MetricCategory.RISK_METRICS,
                timestamp=datetime.utcnow(),
                phase=TradingPhase.RISK_ASSESSMENT,
                unit="multiplier",
                threshold_max=1.5,  # Límite EAS
                status="warning" if risk_multiplier > 1.5 else "normal",
                metadata=risk_data
            )
            
            self._register_metric(risk_metric)
            
            # Métrica de exposición
            exposure_metric = TradingMetric(
                name="risk_exposure",
                value=exposure,
                category=MetricCategory.RISK_METRICS,
                timestamp=datetime.utcnow(),
                phase=TradingPhase.RISK_ASSESSMENT,
                unit="percent",
                threshold_max=self.thresholds['daily_loss_limit'],
                status="critical" if exposure > self.thresholds['daily_loss_limit'] else "normal",
                metadata=risk_data
            )
            
            self._register_metric(exposure_metric)
            
            # Actualizar Prometheus
            self.prometheus.risk_gauges['risk_multiplier'].set(risk_multiplier)
            self.prometheus.risk_gauges['risk_exposure'].set(exposure)
            
        except Exception as e:
            logger.error(f"❌ Error registrando evaluación de riesgo: {e}")

    def _register_metric(self, metric: TradingMetric):
        """Registra una métrica en el sistema"""
        self.metrics[metric.name] = metric
        
        # Actualizar historial
        if metric.name not in self.metrics_history:
            self.metrics_history[metric.name] = []
        
        self.metrics_history[metric.name].append(metric)
        
        # Mantener tamaño del historial
        if len(self.metrics_history[metric.name]) > self.max_history_size:
            self.metrics_history[metric.name] = self.metrics_history[metric.name][-self.max_history_size:]
        
        # Guardar en base de datos
        self._save_metric_to_db(metric)
        
        # Verificar alertas
        self._check_metric_alert(metric)

    def _check_metric_alert(self, metric: TradingMetric):
        """Verifica si una métrica genera alerta"""
        if metric.status == "critical":
            alert_level = "CRITICAL"
        elif metric.status == "warning":
            alert_level = "WARNING"
        else:
            return
            
        self.prometheus.record_alert(alert_level, metric.category.value)
        
        # Enviar alerta a HealthMonitor
        health_monitor = get_health_monitor()
        health_monitor.update_metrics("performance_alerts", {
            f"alert_{metric.name}": {
                "level": alert_level,
                "value": metric.value,
                "threshold": metric.threshold_max or metric.threshold_min,
                "timestamp": metric.timestamp.isoformat()
            }
        })

    async def _metrics_collection_loop(self):
        """Bucle de recolección de métricas del sistema"""
        while self.is_running:
            try:
                # Recolectar métricas básicas del sistema
                await self._collect_system_metrics()
                
                # Recolectar métricas de trading
                await self._collect_trading_metrics()
                
                # Actualizar HealthMonitor
                await self._update_health_monitor()
                
                await asyncio.sleep(10)  # 10 segundos
                
            except Exception as e:
                logger.error(f"❌ Error en recolección de métricas: {e}")
                await asyncio.sleep(30)

    async def _collect_system_metrics(self):
        """Recolecta métricas del sistema"""
        try:
            # Métricas de ejecución
            avg_execution_time = self._calculate_avg_execution_time()
            error_rate = self._calculate_error_rate()
            
            execution_metric = TradingMetric(
                name="avg_execution_time",
                value=avg_execution_time,
                category=MetricCategory.EXECUTION_QUALITY,
                timestamp=datetime.utcnow(),
                phase=TradingPhase.ORDER_EXECUTION,
                unit="ms",
                threshold_max=self.thresholds['max_execution_time'],
                status="critical" if avg_execution_time > self.thresholds['max_execution_time'] else "normal"
            )
            
            self._register_metric(execution_metric)
            self.prometheus.execution_gauges['avg_execution_time'].set(avg_execution_time)
            self.prometheus.execution_gauges['error_rate'].set(error_rate)
            
        except Exception as e:
            logger.error(f"❌ Error recolectando métricas del sistema: {e}")

    async def _collect_trading_metrics(self):
        """Recolecta métricas de trading"""
        try:
            # Calcular métricas de performance
            daily_pnl = self._calculate_daily_pnl()
            win_rate = self._calculate_win_rate()
            profit_factor = self._calculate_profit_factor()
            current_drawdown = self._calculate_current_drawdown()
            
            # Métrica de PnL diario
            pnl_metric = TradingMetric(
                name="daily_pnl",
                value=daily_pnl,
                category=MetricCategory.TRADING_PERFORMANCE,
                timestamp=datetime.utcnow(),
                phase=TradingPhase.PERFORMANCE_REVIEW,
                unit="USD",
                status="critical" if daily_pnl < -self._get_daily_loss_limit() else "normal"
            )
            self._register_metric(pnl_metric)
            self.prometheus.trading_gauges['daily_pnl'].set(daily_pnl)
            
            # Métrica de win rate
            win_rate_metric = TradingMetric(
                name="win_rate",
                value=win_rate,
                category=MetricCategory.TRADING_PERFORMANCE,
                timestamp=datetime.utcnow(),
                phase=TradingPhase.PERFORMANCE_REVIEW,
                unit="percent",
                threshold_min=self.thresholds['min_win_rate'],
                status="warning" if win_rate < self.thresholds['min_win_rate'] else "normal"
            )
            self._register_metric(win_rate_metric)
            self.prometheus.trading_gauges['win_rate'].set(win_rate)
            self.prometheus.trading_gauges['profit_factor'].set(profit_factor)
            self.prometheus.trading_gauges['current_drawdown'].set(current_drawdown)
            
        except Exception as e:
            logger.error(f"❌ Error recolectando métricas de trading: {e}")

    async def _performance_analysis_loop(self):
        """Bucle de análisis de performance predictivo"""
        while self.is_running:
            try:
                # Análisis de tendencias
                await self._analyze_performance_trends()
                
                # Detección de anomalías
                await self._detect_performance_anomalies()
                
                # Predicción de drawdown
                drawdown_risk = self._predict_drawdown_risk()
                if drawdown_risk > self.zscore_thresholds['drawdown_risk']:
                    logger.warning(
                        f"📉 Riesgo de drawdown detectado (Z-score: {drawdown_risk:.2f})",
                        extra={"drawdown_zscore": drawdown_risk}
                    )
                
                await asyncio.sleep(60)  # 1 minuto
                
            except Exception as e:
                logger.error(f"❌ Error en análisis de performance: {e}")
                await asyncio.sleep(120)

    async def _risk_monitoring_loop(self):
        """Bucle de monitoreo de riesgo"""
        while self.is_running:
            try:
                # Verificar límites de riesgo
                await self._check_risk_limits()
                
                # Verificar kill switch conditions
                await self._check_kill_switch()
                
                await asyncio.sleep(30)  # 30 segundos
                
            except Exception as e:
                logger.error(f"❌ Error en monitoreo de riesgo: {e}")
                await asyncio.sleep(60)

    async def _reporting_loop(self):
        """Bucle de generación de reportes"""
        while self.is_running:
            try:
                # Generar reporte de performance
                report = self.generate_performance_report()
                
                # Enviar a HealthMonitor
                health_monitor = get_health_monitor()
                health_monitor.update_metrics("performance_report", report)
                
                # Log resumen de performance
                if len(self.trade_records) > 0:
                    logger.info(
                        f"📊 Performance Report: {report['win_rate']:.1f}% Win Rate | "
                        f"PnL: ${report['daily_pnl']:.2f} | "
                        f"Drawdown: {report['current_drawdown']:.2f}%",
                        extra=report
                    )
                
                await asyncio.sleep(300)  # 5 minutos
                
            except Exception as e:
                logger.error(f"❌ Error generando reporte: {e}")
                await asyncio.sleep(600)

    def _calculate_avg_execution_time(self) -> float:
        """Calcula tiempo promedio de ejecución"""
        if not self.trade_records:
            return 0.0
        
        execution_times = [
            trade.phase_durations.get(TradingPhase.ORDER_EXECUTION, 0)
            for trade in self.trade_records[-50:]  # Últimos 50 trades
        ]
        
        return np.mean(execution_times) if execution_times else 0.0

    def _calculate_error_rate(self) -> float:
        """Calcula tasa de errores de ejecución"""
        if not self.trade_records:
            return 0.0
        
        recent_trades = self.trade_records[-100:]
        error_count = sum(1 for trade in recent_trades if trade.metadata.get('error', False))
        
        return (error_count / len(recent_trades)) * 100 if recent_trades else 0.0

    def _calculate_daily_pnl(self) -> float:
        """Calcula PnL diario"""
        today = datetime.utcnow().date()
        daily_trades = [
            trade for trade in self.trade_records
            if trade.entry_time.date() == today and trade.pnl is not None
        ]
        
        return sum(trade.pnl for trade in daily_trades)

    def _calculate_win_rate(self) -> float:
        """Calcula win rate"""
        if not self.trade_records:
            return 0.0
        
        winning_trades = [trade for trade in self.trade_records if trade.pnl and trade.pnl > 0]
        return (len(winning_trades) / len(self.trade_records)) * 100

    def _calculate_profit_factor(self) -> float:
        """Calcula profit factor"""
        if not self.trade_records:
            return 0.0
        
        gross_profit = sum(trade.pnl for trade in self.trade_records if trade.pnl and trade.pnl > 0)
        gross_loss = abs(sum(trade.pnl for trade in self.trade_records if trade.pnl and trade.pnl < 0))
        
        return gross_profit / gross_loss if gross_loss > 0 else float('inf')

    def _calculate_current_drawdown(self) -> float:
        """Calcula drawdown actual"""
        if not self.trade_records:
            return 0.0
        
        # Implementación simplificada - en producción usar equity curve
        recent_pnls = [trade.pnl for trade in self.trade_records[-20:] if trade.pnl]
        if not recent_pnls:
            return 0.0
        
        cumulative = np.cumsum(recent_pnls)
        peak = np.maximum.accumulate(cumulative)
        drawdowns = (peak - cumulative) / peak * 100
        
        return drawdowns[-1] if len(drawdowns) > 0 else 0.0

    def _predict_drawdown_risk(self) -> float:
        """Predice riesgo de drawdown usando z-score"""
        try:
            pnl_history = [
                trade.pnl for trade in self.trade_records[-30:]
                if trade.pnl is not None
            ]
            
            if len(pnl_history) < 10:
                return 0.0
            
            mean_pnl = np.mean(pnl_history)
            std_pnl = np.std(pnl_history) if np.std(pnl_history) > 0 else 1.0
            
            # Calcular z-score de la secuencia reciente
            recent_pnl = pnl_history[-5:]
            avg_recent = np.mean(recent_pnl)
            
            z_score = abs(avg_recent - mean_pnl) / std_pnl
            return z_score
            
        except Exception as e:
            logger.error(f"❌ Error prediciendo drawdown: {e}")
            return 0.0

    async def _check_risk_limits(self):
        """Verifica límites de riesgo"""
        try:
            # Verificar drawdown máximo
            current_drawdown = self._calculate_current_drawdown()
            if current_drawdown > self.thresholds['max_drawdown']:
                logger.critical(
                    f"🚨 Drawdown máximo excedido: {current_drawdown:.2f}%",
                    extra={"current_drawdown": current_drawdown, "threshold": self.thresholds['max_drawdown']}
                )
                self.prometheus.record_alert("CRITICAL", "risk_management")
            
            # Verificar pérdidas consecutivas
            consecutive_losses = self._get_consecutive_losses()
            if consecutive_losses >= self.thresholds['consecutive_losses']:
                logger.critical(
                    f"🚨 Kill switch activado: {consecutive_losses} pérdidas consecutivas",
                    extra={"consecutive_losses": consecutive_losses}
                )
                self.prometheus.risk_gauges['kill_switch_status'].set(1)
                self.prometheus.record_alert("CRITICAL", "kill_switch")
            
        except Exception as e:
            logger.error(f"❌ Error verificando límites de riesgo: {e}")

    async def _check_kill_switch(self):
        """Verifica condiciones para kill switch"""
        consecutive_losses = self._get_consecutive_losses()
        
        if consecutive_losses >= self.thresholds['consecutive_losses']:
            # Activar kill switch
            self.prometheus.risk_gauges['kill_switch_status'].set(1)
            
            # Notificar a HealthMonitor
            health_monitor = get_health_monitor()
            health_monitor.update_metrics("risk_metrics", {
                "kill_switch_activated": True,
                "consecutive_losses": consecutive_losses
            })

    def _get_consecutive_losses(self) -> int:
        """Obtiene número de pérdidas consecutivas"""
        if not self.trade_records:
            return 0
        
        consecutive = 0
        for trade in reversed(self.trade_records):
            if trade.pnl is None:
                continue
            if trade.pnl < 0:
                consecutive += 1
            else:
                break
        
        return consecutive

    def _get_daily_loss_limit(self) -> float:
        """Obtiene límite de pérdida diaria"""
        # Implementar lógica basada en equity
        return 1000.0  # Ejemplo: $1000

    async def _analyze_performance_trends(self):
        """Analiza tendencias de performance"""
        try:
            # Análisis de tendencia de win rate
            if 'win_rate' in self.metrics_history:
                win_rates = [m.value for m in self.metrics_history['win_rate'][-20:]]
                if len(win_rates) >= 5:
                    trend = self._calculate_trend(win_rates)
                    if trend < -5.0:  # Caída del 5% o más
                        logger.warning(
                            f"📉 Tendencia negativa en win rate: {trend:.2f}%",
                            extra={"win_rate_trend": trend}
                        )
        
        except Exception as e:
            logger.error(f"❌ Error analizando tendencias: {e}")

    async def _detect_performance_anomalies(self):
        """Detecta anomalías en el performance"""
        try:
            # Detectar anomalías en PnL
            if 'daily_pnl' in self.metrics_history:
                pnl_values = [m.value for m in self.metrics_history['daily_pnl'][-30:]]
                if len(pnl_values) >= 10:
                    anomaly = self._detect_anomaly(pnl_values)
                    if anomaly:
                        logger.warning(
                            f"⚠️ Anomalía detectada en PnL: {anomaly}",
                            extra={"pnl_anomaly": anomaly}
                        )
        
        except Exception as e:
            logger.error(f"❌ Error detectando anomalías: {e}")

    def _calculate_trend(self, values: List[float]) -> float:
        """Calcula tendencia de una serie de valores"""
        if len(values) < 2:
            return 0.0
        
        x = np.arange(len(values))
        slope, _ = np.polyfit(x, values, 1)
        
        # Convertir a porcentaje de cambio
        if values[0] != 0:
            trend_percent = (slope * len(values)) / values[0] * 100
        else:
            trend_percent = 0.0
        
        return trend_percent

    def _detect_anomaly(self, values: List[float]) -> Optional[Dict[str, Any]]:
        """Detecta anomalías en una serie de valores"""
        if len(values) < 10:
            return None
        
        mean = np.mean(values)
        std = np.std(values)
        
        last_value = values[-1]
        z_score = abs(last_value - mean) / std if std > 0 else 0
        
        if z_score > self.zscore_thresholds['performance_anomaly']:
            return {
                "z_score": z_score,
                "value": last_value,
                "expected_range": f"{mean - 2*std:.2f} - {mean + 2*std:.2f}",
                "deviation": f"{z_score:.2f}σ"
            }
        
        return None

    def _health_callback(self, system_status: Any, metrics: Any):
        """
        Callback para HealthMonitor - ajusta comportamiento basado en salud del sistema
        """
        if system_status.value == "critical":
            # En modo crítico, aumentar frecuencia de reportes
            logger.warning("🔧 Modo crítico: aumentando monitorización de performance")
        elif system_status.value == "healthy":
            # Comportamiento normal
            pass

    async def _update_health_monitor(self):
        """Actualiza HealthMonitor con métricas de performance"""
        health_monitor = get_health_monitor()
        
        performance_metrics = {
            "win_rate": self._calculate_win_rate(),
            "daily_pnl": self._calculate_daily_pnl(),
            "current_drawdown": self._calculate_current_drawdown(),
            "consecutive_losses": self._get_consecutive_losses(),
            "active_trades": len([t for t in self.trade_records if t.exit_time is None])
        }
        
        health_monitor.update_metrics("performance_tracker", performance_metrics)

    def generate_performance_report(self) -> Dict[str, Any]:
        """Genera reporte completo de performance"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_trades": len(self.trade_records),
                "win_rate": self._calculate_win_rate(),
                "profit_factor": self._calculate_profit_factor(),
                "daily_pnl": self._calculate_daily_pnl(),
                "current_drawdown": self._calculate_current_drawdown(),
                "consecutive_losses": self._get_consecutive_losses(),
                "avg_execution_time": self._calculate_avg_execution_time()
            },
            "current_metrics": {
                name: asdict(metric) for name, metric in self.metrics.items()
            },
            "risk_assessment": {
                "drawdown_risk": self._predict_drawdown_risk(),
                "kill_switch_active": self._get_consecutive_losses() >= self.thresholds['consecutive_losses'],
                "risk_exposure": self._calculate_daily_pnl() / self._get_daily_loss_limit() * 100
            },
            "recent_trades": [
                asdict(trade) for trade in self.trade_records[-10:]
            ]
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del tracker"""
        return {
            "total_trades": len(self.trade_records),
            "active_metrics": len(self.metrics),
            "is_running": self.is_running,
            "performance_report": self.generate_performance_report(),
            "prometheus_port": self.prometheus_port
        }

    # Métodos de base de datos (similares al código anterior pero especializados)
    def _init_database(self):
        """Inicializa base de datos de performance"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Tabla de trades
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    position_size REAL NOT NULL,
                    pnl REAL,
                    pnl_percent REAL,
                    risk_multiplier REAL NOT NULL,
                    signal_confidence REAL NOT NULL,
                    ia_validation_score REAL NOT NULL,
                    execution_quality REAL NOT NULL,
                    phase_durations TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de métricas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    category TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    unit TEXT,
                    threshold_min REAL,
                    threshold_max REAL,
                    status TEXT NOT NULL,
                    confidence REAL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Índices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)")
            
            conn.commit()
            conn.close()
            
            logger.info("🗄️ Base de datos de performance inicializada")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando base de datos: {e}")

    def _save_trade_to_db(self, trade: TradeRecord):
        """Guarda trade en base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO trades 
                (trade_id, symbol, entry_time, exit_time, entry_price, exit_price, 
                 position_size, pnl, pnl_percent, risk_multiplier, signal_confidence, 
                 ia_validation_score, execution_quality, phase_durations, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.trade_id,
                trade.symbol,
                trade.entry_time.isoformat(),
                trade.exit_time.isoformat() if trade.exit_time else None,
                trade.entry_price,
                trade.exit_price,
                trade.position_size,
                trade.pnl,
                trade.pnl_percent,
                trade.risk_multiplier,
                trade.signal_confidence,
                trade.ia_validation_score,
                trade.execution_quality,
                json.dumps({k.value: v for k, v in trade.phase_durations.items()}),
                json.dumps(trade.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error guardando trade en BD: {e}")

    def _save_metric_to_db(self, metric: TradingMetric):
        """Guarda métrica en base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO metrics 
                (name, value, category, timestamp, phase, unit, threshold_min, 
                 threshold_max, status, confidence, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metric.name,
                metric.value,
                metric.category.value,
                metric.timestamp.isoformat(),
                metric.phase.value,
                metric.unit,
                metric.threshold_min,
                metric.threshold_max,
                metric.status,
                metric.confidence,
                json.dumps(metric.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error guardando métrica en BD: {e}")

# Función de fábrica para integración
def create_performance_tracker(config: Dict[str, Any]) -> PerformanceTracker:
    """Crea y configura el tracker de performance"""
    return PerformanceTracker(config)

# Ejemplo de uso
async def main():
    """Función principal de ejemplo"""
    from infrastructure.health_monitor import initialize_health_monitor
    
    config = {
        "performance_tracking": {
            "prometheus_port": 8000
        },
        "risk_config": {
            "max_drawdown": 6.0,
            "daily_loss_limit": 1.0
        }
    }
    
    # Inicializar HealthMonitor
    health_monitor = initialize_health_monitor(config)
    
    # Crear tracker
    tracker = create_performance_tracker(config)
    await tracker.start()
    
    try:
        # Simular algunos trades para demostración
        for i in range(5):
            trade_data = {
                'trade_id': f"demo_trade_{i}",
                'symbol': 'XAUUSD',
                'entry_price': 1800 + i * 10,
                'position_size': 0.1,
                'pnl': 15.0 - i * 5,
                'pnl_percent': 0.1,
                'risk_multiplier': 1.0 + i * 0.1,
                'signal_confidence': 0.8 + i * 0.05,
                'ia_validation_score': 0.85,
                'execution_quality': 0.9,
                'phase_durations': {
                    TradingPhase.ORDER_EXECUTION: 50 + i * 10
                },
                'metadata': {
                    'slippage': 0.5,
                    'spread': 1.2
                }
            }
            
            tracker.record_trade_execution(trade_data)
            await asyncio.sleep(1)
        
        # Esperar y mostrar reporte
        await asyncio.sleep(5)
        report = tracker.generate_performance_report()
        print("📊 Performance Report:")
        print(json.dumps(report, indent=2, default=str))
        
    except KeyboardInterrupt:
        print("⏹️ Interrumpido por usuario")
    finally:
        tracker.stop()

if __name__ == "__main__":
    asyncio.run(main())