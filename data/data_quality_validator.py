#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador de Calidad de Datos - EAS Híbrido 2025
Sistema de validación de calidad de datos de mercado para scalping de alta frecuencia
CORREGIDO según auditoría EAS
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import statistics
from collections import deque

# Intentamos usar el logger estructurado del proyecto; si no existe, fallback simple.
try:
    from infrastructure.structured_logger import get_eas_logger, log_eas_warning, log_eas_error, log_eas_info
except Exception:
    import logging
    logging.basicConfig(level=logging.INFO)
    _fallback_logger = logging.getLogger("DataQualityValidator")

    def get_eas_logger(name: str):
        return _fallback_logger

    def log_eas_warning(event_type: str, data: Dict[str, Any]):
        _fallback_logger.warning(f"{event_type}: {data}")

    def log_eas_error(event_type: str, data: Dict[str, Any]):
        _fallback_logger.error(f"{event_type}: {data}")

    def log_eas_info(event_type: str, data: Dict[str, Any]):
        _fallback_logger.info(f"{event_type}: {data}")

logger = get_eas_logger("DataQualityValidator")


class DataQualityIssue(Enum):
    """Tipos de issues de calidad de datos"""
    MISSING_VALUES = "missing_values"
    OUTLIERS = "outliers"
    STALE_DATA = "stale_data"
    VOLUME_SPIKES = "volume_spikes"
    PRICE_GAPS = "price_gaps"
    INCONSISTENT_SPREAD = "inconsistent_spread"
    FEED_LATENCY = "feed_latency"
    ORDER_BOOK_IMBALANCE = "order_book_imbalance"
    MACRO_RISK_CONTEXT = "macro_risk_context"  # NUEVO: Contexto de riesgo macro


