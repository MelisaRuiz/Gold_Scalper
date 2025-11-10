#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HECTA GOLD Macro Analysis Agent v3.1 - EAS Híbrido 2025 Integration
Agente especializado con análisis de régimen, integración HealthMonitor y arquitectura de agentes
CORREGIDO Y FUNCIONAL
"""

import asyncio
import logging
import aiohttp
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
import websockets
import numpy as np
from enum import Enum
import threading

# ===== IMPLEMENTACIÓN MÍNIMA DE LOGGER ESTRUCTURADO =====
try:
    from infrastructure.structured_logger import StructuredLogger
except ImportError:
    # Fallback a logger estándar
    logging.basicConfig(level=logging.INFO)
    _fallback_logger = logging.getLogger("MacroAnalysisAgent")
    
    class StructuredLogger:
        def __init__(self, name: str):
            self.logger = _fallback_logger
        
        def info(self, msg: str, extra: Dict = None):
            self.logger.info(msg, extra=extra or {})
        
        def warning(self, msg: str, extra: Dict = None):
            self.logger.warning(msg, extra=extra or {})
        
        def error(self, msg: str, extra: Dict = None):
            self.logger.error(msg, extra=extra or {})

logger = StructuredLogger("HECTAGold.MacroAnalysisAgent")

# ===== IMPLEMENTACIONES OPCIONALES =====
try:
    from infrastructure.health_monitor import get_health_monitor
except ImportError:
    class HealthMonitorStub:
        def register_health_callback(self, callback):
            pass
        
        async def update_agent_metrics(self, agent: str, data: Dict):
            pass
    
    def get_health_monitor():
        return HealthMonitorStub()

try:
    from infrastructure.circuit_breaker import CircuitBreaker
except ImportError:
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

        def is_open(self) -> bool:
            return self.failures < self.max_failures

        def get_state(self) -> str:
            return "CLOSED" if self.is_open() else "OPEN"

try:
    from infrastructure.guardrails import with_guardrails
except ImportError:
    def with_guardrails(agent_context: str):
        def decorator(func):
            return func
        return decorator

class MarketRegime(Enum):
    """Régimenes de mercado según EAS Híbrido 2025"""
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF" 
    NEUTRAL = "NEUTRAL"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"

class InflationRegime(Enum):
    """Régimenes de inflación"""
    INFLATION_HEDGE = "inflation_hedge"
    DEFLATION = "deflation"
    HIGH_INFLATION = "high_inflation"
    GOLDILOCKS = "goldilocks"
    STAGFLATION = "stagflation"

class GoldBias(Enum):
    """Sesgo direccional del oro"""
    STRONGLY_BULLISH = "STRONGLY_BULLISH"
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"
    STRONGLY_BEARISH = "STRONGLY_BEARISH"

@dataclass
class EnhancedMacroBias:
    """Estructura mejorada de bias macro para EAS Híbrido 2025"""
    # Datos crudos
    vix: float
    dxy: float
    real_yields: float
    inflation_expectations: float
    gold_etf_flows: float
    # Métricas calculadas
    bias_score: int  # 1-10 scale
    kill_switch: bool
    confidence: float
    regime: InflationRegime
    market_regime: MarketRegime
    gold_bias: GoldBias
    risk_multiplier: float
    # Metadata
    timestamp: datetime
    data_sources: List[str]
    data_quality: float
    signal_strength: float
    regime_confidence: float
    # Análisis adicional
    technical_factors: Dict[str, float]
    fundamental_factors: Dict[str, float]
    sentiment_factors: Dict[str, float]

class MacroAnalysisAgent:
    """
    Agente de análisis macroeconómico para EAS Híbrido 2025
    Integrado con HealthMonitor, circuit breakers y guardrails
    CORREGIDO Y FUNCIONAL
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.agent_config = config.get('macro_agent', {})
        self.api_keys = config.get('api_keys', {})
        # Umbrales EAS Híbrido 2025
        self.thresholds = {
            'vix_spike': 25.0,
            'vix_extreme': 35.0,
            'dxy_strong': 105.0,
            'dxy_weak': 95.0,
            'yields_high': 2.0,
            'yields_low': 0.0,
            'inflation_high': 3.0,
            'min_confidence': 0.7
        }
        # Configuración de fuentes
        self.data_sources = {
            'vix': ['alphavantage', 'fred', 'polygon'],
            'dxy': ['fred', 'polygon', 'finnhub'],
            'yields': ['fred', 'treasury'],
            'inflation': ['fred', 'bls'],
            'etf_flows': ['bloomberg', 'reuters']
        }
        # Circuit breaker para APIs
        self.circuit_breaker = CircuitBreaker(
            max_failures=3,
            reset_timeout=300
        )
        # Estado del agente
        self.session = None
        self.ws_task = None
        self.cache = {}
        self.cache_duration = 300  # 5 minutos
        self.last_analysis = None
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'api_errors': 0,
            'cache_hits': 0,
            'avg_response_time': 0.0,
            'total_analysis_time': 0.0
        }
        # Histórico para análisis de tendencias
        self.historical_data = {
            'vix': [],
            'dxy': [],
            'yields': [],
            'bias_scores': []
        }
        self.max_history_size = 100
        self._lock = threading.RLock()
        logger.info("🎯 Macro Analysis Agent EAS Híbrido 2025 inicializado")

    async def initialize(self):
        """Inicialización del agente con integración HealthMonitor"""
        try:
            # Configurar sesión HTTP optimizada
            connector = aiohttp.TCPConnector(
                limit=15,
                ttl_dns_cache=300,
                force_close=True
            )
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'HECTA-Gold-Scalper-EAS-2025/8.7',
                    'Accept': 'application/json'
                }
            )
            # Iniciar WebSocket si está configurado
            if self.agent_config.get('websocket_enabled', False):
                self.ws_task = asyncio.create_task(self._fred_ws_listener())
            # Registrar callback en HealthMonitor
            health_monitor = get_health_monitor()
            health_monitor.register_health_callback(self._health_callback)
            logger.info("🚀 Macro Analysis Agent inicializado con integración HealthMonitor")
        except Exception as e:
            logger.error(f"❌ Error inicializando Macro Analysis Agent: {e}")
            raise

    @with_guardrails(agent_context="macro_analysis")
    async def analyze_market_conditions(self) -> EnhancedMacroBias:
        """
        Análisis principal de condiciones macroeconómicas
        Devuelve bias estructurado para el sistema EAS
        """
        start_time = datetime.now()
        self.metrics['total_requests'] += 1
        try:
            # Verificar circuit breaker
            if not self.circuit_breaker.allow_request():
                logger.warning("🔒 Circuit breaker activado - usando análisis cacheado")
                return self._get_cached_analysis()
            # Verificar cache primero
            cached_result = self._get_cached_analysis()
            if cached_result:
                self.metrics['cache_hits'] += 1
                return cached_result
            # Recolectar datos en paralelo
            data_tasks = [
                self._fetch_vix_data(),
                self._fetch_dxy_data(),
                self._fetch_real_yields(),
                self._fetch_inflation_expectations(),
                self._fetch_gold_etf_flows()
            ]
            results = await asyncio.gather(*data_tasks, return_exceptions=True)
            # Procesar resultados con manejo de errores individual
            processed_data = self._process_data_results(results)
            # Realizar análisis macro
            analysis = await self._perform_macro_analysis(processed_data)
            # Actualizar cache e histórico
            self._update_cache("macro_bias", analysis)
            self._update_historical_data(processed_data, analysis)
            with self._lock:
                self.last_analysis = analysis
            # Registrar éxito
            self.circuit_breaker.record_success()
            self.metrics['successful_requests'] += 1
            # Actualizar métricas de performance
            analysis_time = (datetime.now() - start_time).total_seconds()
            self.metrics['total_analysis_time'] += analysis_time
            self.metrics['avg_response_time'] = (
                self.metrics['total_analysis_time'] / self.metrics['successful_requests']
            )
            # Enviar métricas a HealthMonitor
            await self._update_health_metrics(analysis)
            logger.info(
                f"📊 Macro Analysis Completo - Score: {analysis.bias_score}/10 | "
                f"Regime: {analysis.regime.value} | "
                f"Gold Bias: {analysis.gold_bias.value} | "
                f"Risk Multiplier: {analysis.risk_multiplier:.2f}",
                extra=asdict(analysis)
            )
            return analysis
        except Exception as e:
            # Registrar fallo
            self.circuit_breaker.record_failure()
            self.metrics['api_errors'] += 1
            logger.error(f"❌ Error en análisis macro: {e}")
            # Usar análisis cacheado como fallback
            return self._get_fallback_analysis()

    async def _perform_macro_analysis(self, data: Dict[str, Any]) -> EnhancedMacroBias:
        """Realiza análisis macroeconómico completo"""
        vix = data.get('vix', 20.0)
        dxy = data.get('dxy', 102.0)
        yields = data.get('yields', 1.2)
        inflation = data.get('inflation', 2.0)
        etf_flows = data.get('etf_flows', 0.0)
        # Calcular métricas principales
        bias_score = self._calculate_enhanced_bias_score(vix, dxy, yields, inflation, etf_flows)
        kill_switch = self._calculate_kill_switch(vix, dxy, yields, inflation)
        confidence = self._calculate_analysis_confidence(data)
        regime = self._determine_inflation_regime(yields, inflation, vix)
        market_regime = self._determine_market_regime(bias_score, vix, yields)
        gold_bias = self._determine_gold_bias(vix, dxy, yields, inflation, etf_flows)
        risk_multiplier = self._calculate_risk_multiplier(bias_score, confidence, kill_switch)
        # Factores técnicos y fundamentales
        technical_factors = self._calculate_technical_factors(data)
        fundamental_factors = self._calculate_fundamental_factors(data)
        sentiment_factors = self._calculate_sentiment_factors(data)
        # Calcular calidad de datos y fuerza de señal
        data_quality = self._calculate_data_quality(data)
        signal_strength = self._calculate_signal_strength(bias_score, confidence)
        regime_confidence = self._calculate_regime_confidence(regime, data)
        return EnhancedMacroBias(
            vix=vix,
            dxy=dxy,
            real_yields=yields,
            inflation_expectations=inflation,
            gold_etf_flows=etf_flows,
            bias_score=bias_score,
            kill_switch=kill_switch,
            confidence=confidence,
            regime=regime,
            market_regime=market_regime,
            gold_bias=gold_bias,
            risk_multiplier=risk_multiplier,
            timestamp=datetime.now(),
            data_sources=list(data.keys()),
            data_quality=data_quality,
            signal_strength=signal_strength,
            regime_confidence=regime_confidence,
            technical_factors=technical_factors,
            fundamental_factors=fundamental_factors,
            sentiment_factors=sentiment_factors
        )

    def _calculate_enhanced_bias_score(self, vix: float, dxy: float, yields: float, 
                                     inflation: float, etf_flows: float) -> int:
        """Calcula score de bias mejorado con múltiples factores"""
        score = 5  # Neutral
        # Factor VIX (40% peso)
        vix_weight = 0.4
        if vix < 15: 
            vix_score = 8   # Mercado complaciente - buen entorno
        elif vix < 20: 
            vix_score = 6   # Normal
        elif vix < 25: 
            vix_score = 4   # Preocupación creciente
        elif vix < 30:
            vix_score = 2   # Miedo - condiciones difíciles
        else: 
            vix_score = 0   # Pánico - evitar trading
        # Factor DXY (25% peso)
        dxy_weight = 0.25
        if dxy < 95: 
            dxy_score = 9   # USD muy débil - muy alcista oro
        elif dxy < 100: 
            dxy_score = 7   # USD débil - alcista
        elif dxy < 105: 
            dxy_score = 5   # USD neutral
        elif dxy < 110: 
            dxy_score = 3   # USD fuerte
        else: 
            dxy_score = 1   # USD muy fuerte - muy bajista
        # Factor rendimientos reales (20% peso)
        yields_weight = 0.2
        if yields < 0: 
            yields_score = 10  # Rendimientos negativos - ideal para oro
        elif yields < 1.0: 
            yields_score = 8   # Bajos - muy favorable
        elif yields < 2.0: 
            yields_score = 6   # Moderados - favorable
        elif yields < 3.0: 
            yields_score = 4   # Altos - presión bajista
        else: 
            yields_score = 2   # Muy altos - muy bajista
        # Factor inflación (10% peso)
        inflation_weight = 0.1
        if inflation > 3.0: 
            inflation_score = 9   # Alta inflación - hedge ideal
        elif inflation > 2.0: 
            inflation_score = 7   # Inflación moderada - favorable
        elif inflation > 1.0: 
            inflation_score = 5   # Inflación controlada - neutral
        else: 
            inflation_score = 3   # Baja inflación - menos favorable
        # Factor ETF flows (5% peso)
        etf_weight = 0.05
        if etf_flows > 100: 
            etf_score = 9    # Fuertes entradas - muy alcista
        elif etf_flows > 50: 
            etf_score = 7    # Entradas moderadas - alcista
        elif etf_flows > -50: 
            etf_score = 5    # Flujos neutros - neutral
        elif etf_flows > -100: 
            etf_score = 3    # Salidas moderadas - bajista
        else: 
            etf_score = 1    # Fuertes salidas - muy bajista
        # Calcular score ponderado
        weighted_score = (
            vix_score * vix_weight +
            dxy_score * dxy_weight +
            yields_score * yields_weight +
            inflation_score * inflation_weight +
            etf_score * etf_weight
        )
        # Normalizar a escala 1-10
        final_score = int(round(weighted_score))
        return max(1, min(10, final_score))

    def _calculate_kill_switch(self, vix: float, dxy: float, yields: float, inflation: float) -> bool:
        """Determina condiciones extremas para kill switch"""
        extreme_conditions = [
            vix > self.thresholds['vix_extreme'],      # Pánico de mercado
            vix < 10,                                  # Complacencia extrema
            dxy > 110,                                 # USD extremadamente fuerte
            dxy < 90,                                  # USD extremadamente débil
            yields > 4.0,                              # Rendimientos muy altos
            inflation > 5.0,                           # Hiperinflación
            inflation < -1.0                           # Deflación severa
        ]
        return any(extreme_conditions)

    def _calculate_analysis_confidence(self, data: Dict[str, Any]) -> float:
        """Calcula confianza del análisis basado en calidad y consistencia de datos"""
        confidence = 0.7  # Base
        # Factor: Número de fuentes exitosas
        successful_sources = len([v for v in data.values() if v is not None])
        total_sources = len(data)
        source_ratio = successful_sources / total_sources if total_sources > 0 else 0
        confidence += source_ratio * 0.2
        # Factor: Consistencia entre fuentes
        consistency_score = self._calculate_data_consistency(data)
        confidence += consistency_score * 0.1
        return min(0.95, confidence)

    def _calculate_data_consistency(self, data: Dict[str, Any]) -> float:
        """Calcula consistencia entre diferentes fuentes de datos"""
        # Verificar si los datos están en rangos consistentes
        consistency_checks = []
        vix = data.get('vix')
        dxy = data.get('dxy')
        yields = data.get('yields')
        if vix and dxy:
            # VIX alto generalmente correlaciona con DXY bajo (oro como refugio)
            if vix > 25 and dxy < 100:
                consistency_checks.append(True)
            elif vix < 15 and dxy > 105:
                consistency_checks.append(True)
            else:
                consistency_checks.append(False)
        if yields and vix:
            # Rendimientos altos pueden correlacionar con VIX bajo (entorno risk-on)
            if yields > 2.5 and vix < 20:
                consistency_checks.append(True)
            elif yields < 0.5 and vix > 25:
                consistency_checks.append(True)
            else:
                consistency_checks.append(False)
        if consistency_checks:
            return sum(consistency_checks) / len(consistency_checks)
        return 0.8  # Valor por defecto si no hay suficientes datos

    def _determine_inflation_regime(self, yields: float, inflation: float, vix: float) -> InflationRegime:
        """Determina régimen de inflación actual"""
        if yields > 2.0 and inflation > 3.0:
            return InflationRegime.HIGH_INFLATION
        elif yields < 0 and inflation < 1.0:
            return InflationRegime.DEFLATION
        elif yields < 1.0 and inflation > 2.0:
            return InflationRegime.INFLATION_HEDGE
        elif vix > 25 and inflation > 2.0:
            return InflationRegime.STAGFLATION
        else:
            return InflationRegime.GOLDILOCKS

    def _determine_market_regime(self, bias_score: int, vix: float, yields: float) -> MarketRegime:
        """Determina régimen de mercado actual"""
        if vix > 25:
            return MarketRegime.HIGH_VOLATILITY
        elif vix < 15:
            return MarketRegime.LOW_VOLATILITY
        elif bias_score >= 7 and yields < 2.0:
            return MarketRegime.RISK_ON
        elif bias_score <= 4 or yields > 2.5:
            return MarketRegime.RISK_OFF
        else:
            return MarketRegime.NEUTRAL

    def _determine_gold_bias(self, vix: float, dxy: float, yields: float, 
                           inflation: float, etf_flows: float) -> GoldBias:
        """Determina bias direccional para oro con múltiples factores"""
        bullish_signals = 0
        bearish_signals = 0
        # Señales alcistas
        if vix > 20: bullish_signals += 1           # Miedo = oro como refugio
        if dxy < 100: bullish_signals += 1          # USD débil = oro fuerte
        if yields < 1.0: bullish_signals += 1       # Rendimientos bajos = oro atractivo
        if inflation > 2.5: bullish_signals += 1    # Inflación = hedge
        if etf_flows > 50: bullish_signals += 1     # Entradas ETF = interés institucional
        # Señales bajistas  
        if vix < 15: bearish_signals += 1           # Avaricia = menos interés en oro
        if dxy > 105: bearish_signals += 1          # USD fuerte = presión oro
        if yields > 2.0: bearish_signals += 1       # Rendimientos altos = menos atractivo
        if inflation < 1.5: bearish_signals += 1    # Baja inflación = menos necesidad de hedge
        if etf_flows < -50: bearish_signals += 1    # Salidas ETF = desinterés institucional
        net_signals = bullish_signals - bearish_signals
        if net_signals >= 3:
            return GoldBias.STRONGLY_BULLISH
        elif net_signals >= 1:
            return GoldBias.BULLISH
        elif net_signals <= -3:
            return GoldBias.STRONGLY_BEARISH
        elif net_signals <= -1:
            return GoldBias.BEARISH
        else:
            return GoldBias.NEUTRAL

    def _calculate_risk_multiplier(self, score: int, confidence: float, kill_switch: bool) -> float:
        """Calcula multiplicador de riesgo dinámico para EAS"""
        if kill_switch:
            return 0.0  # No trading en condiciones extremas
        # Base multiplier del score (1-10 scale to 0.1-1.0)
        base_multiplier = score / 10.0
        # Ajustar por confianza
        confidence_adjusted = base_multiplier * confidence
        # Aplicar límites EAS (0.1 - 1.5)
        final_multiplier = max(0.1, min(1.5, confidence_adjusted))
        # Redondear a 2 decimales para precisión
        return round(final_multiplier, 2)

    def _calculate_technical_factors(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Calcula factores técnicos para el análisis"""
        return {
            "vix_trend": self._calculate_trend(self.historical_data.get('vix', [])),
            "dxy_momentum": self._calculate_momentum(data.get('dxy', 0)),
            "yields_volatility": self._calculate_volatility(self.historical_data.get('yields', [])),
            "market_stress": data.get('vix', 0) / 20.0  # Normalizado
        }

    def _calculate_fundamental_factors(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Calcula factores fundamentales para el análisis"""
        return {
            "real_rates_attractiveness": max(0, 2.0 - data.get('yields', 0)) / 2.0,
            "inflation_hedge_demand": min(1.0, data.get('inflation', 0) / 3.0),
            "dollar_strength_impact": max(0, 105.0 - data.get('dxy', 0)) / 15.0,
            "safe_haven_demand": min(1.0, data.get('vix', 0) / 30.0)
        }

    def _calculate_sentiment_factors(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Calcula factores de sentimiento para el análisis"""
        return {
            "etf_sentiment": data.get('etf_flows', 0) / 100.0,
            "fear_greed_index": min(1.0, data.get('vix', 0) / 40.0),
            "institutional_demand": abs(data.get('etf_flows', 0)) / 200.0,
            "market_stability": max(0, 25.0 - data.get('vix', 0)) / 25.0
        }

    def _calculate_data_quality(self, data: Dict[str, Any]) -> float:
        """Calcula calidad general de los datos"""
        quality_factors = []
        for key, value in data.items():
            if value is not None:
                # Verificar si el valor está dentro de rangos razonables
                if self._is_value_reasonable(key, value):
                    quality_factors.append(1.0)
                else:
                    quality_factors.append(0.5)
            else:
                quality_factors.append(0.0)
        return sum(quality_factors) / len(quality_factors) if quality_factors else 0.0

    def _calculate_signal_strength(self, bias_score: int, confidence: float) -> float:
        """Calcula fuerza de la señal macro"""
        # Normalizar score a 0-1
        normalized_score = (bias_score - 1) / 9.0
        return normalized_score * confidence

    def _calculate_regime_confidence(self, regime: InflationRegime, data: Dict[str, Any]) -> float:
        """Calcula confianza en la clasificación del régimen"""
        # Basado en qué tan claramente se ajusta a las condiciones del régimen
        base_confidence = 0.7
        # Ajustar según consistencia de señales
        consistent_signals = self._count_consistent_signals(regime, data)
        total_signals = 5  # Número total de señales verificadas
        regime_confidence = base_confidence + (consistent_signals / total_signals) * 0.3
        return min(0.95, regime_confidence)

    def _count_consistent_signals(self, regime: InflationRegime, data: Dict[str, Any]) -> int:
        """Cuenta señales consistentes con el régimen identificado"""
        consistent_count = 0
        vix = data.get('vix', 20.0)
        dxy = data.get('dxy', 102.0)
        yields = data.get('yields', 1.2)
        inflation = data.get('inflation', 2.0)
        etf_flows = data.get('etf_flows', 0.0)
        if regime == InflationRegime.HIGH_INFLATION:
            if yields > 2.0: consistent_count += 1
            if inflation > 3.0: consistent_count += 1
            if vix > 20: consistent_count += 1
            if dxy < 100: consistent_count += 1  # USD débil en alta inflación
        elif regime == InflationRegime.DEFLATION:
            if yields < 0: consistent_count += 1
            if inflation < 1.0: consistent_count += 1
            if vix > 25: consistent_count += 1
            if dxy > 105: consistent_count += 1  # USD fuerte en deflación
        elif regime == InflationRegime.INFLATION_HEDGE:
            if yields < 1.0: consistent_count += 1
            if inflation > 2.0: consistent_count += 1
            if etf_flows > 0: consistent_count += 1
        elif regime == InflationRegime.STAGFLATION:
            if vix > 25: consistent_count += 1
            if inflation > 2.0: consistent_count += 1
            if yields > 1.5: consistent_count += 1
        elif regime == InflationRegime.GOLDILOCKS:
            if 15 <= vix <= 25: consistent_count += 1
            if 1.0 <= inflation <= 2.5: consistent_count += 1
            if 0.5 <= yields <= 2.0: consistent_count += 1
        return consistent_count

    def _calculate_trend(self, data: List[float]) -> float:
        """Calcula tendencia de una serie de datos"""
        if len(data) < 2:
            return 0.0
        try:
            x = np.arange(len(data))
            slope, _ = np.polyfit(x, data, 1)
            # Normalizar a -1 a 1
            if len(data) > 0 and max(data) != min(data):
                normalized_slope = slope / (max(data) - min(data))
                return max(-1, min(1, normalized_slope))
        except Exception as e:
            logger.debug(f"Error calculando tendencia: {e}")
        return 0.0

    def _calculate_momentum(self, current_value: float) -> float:
        """Calcula momentum basado en datos históricos"""
        if len(self.historical_data.get('dxy', [])) < 5:
            return 0.0
        recent_values = self.historical_data['dxy'][-5:]
        if len(recent_values) < 2:
            return 0.0
        try:
            momentum = (current_value - recent_values[0]) / recent_values[0] if recent_values[0] != 0 else 0
            return max(-0.1, min(0.1, momentum))  # Limitar a ±10%
        except Exception as e:
            logger.debug(f"Error calculando momentum: {e}")
            return 0.0

    def _calculate_volatility(self, data: List[float]) -> float:
        """Calcula volatilidad de una serie de datos"""
        if len(data) < 5:
            return 0.0
        try:
            returns = np.diff(data) / data[:-1]
            volatility = np.std(returns) if len(returns) > 0 else 0
            return float(volatility)
        except Exception as e:
            logger.debug(f"Error calculando volatilidad: {e}")
            return 0.0

    def _is_value_reasonable(self, metric: str, value: float) -> bool:
        """Verifica si un valor está dentro de rangos razonables"""
        reasonable_ranges = {
            'vix': (5, 80),
            'dxy': (80, 120),
            'yields': (-2, 10),
            'inflation': (-2, 15),
            'etf_flows': (-500, 500)
        }
        if metric in reasonable_ranges:
            min_val, max_val = reasonable_ranges[metric]
            return min_val <= value <= max_val
        return True

    # === IMPLEMENTACIONES MEJORADAS DE OBTENCIÓN DE DATOS ===
    async def _fetch_vix_data(self) -> float:
        """Obtiene datos del VIX desde múltiples fuentes"""
        sources = [
            self._fetch_vix_alphavantage(),
            self._fetch_vix_fred(),
            self._fetch_vix_polygon()
        ]
        results = await asyncio.gather(*sources, return_exceptions=True)
        valid_results = [r for r in results if not isinstance(r, Exception) and r is not None]
        if valid_results:
            return float(np.median(valid_results))
        else:
            logger.warning("⚠️ Todas las fuentes de VIX fallaron - usando valor por defecto")
            return 20.0

    async def _fetch_dxy_data(self) -> float:
        """Obtiene datos del DXY desde múltiples fuentes"""
        sources = [
            self._fetch_dxy_fred(),
            self._fetch_dxy_polygon(),
            self._fetch_dxy_finnhub()
        ]
        results = await asyncio.gather(*sources, return_exceptions=True)
        valid_results = [r for r in results if not isinstance(r, Exception) and r is not None]
        if valid_results:
            return float(np.median(valid_results))
        else:
            logger.warning("⚠️ Todas las fuentes de DXY fallaron - usando valor por defecto")
            return 102.0

    async def _fetch_real_yields(self) -> float:
        """Obtiene rendimientos reales desde FRED"""
        try:
            api_key = self.api_keys.get('fred')
            if not api_key:
                logger.warning("⚠️ API key FRED no configurada")
                return 1.2
            # Tasa nominal 10 años menos expectativas de inflación
            nominal_yield_url = f"https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key={api_key}&file_type=json&limit=1&sort_order=desc"
            inflation_exp_url = f"https://api.stlouisfed.org/fred/series/observations?series_id=T10YIE&api_key={api_key}&file_type=json&limit=1&sort_order=desc"
            async with self.session.get(nominal_yield_url, timeout=8) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('observations'):
                        nominal_yield = float(data['observations'][0]['value'])
                else:
                    return 1.2
            async with self.session.get(inflation_exp_url, timeout=8) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('observations'):
                        inflation_exp = float(data['observations'][0]['value'])
                else:
                    return 1.2
            real_yield = nominal_yield - inflation_exp
            return real_yield
        except Exception as e:
            logger.warning(f"⚠️ Error obteniendo rendimientos reales: {e}")
            return 1.2

    async def _fetch_inflation_expectations(self) -> float:
        """Obtiene expectativas de inflación desde FRED"""
        try:
            api_key = self.api_keys.get('fred')
            if not api_key:
                logger.warning("⚠️ API key FRED no configurada")
                return 2.0
            url = f"https://api.stlouisfed.org/fred/series/observations?series_id=T10YIE&api_key={api_key}&file_type=json&limit=1&sort_order=desc"
            async with self.session.get(url, timeout=8) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('observations'):
                        return float(data['observations'][0]['value'])
                return 2.0
        except Exception as e:
            logger.warning(f"⚠️ Error obteniendo expectativas de inflación: {e}")
            return 2.0

    async def _fetch_gold_etf_flows(self) -> float:
        """Obtiene flujos de ETFs de oro (simulación para desarrollo)"""
        # En producción, esto se conectaría a Bloomberg, Reuters, o APIs financieras
        try:
            # Simular flujos basados en condiciones de mercado
            vix = await self._fetch_vix_data()
            dxy = await self._fetch_dxy_data()
            # Lógica simplificada: VIX alto = flujos positivos, DXY alto = flujos negativos
            base_flow = 0.0
            if vix > 25:
                base_flow += 75  # Flujos positivos en volatilidad
            elif vix < 15:
                base_flow -= 25  # Flujos negativos en complacencia
            if dxy > 105:
                base_flow -= 50  # USD fuerte presiona oro
            elif dxy < 95:
                base_flow += 50  # USD débil favorece oro
            # Agregar ruido aleatorio para simulación
            import random
            noise = random.randint(-20, 20)
            return base_flow + noise
        except Exception as e:
            logger.warning(f"⚠️ Error obteniendo flujos ETF: {e}")
            return 0.0

    # Implementaciones específicas de fuentes (mantenidas del código original)
    async def _fetch_vix_alphavantage(self) -> Optional[float]:
        """Fetch VIX desde Alpha Vantage"""
        try:
            api_key = self.api_keys.get('alpha_vantage')
            if not api_key:
                return None
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=VIX&apikey={api_key}"
            async with self.session.get(url, timeout=8) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    price = data.get('Global Quote', {}).get('05. price')
                    return float(price) if price else None
            return None
        except Exception as e:
            logger.debug(f"❌ Error Alpha Vantage VIX: {e}")
            return None

    async def _fetch_vix_fred(self) -> Optional[float]:
        """Fetch VIX desde FRED"""
        try:
            api_key = self.api_keys.get('fred')
            if not api_key:
                return None
            url = f"https://api.stlouisfed.org/fred/series/observations?series_id=VIXCLS&api_key={api_key}&file_type=json&limit=1&sort_order=desc"
            async with self.session.get(url, timeout=8) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('observations'):
                        return float(data['observations'][0]['value'])
            return None
        except Exception as e:
            logger.debug(f"❌ Error FRED VIX: {e}")
            return None

    async def _fetch_vix_polygon(self) -> Optional[float]:
        """Fetch VIX desde Polygon"""
        try:
            api_key = self.api_keys.get('polygon')
            if not api_key:
                return None
            url = f"https://api.polygon.io/v2/aggs/ticker/VIX/prev?adjusted=true&apiKey={api_key}"
            async with self.session.get(url, timeout=8) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('results'):
                        return float(data['results'][0]['c'])
            return None
        except Exception as e:
            logger.debug(f"❌ Error Polygon VIX: {e}")
            return None

    async def _fetch_dxy_fred(self) -> Optional[float]:
        """Fetch DXY desde FRED"""
        try:
            api_key = self.api_keys.get('fred')
            if not api_key:
                return None
            url = f"https://api.stlouisfed.org/fred/series/observations?series_id=DTWEXBGS&api_key={api_key}&file_type=json&limit=1&sort_order=desc"
            async with self.session.get(url, timeout=8) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('observations'):
                        return float(data['observations'][0]['value'])
            return None
        except Exception as e:
            logger.debug(f"❌ Error FRED DXY: {e}")
            return None

    async def _fetch_dxy_polygon(self) -> Optional[float]:
        """Fetch DXY desde Polygon"""
        try:
            api_key = self.api_keys.get('polygon')
            if not api_key:
                return None
            url = f"https://api.polygon.io/v2/aggs/ticker/DXY/prev?adjusted=true&apiKey={api_key}"
            async with self.session.get(url, timeout=8) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('results'):
                        return float(data['results'][0]['c'])
            return None
        except Exception as e:
            logger.debug(f"❌ Error Polygon DXY: {e}")
            return None

    async def _fetch_dxy_finnhub(self) -> Optional[float]:
        """Fetch DXY desde Finnhub"""
        try:
            api_key = self.api_keys.get('finnhub')
            if not api_key:
                return None
            url = f"https://finnhub.io/api/v1/forex/rates?base=USD&token={api_key}"
            async with self.session.get(url, timeout=8) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('quote', {}).get('USD', 102.0)
            return None
        except Exception as e:
            logger.debug(f"❌ Error Finnhub DXY: {e}")
            return None

    def _process_data_results(self, results: List[Any]) -> Dict[str, Any]:
        """Procesa resultados de las tareas de obtención de datos"""
        processed = {}
        data_keys = ['vix', 'dxy', 'yields', 'inflation', 'etf_flows']
        for i, result in enumerate(results):
            if i < len(data_keys) and not isinstance(result, Exception) and result is not None:
                processed[data_keys[i]] = result
        return processed

    def _get_cached_analysis(self) -> Optional[EnhancedMacroBias]:
        """Obtiene análisis cacheado"""
        cache_key = "macro_bias"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if self._is_cache_valid(cached['timestamp']):
                logger.debug("📦 Usando análisis macro cacheado")
                return cached['data']
        return None

    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Verifica si el cache es válido"""
        return (datetime.now() - timestamp).total_seconds() < self.cache_duration

    def _update_cache(self, key: str, data: EnhancedMacroBias):
        """Actualiza el cache"""
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.now()
        }

    def _update_historical_data(self, data: Dict[str, Any], analysis: EnhancedMacroBias):
        """Actualiza datos históricos para análisis de tendencias"""
        for key in ['vix', 'dxy', 'yields']:
            if key in data:
                self.historical_data[key].append(data[key])
                if len(self.historical_data[key]) > self.max_history_size:
                    self.historical_data[key].pop(0)
        self.historical_data['bias_scores'].append(analysis.bias_score)
        if len(self.historical_data['bias_scores']) > self.max_history_size:
            self.historical_data['bias_scores'].pop(0)

    def _get_fallback_analysis(self) -> EnhancedMacroBias:
        """Análisis de fallback para errores"""
        logger.warning("🔄 Usando análisis macro de fallback")
        return EnhancedMacroBias(
            vix=20.0,
            dxy=102.0,
            real_yields=1.2,
            inflation_expectations=2.0,
            gold_etf_flows=0.0,
            bias_score=5,
            kill_switch=False,
            confidence=0.5,
            regime=InflationRegime.GOLDILOCKS,
            market_regime=MarketRegime.NEUTRAL,
            gold_bias=GoldBias.NEUTRAL,
            risk_multiplier=0.5,
            timestamp=datetime.now(),
            data_sources=['fallback'],
            data_quality=0.3,
            signal_strength=0.3,
            regime_confidence=0.5,
            technical_factors={},
            fundamental_factors={},
            sentiment_factors={}
        )

    async def _update_health_metrics(self, analysis: EnhancedMacroBias):
        """Actualiza HealthMonitor con métricas del agente macro"""
        try:
            health_monitor = get_health_monitor()
            metrics = {
                "bias_score": analysis.bias_score,
                "confidence": analysis.confidence,
                "risk_multiplier": analysis.risk_multiplier,
                "data_quality": analysis.data_quality,
                "kill_switch_active": analysis.kill_switch,
                "success_rate": (self.metrics['successful_requests'] / self.metrics['total_requests']) * 100 if self.metrics['total_requests'] > 0 else 0,
                "avg_response_time": self.metrics['avg_response_time'],
                "cache_hit_rate": (self.metrics['cache_hits'] / self.metrics['total_requests']) * 100 if self.metrics['total_requests'] > 0 else 0
            }
            await health_monitor.update_agent_metrics("macro_agent", metrics)
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron enviar métricas a HealthMonitor: {e}")

    def _health_callback(self) -> Dict[str, Any]:
        """
        Callback para HealthMonitor - ajusta comportamiento basado en salud del sistema
        """
        with self._lock:
            status_info = {
                "status": "OK" if self.circuit_breaker.is_open() else "DEGRADED",
                "metrics": self.metrics,
                "circuit_breaker_state": self.circuit_breaker.get_state(),
                "cache_size": len(self.cache),
                "historical_data_points": sum(len(v) for v in self.historical_data.values()),
                "last_analysis_time": self.last_analysis.timestamp.isoformat() if self.last_analysis else None
            }
        # Ajustar comportamiento basado en estado del sistema
        if status_info["status"] == "DEGRADED":
            # En modo degradado, reducir exigencia de confianza
            self.thresholds['min_confidence'] = 0.5
            logger.info("🔧 Modo degradado: reducido umbral mínimo de confianza a 50%")
        return status_info

    async def _fred_ws_listener(self):
        """Listener de WebSocket para datos macro en tiempo real"""
        uri = self.agent_config.get('fred_ws_uri', "wss://api.stlouisfed.org/fred/ws")
        while True:
            try:
                async with websockets.connect(uri) as ws:
                    logger.info("🔌 Conectado a FRED WebSocket")
                    # Suscribirse a datos relevantes
                    subscribe_msg = {
                        "action": "subscribe",
                        "series": ["VIXCLS", "DTWEXBGS", "DFII10", "T10YIE"]
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    async for msg in ws:
                        data = json.loads(msg)
                        await self._update_from_ws(data)
            except websockets.exceptions.ConnectionClosed:
                logger.warning("🔌 WebSocket FRED desconectado - reconectando en 30s")
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"❌ Error en WebSocket FRED: {e}")
                await asyncio.sleep(30)

    async def _update_from_ws(self, data: Dict[str, Any]):
        """Actualiza datos desde WebSocket en tiempo real"""
        try:
            series_id = data.get('series_id')
            value = data.get('value')
            if series_id == "VIXCLS" and value:
                self.cache['vix'] = float(value)
            elif series_id == "DTWEXBGS" and value:
                self.cache['dxy'] = float(value)
            elif series_id == "DFII10" and value:
                self.cache['yields'] = float(value)
            elif series_id == "T10YIE" and value:
                self.cache['inflation'] = float(value)
            logger.debug(f"📊 WS Update - {series_id}: {value}")
        except Exception as e:
            logger.error(f"❌ Error procesando WS data: {e}")

    def get_agent_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas del agente para monitoreo"""
        with self._lock:
            return {
                **self.metrics,
                'cache_size': len(self.cache),
                'historical_data_points': sum(len(v) for v in self.historical_data.values()),
                'circuit_breaker_state': self.circuit_breaker.get_state(),
                'last_analysis_time': self.last_analysis.timestamp.isoformat() if self.last_analysis else None
            }

    def get_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas para HealthMonitor"""
        return self.get_agent_metrics()

    async def close(self):
        """Cierre seguro del agente"""
        logger.info("🔌 Cerrando Macro Analysis Agent...")
        if self.ws_task:
            self.ws_task.cancel()
            try:
                await self.ws_task
            except asyncio.CancelledError:
                logger.debug("WebSocket task cancelado")
        if self.session:
            await self.session.close()
        # Enviar métricas finales a HealthMonitor
        if self.last_analysis:
            await self._update_health_metrics(self.last_analysis)
        logger.info("✅ Macro Analysis Agent cerrado correctamente")

# Función de fábrica para integración con el sistema
def create_macro_analysis_agent(config: Dict[str, Any]) -> MacroAnalysisAgent:
    """Crea y configura el agente de análisis macro"""
    return MacroAnalysisAgent(config)

# Ejemplo de uso
async def main():
    """Función principal de ejemplo"""
    config = {
        "macro_agent": {
            "websocket_enabled": False,
            "fred_ws_uri": "wss://api.stlouisfed.org/fred/ws"
        },
        "api_keys": {
            "alpha_vantage": "YOUR_ALPHA_VANTAGE_KEY",
            "fred": "YOUR_FRED_KEY",
            "polygon": "YOUR_POLYGON_KEY",
            "finnhub": "YOUR_FINNHUB_KEY"
        }
    }
    # Crear agente
    agent = create_macro_analysis_agent(config)
    await agent.initialize()
    try:
        # Ejecutar análisis varias veces para demostración
        for i in range(3):
            analysis = await agent.analyze_market_conditions()
            print(f"\n📊 Análisis Macro {i+1}:")
            print(f"   Score: {analysis.bias_score}/10")
            print(f"   Gold Bias: {analysis.gold_bias.value}")
            print(f"   Régimen: {analysis.regime.value}")
            print(f"   Risk Multiplier: {analysis.risk_multiplier:.2f}")
            print(f"   Confianza: {analysis.confidence:.2f}")
            await asyncio.sleep(10)
    except KeyboardInterrupt:
        print("⏹️ Interrumpido por usuario")
    finally:
        await agent.close()
        # Mostrar métricas finales
        metrics = agent.get_agent_metrics()
        print("\n📈 Métricas del Agente Macro:")
        print(json.dumps(metrics, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())