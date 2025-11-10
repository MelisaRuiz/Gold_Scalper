#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Signal Validation Agent v4.0 - EAS Híbrido 2025 Enhanced
Integración completa con filtros EAS chinos y mecanismos de seguridad avanzados
CORREGIDO Y FUNCIONAL
"""

import asyncio
import json
import numpy as np
import statistics
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import threading

# ===== IMPLEMENTACIONES MÍNIMAS DE INFRAESTRUCTURA (si no existen) =====
class StructuredLogger:
    def __init__(self, name: str):
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

    def is_open(self) -> bool:
        return self.failures < self.max_failures

    def get_state(self) -> str:
        return "CLOSED" if self.is_open() else "OPEN"

class HealthMonitorStub:
    def __init__(self):
        self.metrics = {}

    def register_health_callback(self, callback):
        pass

    async def update_agent_metrics(self, agent: str, data: Dict):
        self.metrics.setdefault(agent, {}).update(data)

_health_monitor_instance = HealthMonitorStub()

def get_health_monitor():
    return _health_monitor_instance

def with_guardrails(agent_context: str):
    def decorator(func):
        return func
    return decorator

# ===== IMPLEMENTACIÓN MÍNIMA DE EnhancedMacroBias =====
class GoldBias(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

@dataclass
class EnhancedMacroBias:
    vix: float = 15.0
    dxy: float = 103.0
    real_yields: float = 2.0
    gold_bias: GoldBias = GoldBias.NEUTRAL
    risk_multiplier: float = 1.0
    bias_score: float = 5.0
    confidence: float = 0.7
    kill_switch: bool = False

# ===== FIN DE IMPLEMENTACIONES DE RESPALDO =====

logger = StructuredLogger("HECTAGold.SignalValidationAgent")

class ConsensusLevel(Enum):
    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    VERY_LOW = "VERY_LOW"

class SignalType(Enum):
    BOS_RETEST_BULLISH = "BOS_RETEST_BULLISH"
    BOS_RETEST_BEARISH = "BOS_RETEST_BEARISH" 
    LIQUIDITY_SWEEP_BULLISH = "LIQUIDITY_SWEEP_BULLISH"
    LIQUIDITY_SWEEP_BEARISH = "LIQUIDITY_SWEEP_BEARISH"
    ORDERBLOCK_RETEST_BULLISH = "ORDERBLOCK_RETEST_BULLISH"
    ORDERBLOCK_RETEST_BEARISH = "ORDERBLOCK_RETEST_BEARISH"
    MARKET_STRUCTURE_SHIFT = "MARKET_STRUCTURE_SHIFT"

class ValidationDecision(Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    DEFER = "DEFER"
    KILL_SWITCH = "KILL_SWITCH"
    PAUSE_LINE_BLOCK = "PAUSE_LINE_BLOCK"

class LiquidityDecision(Enum):
    OPTIMAL = "OPTIMAL"
    NORMAL = "NORMAL"
    LOW = "LOW"
    AVOID = "AVOID"

class LongShadowFilter:
    """Implementación del filtro 'Línea de Pausa' del sistema EAS chino"""
    
    def __init__(self):
        self.shadow_ratio = 1.5  # Sombra ≥1.5 veces cuerpo
        self.max_body_points = 80  # Cuerpo <80 puntos
        self.min_shadow_points = 150  # Sombra >150 puntos
        
    def detect_pause_line(self, candle_data: Dict[str, float]) -> Optional[str]:
        """
        Detecta líneas de pausa según criterios EAS chino
        
        Args:
            candle_data: Datos de la vela {open, high, low, close}
            
        Returns:
            "UPPER_PAUSE_LINE", "LOWER_PAUSE_LINE" o None
        """
        try:
            body_size = abs(candle_data['close'] - candle_data['open'])
            upper_shadow = candle_data['high'] - max(candle_data['open'], candle_data['close'])
            lower_shadow = min(candle_data['open'], candle_data['close']) - candle_data['low']
            
            # Verificar criterios de línea de pausa
            if body_size < self.max_body_points:
                if (upper_shadow >= body_size * self.shadow_ratio and 
                    upper_shadow > self.min_shadow_points):
                    return "UPPER_PAUSE_LINE"
                elif (lower_shadow >= body_size * self.shadow_ratio and 
                      lower_shadow > self.min_shadow_points):
                    return "LOWER_PAUSE_LINE"
                    
            return None
            
        except Exception as e:
            logger.error(f"❌ Error en detección de línea de pausa: {e}")
            return None

class DuplicateOrderPrevention:
    """Sistema de prevención de órdenes duplicadas por vela"""
    
    def __init__(self):
        self.last_order_time = None
        self.current_candle_start = None
        self.candle_period = 60  # 1 minuto para M1
        
    def can_open_new_order(self, symbol: str, order_type: str) -> bool:
        """
        Verifica si se puede abrir nueva orden en la vela actual
        
        Args:
            symbol: Símbolo del instrumento
            order_type: Tipo de orden (BUY/SELL)
            
        Returns:
            True si se permite nueva orden
        """
        current_time = datetime.utcnow()
        
        # Si es la primera orden o ha pasado el periodo de vela, permitir
        if (self.last_order_time is None or 
            (current_time - self.last_order_time).total_seconds() >= self.candle_period):
            self.last_order_time = current_time
            return True
            
        return False
        
    def record_order(self, order_data: Dict[str, Any]):
        """Registra nueva orden para tracking"""
        self.last_order_time = datetime.utcnow()

@dataclass
class InferenceResult:
    """Resultado de inferencia mejorado para EAS"""
    score: float
    classification: str
    reasoning: str
    recommendation: ValidationDecision
    risk_multiplier: float
    reasoning_step_by_step: str
    confidence: float
    processing_time: float
    signal_type: Optional[SignalType] = None
    validation_metrics: Dict[str, float] = None
    guardrail_checks: Dict[str, bool] = None
    pause_line_detected: Optional[str] = None

    def __post_init__(self):
        if self.validation_metrics is None:
            self.validation_metrics = {}
        if self.guardrail_checks is None:
            self.guardrail_checks = {}

@dataclass
class ValidationResult:
    """Resultado de validación EAS Híbrido 2025 mejorado"""
    validation_score: float
    risk_multiplier: float
    reasoning_steps: List[str]
    final_decision: ValidationDecision
    signal_type: SignalType
    confidence: float
    consensus_level: ConsensusLevel
    num_inferences: int
    processing_time: float
    fallback_used: bool
    kill_switch_triggered: bool
    guardrail_violations: List[str]
    timestamp: datetime
    metadata: Dict[str, Any]
    pause_line_block: bool = False  # Nuevo: Indicador de bloqueo por línea de pausa

class SignalValidationAgent:
    """
    Agente de validación de señales EAS Híbrido 2025 MEJORADO
    Integra filtros EAS chinos y mecanismos de seguridad avanzados
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el agente de validación mejorado
        
        Args:
            config: Configuración del sistema EAS
        """
        self.config = config
        self.agent_config = config.get('signal_validation_agent', {})
        
        # Parámetros de validación EAS mejorados
        validation_config = self.agent_config.get('validation', {})
        self.num_inferences = validation_config.get('num_inferences', 5)
        self.temperature = validation_config.get('temperature', 0.3)
        self.consensus_threshold = validation_config.get('consensus_threshold', 0.75)
        self.min_confidence = validation_config.get('min_confidence', 0.7)
        
        # Límites de tiempo optimizados para HFT
        self.max_tot_time = 1.2  # Reducido a 1.2 segundos
        self.per_inference_timeout = 0.4  # Reducido a 400ms por inferencia
        self.local_fallback_enabled = True
        
        # NUEVOS COMPONENTES: Filtros EAS chinos
        self.long_shadow_filter = LongShadowFilter()
        self.duplicate_prevention = DuplicateOrderPrevention()
        
        # Circuit breaker mejorado
        self.circuit_breaker = CircuitBreaker(
            max_failures=2,  # Más sensible
            reset_timeout=180  # 3 minutos de recuperación
        )
        
        # Cliente IA (Anthropic/OpenAI)
        self.ia_client = None
        self._initialize_ia_client()
        
        # Plantillas de prompts EAS mejoradas
        self.system_prompt = self._build_eas_system_prompt()
        self.few_shot_examples = self._build_eas_few_shot_examples()
        
        # Métricas mejoradas para HealthMonitor
        self.metrics = {
            'total_validations': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'timeout_validations': 0,
            'average_validation_score': 0.0,
            'fallback_activations': 0,
            'local_validations': 0,
            'average_processing_time': 0.0,
            'decision_distribution': {},
            'kill_switch_activations': 0,
            'guardrail_violations': 0,
            'pause_line_blocks': 0,
            'duplicate_order_blocks': 0,
            'last_validation_time': None,
            'total_validation_time': 0.0
        }
        
        # Umbrales EAS mejorados
        self.thresholds = {
            'min_validation_score': 0.7,
            'max_risk_multiplier': 1.2,  # Reducido a 1.2x
            'min_signal_confidence': 0.6,
            'kill_switch_score': 0.3,
            'pause_line_block_score': 0.1  # Nuevo umbral
        }
        
        logger.info("🎯 Signal Validation Agent EAS Híbrido 2025 MEJORADO inicializado")
        logger.info("✅ Filtros EAS chinos integrados: Línea de Pausa + Prevención Duplicados")

    def _initialize_ia_client(self):
        """Inicializa cliente de IA según configuración"""
        try:
            api_key = self.config.get('api_keys', {}).get('anthropic')
            if api_key and api_key != "dummy_key":
                import anthropic
                self.ia_client = anthropic.Anthropic(api_key=api_key)
                logger.info("🤖 Cliente Anthropic inicializado")
            else:
                logger.warning("⚠️ API key no configurada - usando modo simulación")
                self.ia_client = None
        except Exception as e:
            logger.error(f"❌ Error inicializando cliente IA: {e}")
            self.ia_client = None

    async def initialize(self):
        """Inicialización del agente con integración HealthMonitor mejorada"""
        try:
            # Registrar callback en HealthMonitor
            health_monitor = get_health_monitor()
            health_monitor.register_health_callback(self._health_callback)
            
            logger.info("🚀 Signal Validation Agent MEJORADO inicializado con HealthMonitor")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando Signal Validation Agent: {e}")
            raise

    @with_guardrails(agent_context="signal_validation")
    async def validate_signal(self, 
                              signal_data: Dict[str, Any],
                              macro_bias: EnhancedMacroBias,
                              market_context: Dict[str, Any],
                              liquidity_analysis_data: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Valida señal con análisis completo EAS Híbrido 2025 MEJORADO
        
        Args:
            signal_data: Datos de la señal técnica
            macro_bias: Análisis macroeconómico
            market_context: Contexto de mercado
            liquidity_analysis_data: Resultado del análisis de liquidez
            
        Returns:
            Resultado de validación estructurado
        """
        start_time = time.time()
        self.metrics['total_validations'] += 1
        
        try:
            # 1. VERIFICACIÓN DE FILTROS EAS CHINOS (PRIMERO - DETERMINISTA)
            filter_check = await self._apply_eas_chinese_filters(signal_data, market_context)
            if not filter_check["allowed"]:
                logger.warning(f"🚫 Señal bloqueada por filtro EAS: {filter_check['reason']}")
                return self._create_filter_block_result(signal_data, filter_check['reason'])

            # 2. Verificar circuit breaker
            if not self.circuit_breaker.allow_request():
                logger.warning("🔒 Circuit breaker activado - usando validación local")
                return await self._local_validation_fallback(signal_data, macro_bias, market_context, liquidity_analysis_data)

            # 3. Verificar condiciones de kill switch macro
            if macro_bias.kill_switch:
                logger.warning("🚨 Kill switch macro activado - rechazando señal")
                self.metrics['kill_switch_activations'] += 1
                return self._create_kill_switch_result(signal_data, "macro_kill_switch")

            # 4. Ejecutar inferencias múltiples en paralelo
            inference_tasks = [
                self._execute_single_inference(signal_data, macro_bias, market_context, i)
                for i in range(self.num_inferences)
            ]
            
            # Ejecutar con timeout global optimizado
            results = await asyncio.wait_for(
                asyncio.gather(*inference_tasks, return_exceptions=True),
                timeout=self.max_tot_time
            )
            
            # Procesar resultados
            valid_results = self._process_inference_results(results)
            
            if not valid_results:
                logger.warning("⚠️ No hay inferencias válidas - usando fallback")
                return await self._local_validation_fallback(signal_data, macro_bias, market_context, liquidity_analysis_data)

            # 5. Calcular consenso
            consensus_result = await self._compute_consensus(valid_results, signal_data)
            
            # 6. Aplicar límites de riesgo EAS y ajuste de liquidez
            consensus_result = self._apply_risk_limits(consensus_result, macro_bias, liquidity_analysis_data)
            
            # 7. Registrar éxito
            self.circuit_breaker.record_success()
            self.metrics['successful_validations'] += 1
            
            # 8. Actualizar métricas
            processing_time = time.time() - start_time
            self._update_validation_metrics(consensus_result, processing_time)
            
            # 9. Enviar métricas a HealthMonitor
            await self._update_health_metrics(consensus_result)
            
            logger.info(
                f"✅ Validación completada: {consensus_result.final_decision.value} | "
                f"Score: {consensus_result.validation_score:.3f} | "
                f"Confianza: {consensus_result.confidence:.3f} | "
                f"Risk Multiplier: {consensus_result.risk_multiplier:.2f}",
                extra=asdict(consensus_result)
            )
            
            return consensus_result
            
        except asyncio.TimeoutError:
            logger.warning("⏰ Timeout global en validación de señal")
            self.metrics['timeout_validations'] += 1
            self.circuit_breaker.record_failure()
            return await self._local_validation_fallback(signal_data, macro_bias, market_context, liquidity_analysis_data)
            
        except Exception as e:
            logger.error(f"❌ Error en validación de señal: {e}")
            self.metrics['failed_validations'] += 1
            self.circuit_breaker.record_failure()
            return await self._local_validation_fallback(signal_data, macro_bias, market_context, liquidity_analysis_data)

    async def _apply_eas_chinese_filters(self, 
                                       signal_data: Dict[str, Any], 
                                       market_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aplica filtros deterministas del sistema EAS chino
        
        Returns:
            Dict con {allowed: bool, reason: str}
        """
        # 1. Filtro de Línea de Pausa
        candle_data = signal_data.get('current_candle', {})
        if candle_data:
            pause_line = self.long_shadow_filter.detect_pause_line(candle_data)
            if pause_line:
                signal_direction = "BUY" if "BULLISH" in signal_data.get('signal_type', '') else "SELL"
                
                # Bloquear órdenes en dirección contraria a la línea de pausa
                if (pause_line == "UPPER_PAUSE_LINE" and signal_direction == "BUY") or \
                   (pause_line == "LOWER_PAUSE_LINE" and signal_direction == "SELL"):
                    self.metrics['pause_line_blocks'] += 1
                    return {
                        "allowed": False,
                        "reason": f"Línea de Pausa {pause_line} detectada - bloqueando {signal_direction}"
                    }

        # 2. Prevención de Órdenes Duplicadas
        symbol = signal_data.get('symbol', 'XAUUSD')
        signal_type = signal_data.get('signal_type', '')
        order_type = "BUY" if "BULLISH" in signal_type else "SELL"
        
        if not self.duplicate_prevention.can_open_new_order(symbol, order_type):
            self.metrics['duplicate_order_blocks'] += 1
            return {
                "allowed": False,
                "reason": f"Orden duplicada bloqueada en misma vela para {symbol}"
            }

        return {"allowed": True, "reason": "Todos los filtros pasados"}

    async def _execute_single_inference(self, 
                                       signal_data: Dict[str, Any],
                                       macro_bias: EnhancedMacroBias,
                                       market_context: Dict[str, Any],
                                       inference_id: int) -> InferenceResult:
        """Ejecuta una inferencia individual con timeout optimizado"""
        start_time = time.time()
        
        try:
            # Construir prompt específico para EAS MEJORADO
            prompt = self._build_enhanced_validation_prompt(signal_data, macro_bias, market_context)
            
            # Ejecutar con timeout individual optimizado
            if self.ia_client:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.ia_client.messages.create,
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=1024,
                        temperature=self.temperature,
                        system=self.system_prompt,
                        messages=[{"role": "user", "content": prompt}]
                    ),
                    timeout=self.per_inference_timeout
                )
                content = response.content[0].text.strip()
            else:
                # Simulación mejorada para desarrollo
                content = self._simulate_ia_response(signal_data, macro_bias)
                await asyncio.sleep(0.05)  # Simulación más rápida
            
            processing_time = time.time() - start_time
            
            # Parsear respuesta
            result_data = self._parse_inference_response(content, inference_id)
            
            # Aplicar guardrails de validación mejorados
            guardrail_checks = self._perform_enhanced_guardrail_checks(result_data, signal_data)
            
            # Verificar línea de pausa en esta inferencia
            candle_data = signal_data.get('current_candle', {})
            pause_line_detected = self.long_shadow_filter.detect_pause_line(candle_data) if candle_data else None
            
            return InferenceResult(
                score=result_data.get('validation_score', 0.0),
                classification=result_data.get('classification', 'NEUTRAL'),
                reasoning=result_data.get('reasoning', ''),
                recommendation=ValidationDecision(result_data.get('recommendation', 'DEFER')),
                risk_multiplier=result_data.get('risk_multiplier', 1.0),
                reasoning_step_by_step=result_data.get('reasoning_step_by_step', ''),
                confidence=result_data.get('confidence', 0.0),
                processing_time=processing_time,
                signal_type=SignalType(signal_data.get('signal_type', 'BOS_RETEST_BULLISH')),
                validation_metrics=result_data.get('validation_metrics', {}),
                guardrail_checks=guardrail_checks,
                pause_line_detected=pause_line_detected
            )
            
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.warning(f"⏰ Timeout en inferencia {inference_id}: {elapsed:.2f}s")
            raise
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ Error en inferencia {inference_id}: {e}")
            raise

    async def _compute_consensus(self, 
                                 inferences: List[InferenceResult],
                                 signal_data: Dict[str, Any]) -> ValidationResult:
        """Calcula consenso mejorado a partir de múltiples inferencias"""
        if not inferences:
            raise ValueError("No valid inferences to compute consensus.")

        # Calcular consenso de decisiones
        decisions = [inf.recommendation for inf in inferences]
        decision_counts = {}
        for decision in decisions:
            decision_counts[decision] = decision_counts.get(decision, 0) + 1
        
        consensus_decision = max(decision_counts, key=decision_counts.get)
        consensus_votes = decision_counts[consensus_decision]
        consensus_score = consensus_votes / len(inferences)
        
        # Determinar nivel de consenso
        if consensus_score >= 0.9:
            consensus_level = ConsensusLevel.VERY_HIGH
        elif consensus_score >= 0.8:
            consensus_level = ConsensusLevel.HIGH
        elif consensus_score >= 0.65:
            consensus_level = ConsensusLevel.MEDIUM
        elif consensus_score >= 0.5:
            consensus_level = ConsensusLevel.LOW
        else:
            consensus_level = ConsensusLevel.VERY_LOW
        
        # Calcular métricas agregadas
        avg_score = statistics.mean([inf.score for inf in inferences])
        avg_risk_multiplier = statistics.mean([inf.risk_multiplier for inf in inferences])
        avg_confidence = statistics.mean([inf.confidence for inf in inferences])
        total_processing_time = sum([inf.processing_time for inf in inferences])
        
        # Verificar líneas de pausa en inferencias
        pause_line_detections = [inf.pause_line_detected for inf in inferences if inf.pause_line_detected]
        pause_line_block = len(pause_line_detections) > len(inferences) * 0.6  # 60% de detecciones
        
        # Sintetizar reasoning steps
        reasoning_steps = []
        for i, inf in enumerate(inferences):
            steps = inf.reasoning_step_by_step.split('\n')
            reasoning_steps.extend([f"Inferencia {i+1}: {step}" for step in steps if step.strip()])
        
        # Verificar violaciones de guardrails
        guardrail_violations = []
        for inf in inferences:
            for check, passed in inf.guardrail_checks.items():
                if not passed:
                    guardrail_violations.append(f"{check}_in_inference_{inferences.index(inf)}")
        
        # Determinar decisión final basada en consenso, guardrails y línea de pausa
        final_decision = consensus_decision
        if pause_line_block:
            final_decision = ValidationDecision.PAUSE_LINE_BLOCK
            guardrail_violations.append("pause_line_consensus_block")
            logger.warning("🚫 Bloqueo por consenso de línea de pausa")
        elif guardrail_violations:
            final_decision = ValidationDecision.REJECT
            logger.warning(f"🚫 Guardrail violations: {guardrail_violations}")
        
        return ValidationResult(
            validation_score=consensus_score,
            risk_multiplier=avg_risk_multiplier,
            reasoning_steps=reasoning_steps[:10],
            final_decision=final_decision,
            signal_type=inferences[0].signal_type,
            confidence=avg_confidence,
            consensus_level=consensus_level,
            num_inferences=len(inferences),
            processing_time=total_processing_time,
            fallback_used=False,
            kill_switch_triggered=False,
            guardrail_violations=guardrail_violations,
            timestamp=datetime.now(),
            metadata={
                "consensus_breakdown": {k.value: v for k, v in decision_counts.items()},
                "average_scores": {
                    "validation_score": avg_score,
                    "confidence": avg_confidence,
                    "risk_multiplier": avg_risk_multiplier
                },
                "pause_line_detections": pause_line_detections,
                "signal_metadata": signal_data.get('metadata', {})
            },
            pause_line_block=pause_line_block
        )

    def _perform_enhanced_guardrail_checks(self, result_data: Dict[str, Any], signal_data: Dict[str, Any]) -> Dict[str, bool]:
        """Realiza verificaciones de seguridad mejoradas"""
        checks = {
            "risk_multiplier_within_limits": True,
            "validation_score_reasonable": True,
            "decision_supported": True,
            "signal_type_valid": True,
            "pause_line_respected": True
        }
        
        risk_multiplier = result_data.get('risk_multiplier', 1.0)
        if not (0.5 <= risk_multiplier <= 1.5):
            checks["risk_multiplier_within_limits"] = False
            logger.warning(f"🚫 Risk multiplier fuera de límites: {risk_multiplier}")
        
        validation_score = result_data.get('validation_score', 0.0)
        if not (0.0 <= validation_score <= 1.0):
            checks["validation_score_reasonable"] = False
        
        reasoning = result_data.get('reasoning', '')
        recommendation = result_data.get('recommendation', '')
        if not reasoning or len(reasoning) < 10:
            checks["decision_supported"] = False
        
        signal_type = signal_data.get('signal_type')
        try:
            SignalType(signal_type)
        except ValueError:
            checks["signal_type_valid"] = False
        
        return checks

    def _build_enhanced_validation_prompt(self, 
                                         signal_data: Dict[str, Any],
                                         macro_bias: EnhancedMacroBias,
                                         market_context: Dict[str, Any]) -> str:
        """Construye prompt mejorado para validación EAS"""
        signal_type = signal_data.get('signal_type', 'UNKNOWN')
        technical_indicators = signal_data.get('technical_indicators', {})
        price_action = signal_data.get('price_action', {})
        candle_data = signal_data.get('current_candle', {})
        
        pause_line_info = ""
        if candle_data:
            pause_line = self.long_shadow_filter.detect_pause_line(candle_data)
            if pause_line:
                pause_line_info = f"🚫 ALERTA: Línea de Pausa {pause_line} detectada - considerar rechazo"

        prompt = f"""
        Eres el Enhanced Consistency Engine del sistema EAS Híbrido 2025.

        {pause_line_info}

        VALIDA la siguiente señal de trading para XAUUSD con disciplina rígida:

        SEÑAL TÉCNICA:
        - Tipo: {signal_type}
        - Precio: {signal_data.get('current_price', 'N/A')}
        - EMA Trend: {technical_indicators.get('ema_trend', 'N/A')}
        - ATR: {technical_indicators.get('atr', 'N/A')}
        - RSI: {technical_indicators.get('rsi', 'N/A')}
        - Vela Actual: {candle_data}

        CONTEXTO MACRO:
        - VIX: {getattr(macro_bias, 'vix', 'N/A')}
        - DXY: {getattr(macro_bias, 'dxy', 'N/A')} 
        - Real Yields: {getattr(macro_bias, 'real_yields', 'N/A')}%
        - Gold Bias: {getattr(macro_bias, 'gold_bias', 'N/A').value if hasattr(macro_bias, 'gold_bias') else 'N/A'}
        - Risk Multiplier: {getattr(macro_bias, 'risk_multiplier', 'N/A')}

        REGLAS EAS INMUTABLES:
        - Riesgo máximo: 0.3% por operación
        - Solo sesión NY (13:00-17:00 GMT)
        - Ratio R/R fijo 1:2
        - Kill Switch: 2 pérdidas consecutivas
        - LÍNEA DE PAUSA: Rechazar si sombra >= 1.5x cuerpo y cuerpo <80pips

        Responde en formato JSON con:
        - validation_score (0.0-1.0)
        - classification (BULLISH/BEARISH/NEUTRAL)
        - recommendation (APPROVE/REJECT/DEFER)
        - risk_multiplier (1.0-1.5)
        - reasoning (análisis conciso)
        - reasoning_step_by_step (pasos detallados)
        - confidence (0.0-1.0)
        - validation_metrics (dict con métricas específicas)
        """
        return prompt

    def _create_filter_block_result(self, signal_data: Dict[str, Any], reason: str) -> ValidationResult:
        """Crea resultado de bloqueo por filtro EAS"""
        self.metrics['guardrail_violations'] += 1
        
        return ValidationResult(
            validation_score=0.0,
            risk_multiplier=0.0,
            reasoning_steps=[f"Filtro EAS activado: {reason}"],
            final_decision=ValidationDecision.REJECT,
            signal_type=SignalType(signal_data.get('signal_type', 'BOS_RETEST_BULLISH')),
            confidence=0.0,
            consensus_level=ConsensusLevel.VERY_LOW,
            num_inferences=0,
            processing_time=0.0,
            fallback_used=False,
            kill_switch_triggered=False,
            guardrail_violations=[reason],
            timestamp=datetime.now(),
            metadata={"filter_block_reason": reason},
            pause_line_block="pause" in reason.lower()
        )

    async def _local_validation_fallback(self,
                                         signal_data: Dict[str, Any],
                                         macro_bias: EnhancedMacroBias,
                                         market_context: Dict[str, Any],
                                         liquidity_analysis_data: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Fallback de validación local mejorado"""
        try:
            self.metrics['fallback_activations'] += 1
            self.metrics['local_validations'] += 1
            
            filter_check = await self._apply_eas_chinese_filters(signal_data, market_context)
            if not filter_check["allowed"]:
                return self._create_filter_block_result(signal_data, filter_check['reason'])

            technical_indicators = signal_data.get('technical_indicators', {})
            price_action = signal_data.get('price_action', {})
            market_structure = signal_data.get('market_structure', {})
            
            validation_score = self._calculate_local_validation_score(
                technical_indicators, price_action, market_structure, macro_bias
            )
            
            if validation_score >= 0.8:
                decision = ValidationDecision.APPROVE
                risk_multiplier = 1.2
                confidence = 0.85
            elif validation_score >= 0.6:
                decision = ValidationDecision.APPROVE
                risk_multiplier = 1.0
                confidence = 0.70
            elif validation_score >= 0.4:
                decision = ValidationDecision.DEFER
                risk_multiplier = 0.8
                confidence = 0.50
            else:
                decision = ValidationDecision.REJECT
                risk_multiplier = 0.5
                confidence = 0.30
                
            result = ValidationResult(
                validation_score=validation_score,
                risk_multiplier=risk_multiplier,
                reasoning_steps=[], 
                final_decision=decision,
                signal_type=SignalType(signal_data.get('signal_type', 'BOS_RETEST_BULLISH')),
                confidence=confidence,
                consensus_level=ConsensusLevel.LOW,
                num_inferences=1,
                processing_time=0.01,
                fallback_used=True,
                kill_switch_triggered=False,
                guardrail_violations=[],
                timestamp=datetime.now(),
                metadata={
                    "fallback_reason": "local_validation",
                    "technical_indicators": technical_indicators,
                    "validation_score_components": self._get_validation_score_components(
                        technical_indicators, price_action, market_structure
                    )
                }
            )
            
            result = self._apply_risk_limits(result, macro_bias, liquidity_analysis_data)
            
            reasoning_steps = [
                "1. Validación local activada (fallback)",
                "2. Análisis de indicadores técnicos",
                "3. Evaluación de estructura de mercado", 
                "4. Cálculo de score de validación",
                f"5. Decisión: {result.final_decision.value} (score: {validation_score:.3f})"
            ]
            
            if liquidity_analysis_data and liquidity_analysis_data.get('decision'):
                reasoning_steps.append(f"6. Análisis de liquidez: {liquidity_analysis_data['decision']}")
            result.reasoning_steps = reasoning_steps
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en validación local mejorada: {e}")
            return self._create_fallback_result(signal_data, "local_validation_error")

    def _calculate_local_validation_score(self,
                                         technical_indicators: Dict[str, Any],
                                         price_action: Dict[str, Any],
                                         market_structure: Dict[str, Any],
                                         macro_bias: Optional[EnhancedMacroBias]) -> float:
        """Calcula score de validación local mejorado"""
        score_components = []
        
        # Componente técnico (40%)
        tech_score = 0.0
        if technical_indicators:
            ema_trend = technical_indicators.get('ema_trend', 0)
            if abs(ema_trend) > 0.5:
                tech_score += 0.3
            elif abs(ema_trend) > 0.2:
                tech_score += 0.2
                
            atr = technical_indicators.get('atr', 0)
            if 1.0 < atr < 5.0:
                tech_score += 0.3
            elif atr <= 1.0:
                tech_score += 0.1
                
            rsi = technical_indicators.get('rsi', 50)
            if 30 < rsi < 70:
                tech_score += 0.2
                
            volume_ratio = technical_indicators.get('volume_ratio', 1.0)
            if volume_ratio > 1.2:
                tech_score += 0.2
                
        score_components.append(tech_score * 0.4)
        
        # Componente de price action (30%)
        price_score = 0.0
        if price_action:
            sr_test = price_action.get('support_resistance_test', False)
            if sr_test:
                price_score += 0.4
                
            candle_pattern = price_action.get('candle_pattern', '')
            strong_patterns = ['BOS_RETEST', 'ORDERBLOCK_TOUCH']
            if candle_pattern in strong_patterns:
                price_score += 0.3
            elif candle_pattern:
                price_score += 0.1
                
            structure = market_structure.get('current_structure', '')
            if structure in ['BULLISH', 'BEARISH']:
                price_score += 0.3
                
        score_components.append(price_score * 0.3)
        
        # Componente macro (30%)
        macro_score = 0.0
        if macro_bias:
            macro_normalized = (macro_bias.bias_score - 1) / 9.0
            macro_score = macro_normalized * macro_bias.confidence
            
        score_components.append(macro_score * 0.3)
        
        final_score = sum(score_components)
        return max(0.0, min(1.0, final_score))

    def _apply_risk_limits(self, 
                           result: ValidationResult, 
                           macro_bias: EnhancedMacroBias, 
                           liquidity_analysis_data: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Aplica límites de riesgo EAS mejorados"""
        # Ajuste por análisis de liquidez
        if liquidity_analysis_data and liquidity_analysis_data.get('decision'):
            try:
                liquidity_decision = LiquidityDecision(liquidity_analysis_data['decision'])
                if liquidity_decision == LiquidityDecision.OPTIMAL:
                    result.risk_multiplier *= 1.2
                    result.reasoning_steps.append("Ajuste Liquidez: Óptima (+20% Risk Multiplier)")
                elif liquidity_decision == LiquidityDecision.NORMAL:
                    result.risk_multiplier *= 1.0
                elif liquidity_decision == LiquidityDecision.LOW:
                    result.risk_multiplier *= 0.7
                    result.reasoning_steps.append("Ajuste Liquidez: Baja (-30% Risk Multiplier)")
                elif liquidity_decision == LiquidityDecision.AVOID:
                    result.final_decision = ValidationDecision.REJECT
                    result.risk_multiplier = 0.0 
                    result.kill_switch_triggered = True
                    result.reasoning_steps.append("🚫 Liquidez AVOID - Señal RECHAZADA")
            except ValueError:
                logger.error(f"❌ Decisión de liquidez desconocida: {liquidity_analysis_data['decision']}")
            except Exception as e:
                logger.error(f"❌ Error aplicando ajuste de liquidez: {e}")
                
        # Aplicar límites de riesgo
        result.risk_multiplier = min(result.risk_multiplier, self.thresholds['max_risk_multiplier'])
        
        # Considerar multiplicador de riesgo macro
        if macro_bias and hasattr(macro_bias, 'risk_multiplier'):
            result.risk_multiplier = min(result.risk_multiplier, macro_bias.risk_multiplier)
            
        # Verificar confianza mínima
        if (result.final_decision != ValidationDecision.REJECT and 
            result.confidence < self.min_confidence):
            result.final_decision = ValidationDecision.DEFER
            result.reasoning_steps.append(
                f"Ajuste Confianza: Confianza ({result.confidence:.3f}) < Mínimo ({self.min_confidence}). Decisión DEFER."
            )
            
        # Activar kill switch si el score es muy bajo
        if (result.final_decision not in [ValidationDecision.REJECT, ValidationDecision.KILL_SWITCH] and
            result.validation_score < self.thresholds['kill_switch_score']):
            result.final_decision = ValidationDecision.KILL_SWITCH
            result.kill_switch_triggered = True
            self.metrics['kill_switch_activations'] += 1
            result.reasoning_steps.append(
                f"Kill Switch: Validation Score ({result.validation_score:.3f}) < Mínimo ({self.thresholds['kill_switch_score']})"
            )
            
        return result

    def _parse_inference_response(self, content: str, inference_id: int) -> Dict[str, Any]:
        """Parsea respuesta de inferencia con manejo robusto de errores"""
        try:
            if content.strip().startswith('{'):
                return json.loads(content)
                
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
                
            return self._parse_fallback_response(content)
            
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Error parseando JSON en inferencia {inference_id}: {e}")
            return self._parse_fallback_response(content)
        except Exception as e:
            logger.error(f"❌ Error inesperado parseando respuesta: {e}")
            return self._get_default_response()

    def _parse_fallback_response(self, content: str) -> Dict[str, Any]:
        """Parsea respuesta de fallback cuando el JSON es inválido"""
        score = 0.5
        if "APPROVE" in content.upper():
            recommendation = "APPROVE"
            score = 0.8
        elif "REJECT" in content.upper():
            recommendation = "REJECT" 
            score = 0.2
        else:
            recommendation = "DEFER"
            score = 0.5
            
        return {
            "validation_score": score,
            "classification": "NEUTRAL",
            "recommendation": recommendation,
            "risk_multiplier": 1.0,
            "reasoning": "Fallback parsing",
            "reasoning_step_by_step": "1. Fallback activation\n2. Basic text analysis\n3. Default scoring",
            "confidence": 0.3,
            "validation_metrics": {"fallback_used": True}
        }

    def _get_default_response(self) -> Dict[str, Any]:
        """Respuesta por defecto para casos de error crítico"""
        return {
            "validation_score": 0.0,
            "classification": "NEUTRAL",
            "recommendation": "DEFER",
            "risk_multiplier": 1.0,
            "reasoning": "Default fallback",
            "reasoning_step_by_step": "1. Default response\n2. No data available",
            "confidence": 0.0,
            "validation_metrics": {"default": True}
        }

    def _simulate_ia_response(self, signal_data: Dict[str, Any], macro_bias: EnhancedMacroBias) -> str:
        """Simula respuesta de IA para desarrollo"""
        signal_type = signal_data.get('signal_type', 'BOS_RETEST_BULLISH')
        price = signal_data.get('current_price', 3875.0)
        
        if "BULLISH" in signal_type:
            score = 0.8
            classification = "BULLISH"
            recommendation = "APPROVE"
        elif "BEARISH" in signal_type:
            score = 0.7
            classification = "BEARISH" 
            recommendation = "APPROVE"
        else:
            score = 0.4
            classification = "NEUTRAL"
            recommendation = "DEFER"
            
        # Ajustar score según bias macro
        if macro_bias and hasattr(macro_bias, 'gold_bias'):
            if macro_bias.gold_bias.value == "BULLISH":
                score += 0.1
            elif macro_bias.gold_bias.value == "BEARISH":
                score -= 0.1
                
        score = max(0.0, min(1.0, score))
        
        return json.dumps({
            "validation_score": score,
            "classification": classification,
            "recommendation": recommendation,
            "risk_multiplier": 1.1 + (score - 0.5) * 0.5,
            "reasoning": f"Simulación: Señal {signal_type} con score ajustado por macro bias.",
            "reasoning_step_by_step": "1. Simulación de IA.\n2. Inferencia positiva.\n3. Ajuste de riesgo estándar.",
            "confidence": min(0.95, 0.5 + score * 0.5),
            "validation_metrics": {"simulated": True}
        })

    def _build_eas_system_prompt(self) -> str:
        """Construye prompt del sistema EAS mejorado"""
        return """
        Eres el Enhanced Consistency Engine del sistema EAS Híbrido 2025.
        Tu función es validar señales de trading con disciplina extrema usando:
        1. ANÁLISIS TÉCNICO: EMA, ATR, RSI, estructura de mercado
        2. CONTEXTO MACRO: VIX, DXY, yields reales, sesgo oro
        3. REGLAS EAS: Riesgo 0.3%, RR 1:2, solo sesión NY
        Evalúa cada señal críticamente y proporciona:
        - Score de validación (0.0-1.0)
        - Clasificación (BULLISH/BEARISH/NEUTRAL)
        - Recomendación (APPROVE/REJECT/DEFER)
        - Multiplicador de riesgo (0.5-1.5)
        - Razonamiento paso a paso
        Responde SOLO en formato JSON válido.
        """

    def _build_eas_few_shot_examples(self) -> List[Dict[str, Any]]:
        """Ejemplos few-shot para EAS mejorado"""
        return [
            {
                "input": {
                    "signal_type": "BOS_RETEST_BULLISH",
                    "technical_indicators": {"ema_trend": 0.8, "atr": 2.5, "rsi": 65},
                    "macro_context": {"vix": 15.5, "dxy": 103.2, "real_yields": 2.1}
                },
                "output": {
                    "validation_score": 0.85,
                    "classification": "BULLISH",
                    "recommendation": "APPROVE",
                    "risk_multiplier": 1.3,
                    "reasoning": "Fuerte alineación técnica con bias macro positivo",
                    "confidence": 0.88
                }
            }
        ]

    def _process_inference_results(self, results: List[Any]) -> List[InferenceResult]:
        """Procesa resultados de inferencia filtrando excepciones"""
        valid_results = []
        for res in results:
            if isinstance(res, InferenceResult):
                valid_results.append(res)
            elif isinstance(res, Exception):
                logger.error(f"Inferencia fallida con excepción: {res}")
        return valid_results

    def _update_validation_metrics(self, result: ValidationResult, processing_time: float):
        """Actualiza métricas de validación"""
        self.metrics['total_validation_time'] += processing_time
        self.metrics['average_processing_time'] = (
            self.metrics['total_validation_time'] / self.metrics['total_validations']
        )
        
        decision = result.final_decision.value
        self.metrics['decision_distribution'][decision] = (
            self.metrics['decision_distribution'].get(decision, 0) + 1
        )
        
        total_score = (self.metrics['average_validation_score'] * 
                      (self.metrics['total_validations'] - 1) + result.validation_score)
        self.metrics['average_validation_score'] = total_score / self.metrics['total_validations']
        
        self.metrics['last_validation_time'] = datetime.now()
        
        if result.pause_line_block:
            self.metrics['pause_line_blocks'] += 1

    async def _update_health_metrics(self, result: ValidationResult):
        """Actualiza métricas en HealthMonitor"""
        try:
            health_monitor = get_health_monitor()
            await health_monitor.update_agent_metrics(
                "signal_validation_agent",
                {
                    "validation_score": result.validation_score,
                    "confidence": result.confidence,
                    "risk_multiplier": result.risk_multiplier,
                    "processing_time": result.processing_time,
                    "final_decision": result.final_decision.value,
                    "consensus_level": result.consensus_level.value,
                    "pause_line_block": result.pause_line_block
                }
            )
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron enviar métricas a HealthMonitor: {e}")

    def _get_validation_score_components(self, 
                                       technical_indicators: Dict[str, Any], 
                                       price_action: Dict[str, Any], 
                                       market_structure: Dict[str, Any]) -> Dict[str, float]:
        """Obtiene componentes del score de validación para análisis"""
        components = {}
        if technical_indicators:
            components['ema_alignment'] = abs(technical_indicators.get('ema_trend', 0))
            components['atr_volatility'] = technical_indicators.get('atr', 0)
            components['rsi_momentum'] = technical_indicators.get('rsi', 50) / 100.0
            components['volume_ratio'] = technical_indicators.get('volume_ratio', 1.0)
            
        if price_action:
            components['sr_test'] = 1.0 if price_action.get('support_resistance_test') else 0.0
            components['candle_pattern'] = 0.8 if price_action.get('candle_pattern') else 0.2
            
        if market_structure:
            components['market_structure'] = 1.0 if market_structure.get('current_structure') else 0.5
            
        return components

    def _create_kill_switch_result(self, signal_data: Dict[str, Any], reason: str) -> ValidationResult:
        """Crea resultado de kill switch"""
        return ValidationResult(
            validation_score=0.0,
            risk_multiplier=0.0,
            reasoning_steps=[f"Kill Switch activado: {reason}"],
            final_decision=ValidationDecision.KILL_SWITCH,
            signal_type=SignalType(signal_data.get('signal_type', 'BOS_RETEST_BULLISH')),
            confidence=0.0,
            consensus_level=ConsensusLevel.VERY_LOW,
            num_inferences=0,
            processing_time=0.0,
            fallback_used=False,
            kill_switch_triggered=True,
            guardrail_violations=[reason],
            timestamp=datetime.now(),
            metadata={"kill_switch_reason": reason}
        )

    def _create_fallback_result(self, signal_data: Dict[str, Any], reason: str) -> ValidationResult:
        """Crea resultado de fallback por error crítico"""
        return ValidationResult(
            validation_score=0.0,
            risk_multiplier=0.0,
            reasoning_steps=[f"Error crítico, fallback a REJECT: {reason}"],
            final_decision=ValidationDecision.REJECT,
            signal_type=SignalType(signal_data.get('signal_type', 'BOS_RETEST_BULLISH')),
            confidence=0.0,
            consensus_level=ConsensusLevel.VERY_LOW,
            num_inferences=0,
            processing_time=0.0,
            fallback_used=True,
            kill_switch_triggered=False,
            guardrail_violations=[],
            timestamp=datetime.now(),
            metadata={"fallback_reason": reason}
        )

    def _health_callback(self) -> Dict[str, Any]:
        """Callback para HealthMonitor"""
        return {
            "status": "OK" if self.circuit_breaker.is_open() else "DEGRADED",
            "metrics": self.metrics,
            "circuit_breaker_state": self.circuit_breaker.get_state(),
            "last_validation": self.metrics.get('last_validation_time')
        }

    async def process_signals(self, 
                              signals: List[Dict[str, Any]], 
                              macro_bias: EnhancedMacroBias, 
                              market_context: Dict[str, Any],
                              liquidity_analysis_data: Optional[Dict[str, Any]] = None) -> List[Tuple[Dict[str, Any], ValidationResult]]:
        """Procesa múltiples señales en lote"""
        validated_signals = []
        for signal in signals:
            logger.info(f"🔍 Validando señal: {signal.get('signal_id', 'N/A')} ({signal.get('symbol', 'N/A')})")
            validation_result = await self.validate_signal(
                signal, 
                macro_bias, 
                market_context,
                liquidity_analysis_data
            )
            validated_signals.append((signal, validation_result))
            
            log_extra = {
                "signal_id": signal.get('signal_id'),
                "validation_score": validation_result.validation_score,
                "risk_multiplier": validation_result.risk_multiplier,
                "pause_line_block": validation_result.pause_line_block
            }
            
            logger.info(
                f"📊 Resultado validación {signal.get('signal_id', 'N/A')}: "
                f"Decisión: {validation_result.final_decision.value} | "
                f"Score: {validation_result.validation_score:.3f} | "
                f"Filtro Pausa: {'✅' if not validation_result.pause_line_block else '🚫'}",
                extra=log_extra
            )
            
        return validated_signals

    async def shutdown(self):
        """Cierre ordenado del agente"""
        logger.info("🛑 Signal Validation Agent MEJORADO shutdown complete")

def create_signal_validation_agent(config: Dict[str, Any]) -> SignalValidationAgent:
    """Factory function para crear el agente"""
    return SignalValidationAgent(config)

# Ejemplo de uso
async def main():
    """Función principal de ejemplo"""
    config = {
        "api_keys": {
            "anthropic": "dummy_key"
        },
        "signal_validation_agent": {
            "validation": {
                "num_inferences": 3,
                "temperature": 0.3,
                "consensus_threshold": 0.75,
                "min_confidence": 0.7
            }
        }
    }
    
    agent = create_signal_validation_agent(config)
    await agent.initialize()
    
    # Simular señal
    signal_data = {
        "signal_id": "test_001",
        "symbol": "XAUUSD",
        "signal_type": "BOS_RETEST_BULLISH",
        "current_price": 2350.5,
        "current_candle": {
            "open": 2349.0,
            "high": 2355.0,
            "low": 2348.0,
            "close": 2350.5
        },
        "technical_indicators": {
            "ema_trend": 0.7,
            "atr": 3.2,
            "rsi": 62,
            "volume_ratio": 1.3
        },
        "price_action": {
            "support_resistance_test": True,
            "candle_pattern": "BOS_RETEST"
        },
        "market_structure": {
            "current_structure": "BULLISH"
        }
    }
    
    macro_bias = EnhancedMacroBias(
        vix=14.2,
        dxy=102.8,
        real_yields=1.8,
        gold_bias=GoldBias.BULLISH,
        risk_multiplier=1.1,
        bias_score=7.5,
        confidence=0.85,
        kill_switch=False
    )
    
    market_context = {"session": "NY", "time": "14:30"}
    
    result = await agent.validate_signal(signal_data, macro_bias, market_context)
    print(f"\n✅ Resultado final: {result.final_decision.value}")
    print(f"📊 Score: {result.validation_score:.3f}")
    print(f"🛡️  Risk Multiplier: {result.risk_multiplier:.2f}")
    print(f"🧠 Confianza: {result.confidence:.3f}")
    print(f"⏱️  Tiempo: {result.processing_time:.3f}s")
    if result.pause_line_block:
        print("🚫 Bloqueado por línea de pausa")
    
    await agent.shutdown()

if __name__ == "__main__":
    asyncio.run(main())