class ValidationSeverity(Enum):
    """Niveles de severidad de validación"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class ValidationRule:
    """Regla de validación de calidad de datos"""
    issue_type: DataQualityIssue
    severity: ValidationSeverity
    threshold: float
    description: str
    timeframe: str = "M15"  # NUEVO: Timeframe específico para contexto
    enabled: bool = True


@dataclass
class ValidationResult:
    """Resultado de una validación de calidad"""
    rule: ValidationRule
    passed: bool
    actual_value: float
    confidence: float
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_type": self.rule.issue_type.value,
            "severity": self.rule.severity.value,
            "passed": self.passed,
            "actual_value": self.actual_value,
            "threshold": self.rule.threshold,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }


@dataclass
class DataQualityScore:
    """Score de calidad de datos consolidado"""
    overall_score: float
    component_scores: Dict[DataQualityIssue, float]
    validation_results: List[ValidationResult]
    timestamp: datetime
    recommendation: str
    critical_failures: List[str] = field(default_factory=list)  # NUEVO: Fallos críticos específicos
    high_severity_failures: List[str] = field(default_factory=list)  # NUEVO: Fallos alta severidad

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "component_scores": {k.value: v for k, v in self.component_scores.items()},
            "failed_validations": len([r for r in self.validation_results if not r.passed]),
            "critical_failures": self.critical_failures,
            "high_severity_failures": self.high_severity_failures,
            "total_validations": len(self.validation_results),
            "timestamp": self.timestamp.isoformat(),
            "recommendation": self.recommendation
        }


class DataQualityValidator:
    """
    Validador de calidad de datos para EAS Híbrido 2025
    Optimizado para scalping de alta frecuencia en XAUUSD
    CORREGIDO según auditoría EAS
    """

    def __init__(self):
        self.validation_rules = self._initialize_validation_rules()
        self.historical_data: Dict[str, Dict[str, deque]] = {}  # symbol -> storage_key -> deque
        self.quality_history: deque = deque(maxlen=1000)  # Últimos 1000 scores
        self.macro_context_cache: Dict[str, Any] = {}  # Cache de contexto macro

        # Configuración para XAUUSD - AJUSTADO según auditoría
        self.symbol_config = {
            "XAUUSD": {
                "typical_spread": 0.15,
                "max_allowed_gap": 1.0,
                "volume_threshold": 1000,
                "latency_threshold_ms": 50,
                "stale_data_threshold": 5.0,  # CRÍTICO: 5 segundos para HFT
                "feed_latency_threshold": 50.0,  # CRÍTICO: 50ms para HFT
                "timeframe": "M15"  # Timeframe principal para scalping
            }
        }

        # Intento de log estructurado si está disponible
        try:
            logger.log_structured("INFO", "DATA_QUALITY_VALIDATOR_INITIALIZED", {
                "validation_rules_count": len(self.validation_rules),
                "supported_symbols": list(self.symbol_config.keys()),
                "hft_optimized": True
            })
        except Exception:
            logger.info(f"DATA_QUALITY_VALIDATOR_INITIALIZED: rules={len(self.validation_rules)}, symbols={list(self.symbol_config.keys())}")

    def _initialize_validation_rules(self) -> List[ValidationRule]:
        """Inicializar reglas de validación para EAS - MEJORADO según auditoría"""
        return [
            # Validaciones de Precios - CRÍTICAS para HFT
            ValidationRule(
                issue_type=DataQualityIssue.STALE_DATA,
                severity=ValidationSeverity.CRITICAL,
                threshold=5.0,  # 5 segundos máximo para HFT
                description="Detección de datos stale para scalping HFT",
                timeframe="TICK"  # Validación a nivel tick
            ),
            ValidationRule(
                issue_type=DataQualityIssue.FEED_LATENCY,
                severity=ValidationSeverity.CRITICAL,
                threshold=50.0,  # 50ms máximo para HFT
                description="Validación de latencia del feed de datos HFT",
                timeframe="TICK"
            ),

            # Validaciones de Alta Severidad
            ValidationRule(
                issue_type=DataQualityIssue.MISSING_VALUES,
                severity=ValidationSeverity.HIGH,
                threshold=0.95,  # Máximo 5% de datos faltantes
                description="Verificar integridad de series de precios",
                timeframe="M15"
            ),
            ValidationRule(
                issue_type=DataQualityIssue.OUTLIERS,
                severity=ValidationSeverity.HIGH,
                threshold=3.0,  # Z-score máximo
                description="Detección de outliers en precios usando Z-score en M15",
                timeframe="M15"
            ),
            ValidationRule(
                issue_type=DataQualityIssue.INCONSISTENT_SPREAD,
                severity=ValidationSeverity.HIGH,
                threshold=0.3,  # Spread máximo en pips
                description="Validación de consistencia del spread",
                timeframe="TICK"
            ),

            # Validaciones de Severidad Media
            ValidationRule(
                issue_type=DataQualityIssue.PRICE_GAPS,
                severity=ValidationSeverity.MEDIUM,
                threshold=1.0,  # Gap máximo en pips
                description="Detección de gaps de precio anormales usando historial interno",
                timeframe="M15"
            ),
            ValidationRule(
                issue_type=DataQualityIssue.VOLUME_SPIKES,
                severity=ValidationSeverity.MEDIUM,
                threshold=2.5,  # Ratio de spike de volumen
                description="Detección de spikes anormales de volumen en M15",
                timeframe="M15"
            ),
            ValidationRule(
                issue_type=DataQualityIssue.ORDER_BOOK_IMBALANCE,
                severity=ValidationSeverity.MEDIUM,
                threshold=0.7,  # Ratio de imbalance máximo
                description="Validación de imbalance del order book L2",
                timeframe="TICK"
            ),

            # NUEVA: Validación de contexto macro
            ValidationRule(
                issue_type=DataQualityIssue.MACRO_RISK_CONTEXT,
                severity=ValidationSeverity.HIGH,
                threshold=0.7,  # Score mínimo de contexto macro
                description="Validación de contexto de riesgo macroeconómico",
                timeframe="CONTEXT"
            )
        ]

    def validate_market_data(self, symbol: str, market_data: Dict[str, Any],
                             macro_context: Optional[Dict[str, Any]] = None) -> DataQualityScore:
        """
        Validar calidad de datos de mercado para un símbolo específico
        MEJORADO: Incluye contexto macro según auditoría
        """
        validation_results = []
        timestamp = datetime.utcnow()

        try:
            # Actualizar datos históricos
            self._update_historical_data(symbol, market_data)

            # Actualizar contexto macro si está disponible
            if macro_context:
                self.macro_context_cache.update(macro_context)

            # Ejecutar todas las validaciones habilitadas
            for rule in self.validation_rules:
                if rule.enabled:
                    result = self._execute_validation(rule, symbol, market_data)
                    validation_results.append(result)

            # Calcular score general
            overall_score, component_scores = self._calculate_quality_score(validation_results)

            # Identificar fallos críticos y de alta severidad
            critical_failures, high_severity_failures = self._identify_critical_failures(validation_results)

            # Generar recomendación
            recommendation = self._generate_recommendation(validation_results, overall_score,
                                                         critical_failures, high_severity_failures)

            # Crear score consolidado
            quality_score = DataQualityScore(
                overall_score=overall_score,
                component_scores=component_scores,
                validation_results=validation_results,
                timestamp=timestamp,
                recommendation=recommendation,
                critical_failures=critical_failures,
                high_severity_failures=high_severity_failures
            )

            # Almacenar en historial
            self.quality_history.append(quality_score)

            # Log del resultado con detalles mejorados
            self._log_validation_result(symbol, quality_score, market_data)

            return quality_score

        except Exception as e:
            log_eas_error("DATA_VALIDATION_ERROR", {
                "symbol": symbol,
                "error": str(e),
                "market_data_keys": list(market_data.keys()) if isinstance(market_data, dict) else [],
                "macro_context_available": macro_context is not None
            })

            # Retornar score mínimo en caso de error
            return DataQualityScore(
                overall_score=0.0,
                component_scores={},
                validation_results=[],
                timestamp=timestamp,
                recommendation="ERROR_EN_VALIDACION",
                critical_failures=["validation_error"],
                high_severity_failures=["system_error"]
            )

    def _execute_validation(self, rule: ValidationRule, symbol: str,
                            market_data: Dict[str, Any]) -> ValidationResult:
        """Ejecutar una validación específica - MEJORADO con manejo de timeframe"""
        try:
            if rule.issue_type == DataQualityIssue.MISSING_VALUES:
                return self._validate_missing_values(rule, symbol, market_data)
            elif rule.issue_type == DataQualityIssue.OUTLIERS:
                return self._validate_outliers(rule, symbol, market_data)
            elif rule.issue_type == DataQualityIssue.STALE_DATA:
                return self._validate_stale_data(rule, symbol, market_data)
            elif rule.issue_type == DataQualityIssue.PRICE_GAPS:
                return self._validate_price_gaps(rule, symbol, market_data)
            elif rule.issue_type == DataQualityIssue.VOLUME_SPIKES:
                return self._validate_volume_spikes(rule, symbol, market_data)
            elif rule.issue_type == DataQualityIssue.INCONSISTENT_SPREAD:
                return self._validate_spread_consistency(rule, symbol, market_data)
            elif rule.issue_type == DataQualityIssue.FEED_LATENCY:
                return self._validate_feed_latency(rule, symbol, market_data)
            elif rule.issue_type == DataQualityIssue.ORDER_BOOK_IMBALANCE:
                return self._validate_order_book_imbalance(rule, symbol, market_data)
            elif rule.issue_type == DataQualityIssue.MACRO_RISK_CONTEXT:
                # El contexto macro se lee desde el caché interno (self.macro_context_cache)
                return self._validate_macro_risk_context(rule, symbol, market_data)
            else:
                # Validación desconocida - considerar como passed
                return ValidationResult(
                    rule=rule,
                    passed=True,
                    actual_value=0.0,
                    confidence=1.0,
                    timestamp=datetime.utcnow(),
                    details={"timeframe": rule.timeframe}
                )

        except Exception as e:
            # En caso de error en validación, considerar como failed
            return ValidationResult(
                rule=rule,
                passed=False,
                actual_value=0.0,
                confidence=0.0,
                timestamp=datetime.utcnow(),
                details={"validation_error": str(e), "timeframe": rule.timeframe}
            )

    def _validate_missing_values(self, rule: ValidationRule, symbol: str,
                                market_data: Dict[str, Any]) -> ValidationResult:
        """Validar datos faltantes en series de precios"""
        required_fields = ['open', 'high', 'low', 'close', 'volume']
        missing_count = sum(1 for field in required_fields if field not in market_data)

        completeness_ratio = 1 - (missing_count / len(required_fields))
        passed = completeness_ratio >= rule.threshold

        return ValidationResult(
            rule=rule,
            passed=passed,
            actual_value=completeness_ratio,
            confidence=0.95,
            timestamp=datetime.utcnow(),
            details={
                "missing_fields": missing_count,
                "total_fields": len(required_fields),
                "completeness_ratio": completeness_ratio,
                "timeframe": rule.timeframe
            }
        )

    def _validate_outliers(self, rule: ValidationRule, symbol: str,
                          market_data: Dict[str, Any]) -> ValidationResult:
        """Validar outliers usando Z-score en precios de cierre - CORREGIDO según auditoría"""
        if 'close' not in market_data:
            return ValidationResult(
                rule=rule,
                passed=False,
                actual_value=0.0,
                confidence=0.0,
                timestamp=datetime.utcnow(),
                details={"error": "Missing close price", "timeframe": rule.timeframe}
            )

        # CORREGIDO: Usar datos históricos del timeframe específico
        close_prices = self._get_historical_values(symbol, 'close', 20, rule.timeframe)
        if len(close_prices) < 5:
            return ValidationResult(
                rule=rule,
                passed=True,  # No hay suficientes datos para validar
                actual_value=0.0,
                confidence=0.5,
                timestamp=datetime.utcnow(),
                details={"warning": "Insufficient historical data", "timeframe": rule.timeframe}
            )

        current_close = market_data['close']
        mean_price = statistics.mean(close_prices)
        std_price = statistics.stdev(close_prices) if len(close_prices) > 1 else 0.1

        if std_price == 0:
            z_score = 0
        else:
            z_score = abs(current_close - mean_price) / std_price

        passed = z_score <= rule.threshold

        return ValidationResult(
            rule=rule,
            passed=passed,
            actual_value=z_score,
            confidence=0.9,
            timestamp=datetime.utcnow(),
            details={
                "current_price": current_close,
                "mean_price": mean_price,
                "std_dev": std_price,
                "z_score": z_score,
                "timeframe": rule.timeframe,
                "sample_size": len(close_prices)
            }
        )

    def _validate_stale_data(self, rule: ValidationRule, symbol: str,
                            market_data: Dict[str, Any]) -> ValidationResult:
        """Validar que los datos no estén stale - CRÍTICO para HFT"""
        current_time = datetime.utcnow()
        data_timestamp = market_data.get('timestamp', current_time)

        if isinstance(data_timestamp, str):
            # Asume formato ISO 8601, maneja la Z de UTC
            try:
                data_timestamp = datetime.fromisoformat(data_timestamp.replace('Z', '+00:00'))
            except Exception:
                data_timestamp = current_time

        time_diff = (current_time - data_timestamp).total_seconds()

        # Uso del umbral del rule, que se inicializó con 5.0s
        passed = time_diff <= rule.threshold

        return ValidationResult(
            rule=rule,
            passed=passed,
            actual_value=time_diff,
            confidence=1.0,
            timestamp=datetime.utcnow(),
            details={
                "data_timestamp": data_timestamp.isoformat(),
                "current_timestamp": current_time.isoformat(),
                "time_diff_seconds": time_diff,
                "timeframe": rule.timeframe,
                "hft_critical": True
            }
        )

    def _validate_price_gaps(self, rule: ValidationRule, symbol: str,
                            market_data: Dict[str, Any]) -> ValidationResult:
        """Validar gaps de precio anormales - CORREGIDO según auditoría"""
        if 'close' not in market_data:
            return ValidationResult(
                rule=rule,
                passed=True,  # No se puede validar
                actual_value=0.0,
                confidence=0.5,
                timestamp=datetime.utcnow(),
                details={"timeframe": rule.timeframe}
            )

        current_close = market_data['close']

        # CORREGIDO: Usar historial interno con timeframe
        historical_closes = self._get_historical_values(symbol, 'close', 1, rule.timeframe)

        if not historical_closes:
            # No hay histórico, no se puede validar
            return ValidationResult(
                rule=rule,
                passed=True,
                actual_value=0.0,
                confidence=0.5,
                timestamp=datetime.utcnow(),
                details={"warning": "No historical data for gap validation", "timeframe": rule.timeframe}
            )

        previous_close = historical_closes[0]
        gap_size = abs(current_close - previous_close)
        passed = gap_size <= rule.threshold

        return ValidationResult(
            rule=rule,
            passed=passed,
            actual_value=gap_size,
            confidence=0.9,
            timestamp=datetime.utcnow(),
            details={
                "current_close": current_close,
                "previous_close": previous_close,
                "gap_size": gap_size,
                "timeframe": rule.timeframe,
                "data_source": "internal_historical"
            }
        )

    def _validate_volume_spikes(self, rule: ValidationRule, symbol: str,
                              market_data: Dict[str, Any]) -> ValidationResult:
        """Validar spikes anormales de volumen"""
        if 'volume' not in market_data:
            return ValidationResult(
                rule=rule,
                passed=True,  # No se puede validar
                actual_value=0.0,
                confidence=0.5,
                timestamp=datetime.utcnow(),
                details={"timeframe": rule.timeframe}
            )

        current_volume = market_data['volume']
        historical_volumes = self._get_historical_values(symbol, 'volume', 10, rule.timeframe)

        if len(historical_volumes) < 5:
            return ValidationResult(
                rule=rule,
                passed=True,  # No hay suficientes datos
                actual_value=0.0,
                confidence=0.5,
                timestamp=datetime.utcnow(),
                details={"timeframe": rule.timeframe}
            )

        mean_volume = statistics.mean(historical_volumes)
        if mean_volume == 0:
            volume_ratio = 1.0
        else:
            volume_ratio = current_volume / mean_volume

        passed = volume_ratio <= rule.threshold

        return ValidationResult(
            rule=rule,
            passed=passed,
            actual_value=volume_ratio,
            confidence=0.8,
            timestamp=datetime.utcnow(),
            details={
                "current_volume": current_volume,
                "mean_volume": mean_volume,
                "volume_ratio": volume_ratio,
                "timeframe": rule.timeframe
            }
        )

    def _validate_spread_consistency(self, rule: ValidationRule, symbol: str,
                                    market_data: Dict[str, Any]) -> ValidationResult:
        """Validar consistencia del spread"""
        if 'spread' not in market_data:
            return ValidationResult(
                rule=rule,
                passed=True,  # No se puede validar
                actual_value=0.0,
                confidence=0.5,
                timestamp=datetime.utcnow(),
                details={"timeframe": rule.timeframe}
            )

        current_spread = market_data['spread']
        symbol_config = self.symbol_config.get(symbol, {})
        typical_spread = symbol_config.get('typical_spread', 0.2)

        # Validar si el spread actual es un múltiplo anormal del spread típico
        spread_ratio = current_spread / typical_spread
        passed = spread_ratio <= rule.threshold

        return ValidationResult(
            rule=rule,
            passed=passed,
            actual_value=current_spread,
            confidence=0.9,
            timestamp=datetime.utcnow(),
            details={
                "current_spread": current_spread,
                "typical_spread": typical_spread,
                "spread_ratio": spread_ratio,
                "timeframe": rule.timeframe
            }
        )

    def _validate_feed_latency(self, rule: ValidationRule, symbol: str,
                              market_data: Dict[str, Any]) -> ValidationResult:
        """Validar latencia del feed de datos - CRÍTICO para HFT"""
        latency = market_data.get('latency_ms', 0)
        passed = latency <= rule.threshold

        return ValidationResult(
            rule=rule,
            passed=passed,
            actual_value=latency,
            confidence=1.0,
            timestamp=datetime.utcnow(),
            details={
                "latency_ms": latency,
                "timeframe": rule.timeframe,
                "hft_critical": True
            }
        )

    def _validate_order_book_imbalance(self, rule: ValidationRule, symbol: str,
                                     market_data: Dict[str, Any]) -> ValidationResult:
        """Validar imbalance del order book L2"""
        order_book = market_data.get('order_book', {})
        bid_volume = order_book.get('total_bid_volume', 0)
        ask_volume = order_book.get('total_ask_volume', 0)

        if bid_volume + ask_volume == 0:
            imbalance_ratio = 0.5
        else:
            imbalance_ratio = abs(bid_volume - ask_volume) / (bid_volume + ask_volume)

        passed = imbalance_ratio <= rule.threshold

        return ValidationResult(
            rule=rule,
            passed=passed,
            actual_value=imbalance_ratio,
            confidence=0.85,
            timestamp=datetime.utcnow(),
            details={
                "bid_volume": bid_volume,
                "ask_volume": ask_volume,
                "imbalance_ratio": imbalance_ratio,
                "timeframe": rule.timeframe
            }
        )

    def _validate_macro_risk_context(self, rule: ValidationRule, symbol: str,
                                     market_data: Dict[str, Any]) -> ValidationResult:
        """NUEVA: Validación de contexto de riesgo macroeconómico"""
        if not self.macro_context_cache:
            return ValidationResult(
                rule=rule,
                passed=True,  # Sin contexto macro, no se puede validar
                actual_value=0.0,
                confidence=0.5,
                timestamp=datetime.utcnow(),
                details={"warning": "No macro context available", "timeframe": rule.timeframe}
            )

        # Calcular score de contexto macro
        macro_score = self._calculate_macro_context_score()
        passed = macro_score >= rule.threshold

        return ValidationResult(
            rule=rule,
            passed=passed,
            actual_value=macro_score,
            confidence=0.8,
            timestamp=datetime.utcnow(),
            details={
                "macro_score": macro_score,
                "vix": self.macro_context_cache.get('vix'),
                "dxy": self.macro_context_cache.get('dxy'),
                "risk_context": self.macro_context_cache.get('risk_context', 'UNKNOWN'),
                "timeframe": rule.timeframe
            }
        )

    def _calculate_macro_context_score(self) -> float:
        """Calcular score de contexto macro basado en múltiples factores"""
        score = 1.0  # Base

        # Factor VIX
        vix = self.macro_context_cache.get('vix')
        if vix:
            if vix > 35:  # Pánico
                score *= 0.4
            elif vix > 25:  # Mercado con miedo
                score *= 0.7

        # Factor DXY
        dxy = self.macro_context_cache.get('dxy')
        if dxy and dxy > 105:  # USD muy fuerte - presión bajista oro
            score *= 0.8

        # Factor riesgo general
        risk_context = self.macro_context_cache.get('risk_context')
        if risk_context == 'HIGH_RISK':
            score *= 0.6
        elif risk_context == 'EXTREME_RISK':
            score *= 0.3

        # El score resultante es un indicador de la calidad del contexto macro para el trading
        # (mayor score = mejor contexto/menor riesgo macro).
        return max(0.0, min(1.0, score))

    def _update_historical_data(self, symbol: str, market_data: Dict[str, Any]):
        """Actualizar datos históricos para el símbolo - MEJORADO con timeframe"""
        if symbol not in self.historical_data:
            self.historical_data[symbol] = {}

        # CORREGIDO: Usar el timeframe del dato si existe, si no, usar M15
        timeframe = market_data.get('timeframe', 'M15')

        for field in ['open', 'high', 'low', 'close', 'volume', 'spread']:
            if field in market_data:
                storage_key = f"{field}_{timeframe}"
                if storage_key not in self.historical_data[symbol]:
                    self.historical_data[symbol][storage_key] = deque(maxlen=100)  # Mantener últimos 100 valores

                self.historical_data[symbol][storage_key].append(market_data[field])

    def _get_historical_values(self, symbol: str, field: str, count: int,
                             timeframe: str = "M15") -> List[float]:
        """Obtener valores históricos para un campo específico y timeframe"""
        storage_key = f"{field}_{timeframe}"
        if (symbol not in self.historical_data or
            storage_key not in self.historical_data[symbol]):
            return []

        values = list(self.historical_data[symbol][storage_key])
        return values[-count:]  # Últimos 'count' valores

    def _calculate_quality_score(self, validation_results: List[ValidationResult]) -> Tuple[float, Dict]:
        """Calcular score de calidad general - MEJORADO con pesos de severidad"""
        if not validation_results:
            return 0.0, {}

        # Pesos basados en severidad - AJUSTADOS según auditoría
        severity_weights = {
            ValidationSeverity.CRITICAL: 4.0,  # Máximo peso para validaciones HFT
            ValidationSeverity.HIGH: 3.0,
            ValidationSeverity.MEDIUM: 2.0,
            ValidationSeverity.LOW: 1.0
        }

        total_weight = 0
        weighted_score = 0.0
        component_scores = {}

        for result in validation_results:
            weight = severity_weights.get(result.rule.severity, 1.0)
            score = 1.0 if result.passed else 0.0

            # Ajustar score por confianza
            adjusted_score = score * result.confidence
            weighted_score += adjusted_score * weight
            total_weight += weight

            # Score por componente
            issue_type = result.rule.issue_type
            if issue_type not in component_scores:
                component_scores[issue_type] = []
            component_scores[issue_type].append(adjusted_score)

        # Calcular score general
        overall_score = weighted_score / total_weight if total_weight > 0 else 0.0

        # Calcular scores por componente
        for issue_type, scores in component_scores.items():
            component_scores[issue_type] = statistics.mean(scores) if scores else 0.0

        return overall_score, component_scores

    def _identify_critical_failures(self, validation_results: List[ValidationResult]) -> Tuple[List[str], List[str]]:
        """Identificar fallos críticos y de alta severidad - NUEVO según auditoría"""
        critical_failures = []
        high_severity_failures = []

        for result in validation_results:
            if not result.passed:
                failure_detail = f"{result.rule.issue_type.value} ({result.actual_value:.2f}/{result.rule.threshold})"
                if result.rule.severity == ValidationSeverity.CRITICAL:
                    critical_failures.append(failure_detail)
                elif result.rule.severity == ValidationSeverity.HIGH:
                    high_severity_failures.append(failure_detail)

        return critical_failures, high_severity_failures

    def _generate_recommendation(self, validation_results: List[ValidationResult],
                               overall_score: float,
                               critical_failures: List[str],
                               high_severity_failures: List[str]) -> str:
        """Generar recomendación basada en los resultados de validación - MEJORADO"""

        if critical_failures:
            failures_str = ", ".join(critical_failures)
            return f"CALIDAD_CRITICA: No operar - Fallos críticos: {failures_str}"

        if high_severity_failures:
            failures_str = ", ".join(high_severity_failures)
            return f"CALIDAD_BAJA: Operar con precaución - Fallos altos: {failures_str}"

        if overall_score >= 0.9:
            return "CALIDAD_EXCELENTE: Datos óptimos para trading HFT"
        elif overall_score >= 0.7:
            return "CALIDAD_ACEPTABLE: Datos adecuados para operar"
        else:
            return "CALIDAD_REGULAR: Considerar verificar fuentes de datos"

    def _log_validation_result(self, symbol: str, quality_score: DataQualityScore,
                              market_data: Dict[str, Any]):
        """Log del resultado de validación - MEJORADO según auditoría"""
        log_data = quality_score.to_dict()
        log_data["symbol"] = symbol
        log_data["data_timestamp"] = market_data.get('timestamp', 'unknown')
        log_data["spread"] = market_data.get('spread', 0)
        log_data["latency_ms"] = market_data.get('latency_ms', 0)

        # CORREGIDO: Logging detallado con fallos específicos
        if quality_score.critical_failures:
            log_eas_error("DATA_QUALITY_CRITICAL_FAILURE", log_data)
        elif quality_score.high_severity_failures or quality_score.overall_score < 0.7:
            log_eas_warning("DATA_QUALITY_HIGH_FAILURE", log_data)
        else:
            log_eas_info("DATA_QUALITY_INFO", log_data)

    def get_quality_trend(self, symbol: str, hours: int = 24) -> List[DataQualityScore]:
        """Obtener tendencia de calidad de datos"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            score for score in self.quality_history
            if score.timestamp >= cutoff_time
        ]

    def should_trade_based_on_quality(self, symbol: str,
                                     minimum_score: float = 0.7) -> Tuple[bool, str]:
        """
        Determina si se debe operar basado en la calidad de datos (usa el último score almacenado)

        Returns:
            Tuple[bool, str]: (puede operar, razonamiento)
        """
        recent_scores = self.get_quality_trend(symbol, 1)  # Última hora
        if not recent_scores:
            return False, "No hay datos de calidad recientes"

        latest_score = recent_scores[-1]

        # 1. Chequeo CRÍTICO (Latencia/Stale Data)
        if latest_score.critical_failures:
            return False, latest_score.recommendation

        # 2. Chequeo de Score Mínimo
        if latest_score.overall_score < minimum_score:
            return False, f"Calidad de datos insuficiente: {latest_score.overall_score:.2f}. " + latest_score.recommendation

        # 3. Chequeo de Alta Severidad (Macro/Outliers/Spread)
        if latest_score.high_severity_failures:
            return True, "Operar con riesgo: Fallos de Alta Severidad. " + latest_score.recommendation

        return True, latest_score.recommendation


