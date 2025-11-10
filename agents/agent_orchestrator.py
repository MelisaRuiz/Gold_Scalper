#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Agent Orchestrator - FAST/SLOW Path Architecture 
Ultra-low latency for XAUUSD scalping with intelligent caching.
Solves: IA latency (200-500ms) vs Scalping requirements (<50ms)
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import threading

# Importación de la infraestructura de Guardrails
from infrastructure.guardrails import SafetyGuardrailSystem

# Importación de la infraestructura de Health Monitor
from infrastructure.health_monitor import HealthMonitor

# Importación de la infraestructura de Market Data Collector
from data.market_data_collector import MarketDataCollector

# Importación de la infraestructura de Performance Tracker
from monitoring.performance_tracker import PerformanceTracker

# Importación de Agentes Concretos
from agents.macro_analysis_agent import MacroAnalysisAgent
from agents.signal_validation_agent import SignalValidationAgent
from agents.liquidity_analysis_agent import LiquidityAnalysisAgent

# AGREGADO: Importación del Generador de Señales
from core.signal_generator import SignalGenerator

logger = logging.getLogger("HECTAGold.AgentOrchestrator")

class ValidationDecision(Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT" 
    MODIFY = "MODIFY"
    PENDING = "PENDING"

@dataclass
class ValidationResult:
    decision: ValidationDecision
    risk_multiplier: float
    validation_score: float
    confidence_reasoning: List[str]
    latency_ms: float
    used_cache: bool
    guardrail_triggered: bool = False
    trade_id: Optional[str] = None 

@dataclass
class SignalData:
    pattern_type: str
    timeframe: str
    entry_price: float
    stop_loss: float
    take_profit: float
    volume_profile: Dict[str, float]
    technical_indicators: Dict[str, Any]
    session_timing: str
    required_imbalance: Optional[str] = None 
    volume: float = 0.0 

@dataclass
class MarketContext:
    vix: float
    dxy: float
    real_yields: float
    gold_volatility: float
    market_regime: str
    liquidity_conditions: str
    # NUEVO: Campos para guardrails precalculados (R9)
    vix_alert: bool = False
    dxy_alert: bool = False
    volatility_alert: bool = False
    regime_alert: bool = False
    # NUEVO: Métricas de calidad de datos (R10)
    data_quality_score: float = 1.0
    # NUEVO: Estado del kill switch (R6)
    kill_switch_active: bool = False

class AgentOrchestrator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.agent_config = config.get('agents_config', {})
        
        # Cache system for FAST path - ACTUALIZADO LÍMITES (R2)
        self.risk_multiplier_cache = 1.0
        self.macro_context_cache: Optional[MarketContext] = None
        self.last_cache_update = 0
        self.cache_ttl = 30
        
        # NUEVO: Métricas para monitoreo de consenso (R11)
        self.consensus_discrepancy_history = []
        self.max_consensus_threshold = 0.3
        
        # Performance tracking
        self.fast_path_times = []
        self.slow_path_times = []
        
        # Agentes concretos
        self.guardrail_system = SafetyGuardrailSystem()
        
        # Inicialización de Agentes Concretos
        self.macro_agent = MacroAnalysisAgent(config)
        self.signal_validator = SignalValidationAgent(config)
        self.liquidity_agent = LiquidityAnalysisAgent(config)
        # AGREGADO: Inicialización del Generador de Señales
        self.signal_generator = SignalGenerator(config)
        
        # Background task management
        self.background_task = None
        self.is_running = False
        
        # Thread safety
        self.cache_lock = threading.RLock()

        # Inicialización de Observabilidad
        self.health_monitor = HealthMonitor()
        self.market_data_collector = MarketDataCollector(config)
        self.performance_tracker = PerformanceTracker(config)
        
        logger.info("🚀 AgentOrchestrator initialized - FAST/SLOW path architecture")

    async def initialize(self):
        """Initialize all agents and start background tasks"""
        try:
            # 1. Inicializar Market Data Collector
            await self.market_data_collector.initialize()
            
            # 2. Inicializar Performance Tracker
            await self.performance_tracker.initialize()

            # 3. Inicializar Agentes Concretos
            await self.macro_agent.initialize()
            await self.signal_validator.initialize()
            await self.liquidity_agent.initialize()
            
            # AGREGADO: Inicializar Generador de Señales
            await self.signal_generator.initialize()
            
            # 4. Inicializar Guardrail System
            await self.guardrail_system.initialize()
            
            # 5. Inicializar Health Monitor
            await self.health_monitor.initialize()
            
            # 6. Cargar contexto macro inicial
            await self._load_initial_macro_context()
            
            # 7. Start background slow path updates
            self.is_running = True
            self.background_task = asyncio.create_task(self._background_slow_path_updater())
            
            logger.info("✅ All agents initialized and background tasks started")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize AgentOrchestrator: {e}")
            raise

    async def _load_initial_macro_context(self):
        """Cargar contexto macro inicial para el cache"""
        try:
            macro_result = await self.macro_agent.analyze_market_conditions()
            
            # NUEVO: Calcular guardrails precomputados (R9)
            vix = macro_result.get('vix', 18.0)
            dxy = macro_result.get('dxy', 104.0)
            gold_volatility = macro_result.get('gold_volatility', 1.5)
            market_regime = macro_result.get('market_regime', 'NORMAL')
            
            # Crear MarketContext con guardrails precalculados
            self.macro_context_cache = MarketContext(
                vix=vix,
                dxy=dxy,
                real_yields=macro_result.get('real_yields', 2.3),
                gold_volatility=gold_volatility,
                market_regime=market_regime,
                liquidity_conditions=macro_result.get('liquidity_conditions', 'NORMAL'),
                # NUEVO: Guardrails precalculados para FAST path
                vix_alert=vix > 25,
                dxy_alert=dxy > 106.0 or dxy < 102.0,
                volatility_alert=gold_volatility > 3.0,
                regime_alert=market_regime == "VOLATILE",
                # NUEVO: Calidad de datos (R10)
                data_quality_score=macro_result.get('data_quality', 1.0),
                # NUEVO: Kill switch state (R6)
                kill_switch_active=macro_result.get('kill_switch', False)
            )
            
            # Actualizar cache de risk multiplier con límite 1.5 (R2)
            risk_multiplier = macro_result.get('risk_multiplier', 1.0)
            self._update_risk_multiplier_cache(risk_multiplier)
            
            logger.info(f"✅ Initial macro context loaded: VIX={self.macro_context_cache.vix}, DXY={self.macro_context_cache.dxy}")
            logger.info(f"🛡️ Precomputed guardrails: VIX_alert={self.macro_context_cache.vix_alert}, DXY_alert={self.macro_context_cache.dxy_alert}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load initial macro context: {e}")
            # Usar valores por defecto seguros con guardrails activados
            self.macro_context_cache = MarketContext(
                vix=18.0, dxy=104.0, real_yields=2.3,
                gold_volatility=1.5, market_regime='NORMAL', liquidity_conditions='NORMAL',
                vix_alert=False, dxy_alert=False, volatility_alert=False, regime_alert=False,
                data_quality_score=0.5, kill_switch_active=False  # Calidad baja en fallback
            )

    async def validate_signal(self, signal_data: SignalData, 
                            market_context: MarketContext) -> ValidationResult:
        """
        FAST PATH validation - Target: < 50ms latency
        """
        start_time = time.time()
        
        try:
            # NUEVO: Verificar edad del cache y degradar si es necesario (R3)
            cache_age = time.time() - self.last_cache_update
            if cache_age > self.cache_ttl * 2:  # 2x TTL
                logger.warning(f"⚠️ Cache demasiado antiguo ({cache_age:.1f}s), degradando risk multiplier")
                degraded_multiplier = 0.8  # Modo conservador
                self._update_risk_multiplier_cache(degraded_multiplier)

            # 1. Obtener datos de mercado de ultra-baja latencia
            current_price = await self.market_data_collector.get_current_price("XAUUSD")
            current_imbalance = await self.market_data_collector.get_order_book_imbalance("XAUUSD")

            # 2. Quick technical validation (non-IA, deterministic)
            technical_validation = self._fast_technical_validation(signal_data)
            
            # Imbalance validation (crucial para scalping)
            if signal_data.required_imbalance and signal_data.required_imbalance != current_imbalance:
                technical_validation["valid"] = False
                technical_validation["reasons"].append(f"Imbalance mismatch: Expected {signal_data.required_imbalance}, got {current_imbalance}")
                
            if not technical_validation["valid"]:
                result = ValidationResult(
                    decision=ValidationDecision.REJECT,
                    risk_multiplier=1.0,
                    validation_score=0.0,
                    confidence_reasoning=technical_validation["reasons"],
                    latency_ms=(time.time() - start_time) * 1000,
                    used_cache=True
                )
                self._report_fast_path_metrics(result) 
                return result

            # 3. Apply guardrails (fast safety checks) - OPTIMIZADO (R9)
            guardrail_result = await self._fast_guardrail_check(signal_data, market_context)
            if guardrail_result.get("triggered"):
                result = ValidationResult(
                    decision=ValidationDecision.REJECT,
                    risk_multiplier=1.0,
                    validation_score=0.0,
                    confidence_reasoning=[f"Guardrail triggered: {guardrail_result.get('reason')}"],
                    latency_ms=(time.time() - start_time) * 1000,
                    used_cache=True,
                    guardrail_triggered=True
                )
                self._report_fast_path_metrics(result) 
                return result
            
            # 4. Get cached risk multiplier (updated by slow path)
            cached_multiplier = self._get_cached_risk_multiplier()
            
            # 5. Fast confidence calculation
            confidence_score = self._calculate_fast_confidence(signal_data, market_context)
            
            latency_ms = (time.time() - start_time) * 1000
            
            if latency_ms > 50:
                logger.warning(f"⚠️ Fast path latency high: {latency_ms:.1f}ms")

            # 6. Preparar y Registrar la Ejecución del Trade
            if confidence_score > 0.7: 
                trade_data = self._create_trade_data(signal_data, cached_multiplier, current_price, current_imbalance)
                trade_id = await self.performance_tracker.record_trade_execution(trade_data)
                logger.info(f"✅ Signal APROBADA. Trade registrado con ID: {trade_id}")
                decision = ValidationDecision.APPROVE
            else:
                decision = ValidationDecision.REJECT

            result = ValidationResult(
                decision=decision,
                risk_multiplier=cached_multiplier,
                validation_score=confidence_score,
                confidence_reasoning=technical_validation["reasons"],
                latency_ms=latency_ms,
                used_cache=True,
                trade_id=trade_id 
            )
            
            self._report_fast_path_metrics(result) 
            return result
            
        except Exception as e:
            logger.error(f"❌ Fast path validation error: {e}")
            # Fallback to safe rejection
            result = ValidationResult(
                decision=ValidationDecision.REJECT,
                risk_multiplier=1.0,
                validation_score=0.0,
                confidence_reasoning=[f"Validation error: {str(e)}"],
                latency_ms=(time.time() - start_time) * 1000,
                used_cache=False
            )
            self._report_fast_path_metrics(result) 
            return result

    def _create_trade_data(self, signal_data: SignalData, risk_multiplier: float, 
                           entry_price: float, imbalance: str) -> Dict[str, Any]:
        """Crea el diccionario de datos de trade para el Performance Tracker."""
        
        return {
            "symbol": "XAUUSD",
            "side": "BUY" if signal_data.stop_loss < signal_data.entry_price else "SELL",
            "volume": signal_data.volume * risk_multiplier,
            "entry_price_requested": signal_data.entry_price,
            "entry_price_executed": entry_price, 
            "stop_loss": signal_data.stop_loss,
            "take_profit": signal_data.take_profit,
            "imbalance_at_execution": imbalance,
            "validation_path": "FAST",
            "timestamp": datetime.utcnow().isoformat()
        }

    def _report_fast_path_metrics(self, result: ValidationResult):
        """Método interno para reportar métricas del FAST PATH al health monitor."""
        try:
            self.health_monitor.record_metric(
                "fast_path.validation_score", 
                result.validation_score
            )
            self.health_monitor.record_metric(
                "fast_path.response_time_ms", 
                result.latency_ms
            )
            self.health_monitor.record_metric(
                "fast_path.risk_multiplier", 
                result.risk_multiplier
            )
            
            logger.debug(f"Metrics reported for FAST path: {result.latency_ms:.1f}ms")
        except Exception as e:
            logger.error(f"Error reporting fast path metrics: {e}")

    async def comprehensive_validation(self, signal_data: SignalData,
                                       market_context: MarketContext) -> ValidationResult:
        """
        SLOW PATH validation - Full IA analysis (200-500ms)
        """
        start_time = time.time()
        
        try:
            # 1. Macro Analysis
            macro_result = await self.macro_agent.analyze_market_conditions()
            
            # 2. Run Signal and Liquidity Agents in parallel
            tasks = [
                self.signal_validator.validate_signal(signal_data, macro_result, market_context),
                self.liquidity_agent.analyze_liquidity_conditions("XAUUSD", signal_data.__dict__)
            ]
            
            # Ejecución en paralelo
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Insertar resultado Macro en la lista para procesamiento unificado
            results.insert(0, macro_result) 
            
            # Process results with guardrails
            processed_results = await self._process_slow_path_results(results)
            
            # Update cache with new risk multiplier - ACTUALIZADO LÍMITE 1.5 (R2)
            new_multiplier = processed_results.get('risk_multiplier', 1.0)
            self._update_risk_multiplier_cache(new_multiplier)
            
            latency_ms = (time.time() - start_time) * 1000
            
            logger.info(f"📊 Slow path completed: {latency_ms:.1f}ms, multiplier: {new_multiplier:.2f}")

            result = ValidationResult(
                decision=processed_results.get('decision', ValidationDecision.REJECT),
                risk_multiplier=new_multiplier,
                validation_score=processed_results.get('validation_score', 0.0),
                confidence_reasoning=processed_results.get('reasoning', []),
                latency_ms=latency_ms,
                used_cache=False
            )
            
            self._report_slow_path_metrics(result) 
            return result
            
        except Exception as e:
            logger.error(f"❌ Slow path validation error: {e}")
            raise

    def _report_slow_path_metrics(self, result: ValidationResult):
        """Método interno para reportar métricas del SLOW PATH al health monitor."""
        try:
            self.health_monitor.record_metric(
                "slow_path.validation_score", 
                result.validation_score
            )
            self.health_monitor.record_metric(
                "slow_path.response_time_ms", 
                result.latency_ms
            )
            self.health_monitor.record_metric(
                "slow_path.risk_multiplier", 
                result.risk_multiplier
            )
            
            logger.debug(f"Metrics reported for SLOW path: {result.latency_ms:.1f}ms")
        except Exception as e:
            logger.error(f"Error reporting slow path metrics: {e}")

    def _fast_technical_validation(self, signal_data: SignalData) -> Dict[str, Any]:
        """Ultra-fast technical validation without IA - ACTUALIZADO R/R 2.0 (R7)"""
        reasons = []
        
        # 1. Pattern validation
        if signal_data.pattern_type not in ["BOS_RETEST", "LIQUIDITY_SWEEP"]:
            reasons.append("Invalid pattern type")
        
        # 2. Timeframe validation
        if signal_data.timeframe not in ["M15", "H1"]:
            reasons.append("Invalid timeframe for scalping")
        
        # 3. Session timing validation
        if signal_data.session_timing not in ["NY_OPEN", "LONDON_NY_OVERLAP"]:
            reasons.append("Outside optimal session")
        
        # 4. Risk/Reward validation - ACTUALIZADO A 2.0 (R7)
        risk = abs(signal_data.entry_price - signal_data.stop_loss)
        reward = abs(signal_data.take_profit - signal_data.entry_price)
        rr_ratio = reward / risk if risk > 0 else 0
        
        if rr_ratio < 2.0:  # ACTUALIZADO: 1.5 → 2.0 para cumplimiento EAS
            reasons.append(f"Low R/R ratio: {rr_ratio:.1f} - EAS requires 2.0")
        
        # 5. Volume profile check
        if signal_data.volume_profile.get('liquidity_zone_score', 0) < 0.6:
            reasons.append("Weak liquidity zone")
        
        valid = len(reasons) == 0
        if not valid:
            reasons.insert(0, "Fast technical validation failed")
        
        return {"valid": valid, "reasons": reasons}

    async def _fast_guardrail_check(self, signal_data: SignalData, 
                                 market_context: MarketContext) -> Dict[str, Any]:
        """Fast safety guardrails using precomputed flags (R9)"""
        
        # NUEVO: Usar banderas precomputadas del slow path para mínima latencia
        if market_context.vix_alert:
            return {"triggered": True, "guardrail_type": "vix", "reason": "High VIX"}
        
        if market_context.dxy_alert:
            return {"triggered": True, "guardrail_type": "dxy", "reason": "Extreme DXY"}
        
        if market_context.volatility_alert:
            return {"triggered": True, "guardrail_type": "volatility", "reason": "High volatility"}
        
        if market_context.regime_alert:
            return {"triggered": True, "guardrail_type": "regime", "reason": "Volatile regime"}
        
        # NUEVO: Verificar kill switch (R6)
        if market_context.kill_switch_active:
            return {"triggered": True, "guardrail_type": "kill_switch", "reason": "Kill switch active"}
        
        # NUEVO: Verificar calidad de datos (R10)
        if market_context.data_quality_score < 0.5:
            return {"triggered": True, "guardrail_type": "data_quality", "reason": "Low data quality"}
        
        return {"triggered": False, "guardrail_type": "none", "reason": ""}

    def _calculate_fast_confidence(self, signal_data: SignalData, 
                                 market_context: MarketContext) -> float:
        """Fast confidence calculation without IA"""
        confidence = 0.7
        
        # Adjust based on technical factors
        if signal_data.pattern_type == "BOS_RETEST":
            confidence += 0.1
        elif signal_data.pattern_type == "LIQUIDITY_SWEEP":
            confidence += 0.15
            
        # Adjust based on session timing
        if signal_data.session_timing == "NY_OPEN":
            confidence += 0.1
            
        # Adjust based on market context
        if 15 <= market_context.vix <= 20:
            confidence += 0.05
        if 103.0 <= market_context.dxy <= 105.0:
            confidence += 0.05
            
        # NUEVO: Ajustar por calidad de datos (R10)
        confidence *= market_context.data_quality_score
            
        return min(0.95, confidence)

    def _get_cached_risk_multiplier(self) -> float:
        """Thread-safe cache access"""
        with self.cache_lock:
            return self.risk_multiplier_cache

    def _update_risk_multiplier_cache(self, new_multiplier: float):
        """Thread-safe cache update - ACTUALIZADO LÍMITE 1.5 (R2)"""
        with self.cache_lock:
            # ACTUALIZADO: 1.2 → 1.5 para consistencia con agentes
            self.risk_multiplier_cache = max(0.8, min(1.5, new_multiplier))
            self.last_cache_update = time.time()
            logger.debug(f"🔄 Risk multiplier cache updated: {self.risk_multiplier_cache:.2f}")

    async def _run_slow_path_generation_cycle(self):
        """
        Ciclo de generación, validación y actualización de cache del SLOW PATH.
        """
        start_time = time.time()
        
        try:
            # 1. Obtener datos de mercado
            market_data = await self.market_data_collector.get_latest_market_data("XAUUSD")
            current_session = self._get_current_session() 
            
            # 2. Análisis Macro
            macro_bias = await self.macro_agent.analyze_market_conditions()
            
            # 3. Análisis de Liquidez
            liquidity_analysis = await self.liquidity_agent.analyze_liquidity_conditions("XAUUSD", market_data)
            
            # 4. Generación de Señales
            signals = await self.signal_generator.generate_signals(
                market_data, macro_bias, liquidity_analysis, current_session
            )
            
            logger.info(f"✅ SLOW PATH: Generadas {len(signals)} señales para validación.")

            # 5. Validación de Señales generadas
            validated_results = []
            if signals and self.macro_context_cache:
                for signal_data in signals:
                    validation_result = await self.signal_validator.validate_signal(
                        signal_data, 
                        macro_bias, 
                        self.macro_context_cache 
                    )
                    
                    # NUEVO: Monitorear discrepancia de consenso (R11)
                    if hasattr(validation_result, 'consensus_discrepancy'):
                        self._record_consensus_discrepancy(validation_result.consensus_discrepancy)
                    
                    # Extraer decision del resultado de validación
                    if hasattr(validation_result, 'decision'):
                        decision = validation_result.decision
                    elif isinstance(validation_result, dict):
                        decision = validation_result.get('decision')
                    else:
                        decision = ValidationDecision.REJECT
                    
                    if decision == ValidationDecision.APPROVE:
                        validated_results.append(validation_result)

            # 6. Consenso para actualización de cache
            new_multiplier = macro_bias.get('risk_multiplier', 1.0) if isinstance(macro_bias, dict) else 1.0
            
            if validated_results:
                try:
                    multipliers = []
                    for result in validated_results:
                        if hasattr(result, 'risk_multiplier'):
                            multipliers.append(result.risk_multiplier)
                        elif isinstance(result, dict):
                            multipliers.append(result.get('risk_multiplier', 1.0))
                    
                    if multipliers:
                        avg_multiplier = sum(multipliers) / len(multipliers)
                        new_multiplier = avg_multiplier
                except Exception as e:
                    logger.warning(f"Error calculando promedio de risk_multiplier: {e}")
            
            # 7. Actualizar cache con límite 1.5 (R2)
            self._update_risk_multiplier_cache(new_multiplier)
            
            # NUEVO: Actualizar contexto macro con guardrails precomputados (R9)
            await self._update_macro_context_with_guardrails(macro_bias)

            latency_ms = (time.time() - start_time) * 1000
            logger.info(f"📊 Ciclo SLOW PATH completado en {latency_ms:.1f}ms. Nuevo Multiplicador: {new_multiplier:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Error en ciclo SLOW PATH: {e}")

    async def _update_macro_context_with_guardrails(self, macro_bias: Dict[str, Any]):
        """Actualiza el contexto macro con guardrails precomputados (R9)"""
        try:
            if not self.macro_context_cache:
                return
                
            # Calcular guardrails precomputados
            vix = macro_bias.get('vix', 18.0)
            dxy = macro_bias.get('dxy', 104.0)
            gold_volatility = macro_bias.get('gold_volatility', 1.5)
            market_regime = macro_bias.get('market_regime', 'NORMAL')
            data_quality = macro_bias.get('data_quality', 1.0)
            kill_switch = macro_bias.get('kill_switch', False)
            
            # Actualizar contexto existente
            self.macro_context_cache.vix = vix
            self.macro_context_cache.dxy = dxy
            self.macro_context_cache.gold_volatility = gold_volatility
            self.macro_context_cache.market_regime = market_regime
            self.macro_context_cache.data_quality_score = data_quality
            self.macro_context_cache.kill_switch_active = kill_switch
            
            # Actualizar guardrails precomputados
            self.macro_context_cache.vix_alert = vix > 25
            self.macro_context_cache.dxy_alert = dxy > 106.0 or dxy < 102.0
            self.macro_context_cache.volatility_alert = gold_volatility > 3.0
            self.macro_context_cache.regime_alert = market_regime == "VOLATILE"
            
            logger.debug(f"🛡️ Macro context updated with precomputed guardrails")
            
        except Exception as e:
            logger.error(f"❌ Error updating macro context with guardrails: {e}")

    def _record_consensus_discrepancy(self, discrepancy: float):
        """Registra discrepancia de consenso para monitoreo (R11)"""
        self.consensus_discrepancy_history.append(discrepancy)
        # Mantener solo últimas 100 mediciones
        if len(self.consensus_discrepancy_history) > 100:
            self.consensus_discrepancy_history.pop(0)
        
        # Alertar si la discrepancia es consistentemente alta
        if len(self.consensus_discrepancy_history) >= 10:
            avg_discrepancy = sum(self.consensus_discrepancy_history[-10:]) / 10
            if avg_discrepancy > self.max_consensus_threshold:
                logger.warning(f"🚨 Alta discrepancia de consenso: {avg_discrepancy:.3f}")
                # Reportar al health monitor
                self.health_monitor.record_metric("consensus.avg_discrepancy", avg_discrepancy)

    async def _background_slow_path_updater(self):
        """Background task that updates cache with slow path analysis"""
        logger.info("🔄 Starting background slow path updater")
        
        while self.is_running:
            try:
                # Wait for cache TTL
                await asyncio.sleep(self.cache_ttl)
                
                # Solo ejecutamos el ciclo si el contexto macro inicial ha sido cargado
                if self.macro_context_cache:
                    await self._run_slow_path_generation_cycle()
                else:
                    logger.debug("Esperando carga inicial del contexto macro antes de correr ciclo SLOW PATH.")
                    await asyncio.sleep(5)  # Esperar menos tiempo si no hay contexto
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Background updater error: {e}")
                await asyncio.sleep(10)

    async def _process_slow_path_results(self, results: List[Any]) -> Dict[str, Any]:
        """Process and validate slow path results with consensus"""
        valid_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"⚠️ Agent {i} returned exception: {result}")
                continue
            valid_results.append(result)
        
        if not valid_results:
            return {"decision": ValidationDecision.REJECT, "validation_score": 0.0, "risk_multiplier": 1.0}
        
        # Calculate consensus
        def get_value(r, key, default):
            if isinstance(r, dict):
                return r.get(key, default)
            return getattr(r, key, default)

        scores = [get_value(r, 'validation_score', 0) for r in valid_results]
        multipliers = [get_value(r, 'risk_multiplier', 1.0) for r in valid_results]
        reasonings = [get_value(r, 'reasoning', []) for r in valid_results]

        avg_score = sum(scores) / len(valid_results)
        avg_multiplier = sum(multipliers) / len(valid_results)
        
        # Apply guardrails to final decision
        final_decision = self._apply_consensus_guardrails(valid_results, avg_score)
        
        return {
            'decision': final_decision,
            'validation_score': avg_score,
            'risk_multiplier': avg_multiplier,
            'reasoning': [item for sublist in reasonings if isinstance(sublist, list) for item in sublist]
        }

    def _apply_consensus_guardrails(self, results: List[Any], avg_score: float) -> ValidationDecision:
        """Apply safety guardrails to consensus decision"""
        
        if avg_score < 0.6:
            return ValidationDecision.REJECT
            
        # Check for high disagreement
        scores = []
        for r in results:
            if isinstance(r, dict):
                scores.append(r.get('validation_score', 0))
            else:
                scores.append(getattr(r, 'validation_score', 0))
                
        max_diff = max(scores) - min(scores)
        
        if max_diff > 0.3:
            return ValidationDecision.REJECT
            
        return ValidationDecision.APPROVE

    def _get_current_session(self) -> str:
        """Obtiene la sesión de trading actual"""
        # Implementación básica - en producción usar SessionManager
        from datetime import datetime
        now = datetime.now()
        hour = now.hour
        
        if 9 <= hour <= 11:  # 9 AM - 11 AM ET
            return "NY_OPEN"
        elif 13 <= hour <= 17:  # 1 PM - 5 PM GMT (Londres-NY overlap)
            return "LONDON_NY_OVERLAP"
        else:
            return "OFF_SESSION"

    async def shutdown(self):
        """Graceful shutdown"""
        self.is_running = False
        if self.background_task:
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass
        
        # Detener componentes
        await self.macro_agent.shutdown() 
        await self.signal_validator.shutdown() 
        await self.liquidity_agent.shutdown() 
        await self.signal_generator.shutdown()
        await self.performance_tracker.shutdown()
        await self.market_data_collector.shutdown()
        await self.guardrail_system.shutdown()
        await self.health_monitor.shutdown()
        
        logger.info("🛑 AgentOrchestrator shutdown complete")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring"""
        fast_avg = sum(self.fast_path_times[-100:]) / max(len(self.fast_path_times[-100:]), 1) if self.fast_path_times else 0
        slow_avg = sum(self.slow_path_times[-100:]) / max(len(self.slow_path_times[-100:]), 1) if self.slow_path_times else 0
        
        # NUEVO: Métricas de consenso (R11)
        avg_discrepancy = sum(self.consensus_discrepancy_history) / max(len(self.consensus_discrepancy_history), 1) if self.consensus_discrepancy_history else 0
        
        return {
            'fast_path_avg_latency_ms': fast_avg,
            'slow_path_avg_latency_ms': slow_avg,
            'current_risk_multiplier': self.risk_multiplier_cache,
            'last_cache_update': self.last_cache_update,
            'background_task_running': self.is_running,
            'macro_context_loaded': self.macro_context_cache is not None,
            # NUEVO: Métricas de consenso
            'consensus_avg_discrepancy': avg_discrepancy,
            'consensus_samples': len(self.consensus_discrepancy_history),
            'cache_age_seconds': time.time() - self.last_cache_update
        }

# Factory function para compatibilidad
def create_agent_orchestrator(config: Dict[str, Any]) -> AgentOrchestrator:
    """Factory function para crear el AgentOrchestrator"""
    return AgentOrchestrator(config)