# Instancia global del validador
global_validator: Optional[DataQualityValidator] = None


def get_data_validator() -> DataQualityValidator:
    """Obtener instancia global del validador de datos"""
    global global_validator
    if global_validator is None:
        global_validator = DataQualityValidator()
    return global_validator


def validate_market_data_and_get_score(symbol: str, market_data: Dict[str, Any],
                                      macro_context: Optional[Dict[str, Any]] = None) -> DataQualityScore:
    """Función de conveniencia para validar datos de mercado"""
    validator = get_data_validator()
    return validator.validate_market_data(symbol, market_data, macro_context)


def can_trade_with_data(symbol: str) -> Tuple[bool, str]:
    """Función de conveniencia para verificar si se puede operar (usa el último score)"""
    validator = get_data_validator()
    return validator.should_trade_based_on_quality(symbol)


# Ejemplo de uso
def example_usage():
    """Ejemplo de uso del validador de calidad de datos"""
    validator = get_data_validator()

    # Datos de mercado de ejemplo para XAUUSD (M15)
    sample_market_data_m15 = {
        'open': 1950.25,
        'high': 1951.50,
        'low': 1949.80,
        'close': 1949.80,
        'volume': 1250,
        'spread': 0.12,
        'timestamp': datetime.utcnow().isoformat(),
        'latency_ms': 15,
        'order_book': {
            'total_bid_volume': 50000,
            'total_ask_volume': 45000
        },
        'timeframe': 'M15'
    }

    # Contexto macro de ejemplo
    sample_macro_context = {
        'vix': 22.5,
        'dxy': 104.1,
        'risk_context': 'NORMAL'
    }

    # 1. Validar calidad de datos (Actualiza el histórico)
    quality_score = validator.validate_market_data("XAUUSD", sample_market_data_m15, sample_macro_context)

    print(f"Score de Calidad: {quality_score.overall_score:.2f}")
    print(f"Recomendación: {quality_score.recommendation}")

    # 2. Verificar si se puede operar
    can_trade, reason = can_trade_with_data("XAUUSD")
    print(f"¿Puede operar? {can_trade}")
    print(f"Razón: {reason}")

    # Ejemplo de fallo CRÍTICO (Stale Data)
    critical_data = sample_market_data_m15.copy()
    critical_data['timestamp'] = (datetime.utcnow() - timedelta(seconds=6.0)).isoformat()
    critical_score = validator.validate_market_data("XAUUSD", critical_data)

    can_trade_critical, reason_critical = can_trade_with_data("XAUUSD")
    print("\n--- Test Fallo Crítico ---")
    print(f"Score: {critical_score.overall_score:.2f}")
    print(f"Fallos Críticos: {critical_score.critical_failures}")
    print(f"¿Puede operar (CRÍTICO)? {can_trade_critical}")
    print(f"Razón (CRÍTICO): {reason_critical}")


if __name__ == "__main__":
    example_usage()
