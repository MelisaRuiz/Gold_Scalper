#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Liquidity Analysis Agent v3.1 - EAS Híbrido 2025 Integration
Agente especializado en análisis de liquidez L2, imbalance y condiciones de mercado
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

# Importaciones de la nueva arquitectura
from infrastructure.structured_logger import StructuredLogger
from infrastructure.health_monitor import get_health_monitor
from infrastructure.circuit_breaker import CircuitBreaker
from infrastructure.guardrails import with_guardrails
from data.market_data_collector import EnhancedGoldDataCollector

logger = StructuredLogger("HECTAGold.LiquidityAnalysisAgent")

class LiquidityRegime(Enum):
    """Regímenes de liquidez para EAS"""
    HIGH_LIQUIDITY = "HIGH_LIQUIDITY"
    NORMAL_LIQUIDITY = "NORMAL_LIQUIDITY"
    LOW_LIQUIDITY = "LOW_LIQUIDITY"
    CRITICAL_LIQUIDITY = "CRITICAL_LIQUIDITY"

class ImbalanceDirection(Enum):
    """Direcciones de imbalance del order book"""
    STRONG_BID_IMBALANCE = "STRONG_BID_IMBALANCE"
    MODERATE_BID_IMBALANCE = "MODERATE_BID_IMBALANCE"
    BALANCED = "BALANCED"
    MODERATE_ASK_IMBALANCE = "MODERATE_ASK_IMBALANCE"
    STRONG_ASK_IMBALANCE = "STRONG_ASK_IMBALANCE"

class LiquidityDecision(Enum):
    """Decisiones de liquidez para EAS"""
    OPTIMAL = "OPTIMAL"
    ACCEPTABLE = "ACCEPTABLE"
    SUBOPTIMAL = "SUBOPTIMAL"
    AVOID = "AVOID"
    KILL_SWITCH = "KILL_SWITCH"

@dataclass
class OrderBookAnalysis:
    """Análisis detallado del order book L2"""
    symbol: str
    timestamp: datetime
    best_bid: float
    best_ask: float
    spread: float
    total_bid_size: float
    total_ask_size: float
    imbalance: float
    imbalance_direction: ImbalanceDirection
    depth_quality: float
    liquidity_zones: List[Dict[str, Any]]
    market_depth: Dict[str, float]
    order_book_quality: float

@dataclass
class LiquidityAnalysisResult:
    """Resultado completo del análisis de liquidez EAS"""
    liquidity_score: float
    liquidity_regime: LiquidityRegime
    imbalance_direction: ImbalanceDirection
    decision: LiquidityDecision
    risk_multiplier: float
    confidence: float
    analysis_metrics: Dict[str, float]
    reasoning_steps: List[str]
    order_book_snapshot: OrderBookAnalysis
    processing_time: float
    timestamp: datetime
    guardrail_violations: List[str]
    metadata: Dict[str, Any]

class LiquidityAnalysisAgent:
    """
    Agente especializado en análisis de liquidez para EAS Híbrido 2025
    Integrado con Market Data Collector y HealthMonitor
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el agente de análisis de liquidez
        
        Args:
            config: Configuración del sistema EAS
        """
        self.config = config
        self.agent_config = config.get('liquidity_agent', {})
        
        # Umbrales EAS para análisis de liquidez
        self.thresholds = {
            'min_liquidity_score': 0.6,
            'max_spread_ratio': 0.002,  # 0.2%
            'min_order_book_quality': 0.7,
            'imbalance_threshold_strong': 0.7,
            'imbalance_threshold_moderate': 0.3,
            'kill_switch_spread': 0.005,  # 0.5%
            'min_depth_quality': 0.5
        }
        
        # Circuit breaker para protección
        self.circuit_breaker = CircuitBreaker(
            max_failures=3,
            reset_timeout=300
        )
        
        # Referencia al market data collector
        self.market_data_collector = None
        
        # Histórico para análisis de tendencias
        self.historical_analysis = {
            'liquidity_scores': [],
            'imbalances': [],
            'spreads': [],
            'order_book_quality': []
        }
        self.max_history_size = 1000
        
        # Métricas para HealthMonitor
        self.metrics = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'average_processing_time': 0.0,
            'liquidity_regime_distribution': {},
            'imbalance_distribution': {},
            'kill_switch_activations': 0,
            'guardrail_violations': 0,
            'last_analysis_time': None,
            'total_processing_time': 0.0
        }
        
        # Configuración de análisis
        self.analysis_config = {
            'depth_levels': 5,
            'volume_threshold': 1000,
            'refresh_interval': 2,  # segundos
            'quality_calculation_window': 20
        }
        
        logger.info("🎯 Liquidity Analysis Agent EAS Híbrido 2025 inicializado")

    async def initialize(self, market_data_collector: EnhancedGoldDataCollector):
        """
        Inicializa el agente con dependencias
        
        Args:
            market_data_collector: Colector de datos de mercado
        """
        try:
            self.market_data_collector = market_data_collector
            
            # Verificar que el market data collector esté inicializado
            if not hasattr(self.market_data_collector, 'get_order_book_imbalance'):
                logger.error("❌ Market Data Collector no tiene método get_order_book_imbalance")
                raise AttributeError("Market Data Collector incompleto")
            
            # Registrar callback en HealthMonitor
            health_monitor = get_health_monitor()
            health_monitor.register_health_callback(self._health_callback)
            
            logger.info("🚀 Liquidity Analysis Agent inicializado con integración HealthMonitor")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando Liquidity Analysis Agent: {e}")
            raise

    @with_guardrails(agent_context="liquidity_analysis")
    async def analyze_liquidity_conditions(self, 
                                         symbol: str = "XAUUSD",
                                         signal_context: Optional[Dict[str, Any]] = None) -> LiquidityAnalysisResult:
        """
        Análisis completo de condiciones de liquidez para EAS
        
        Args:
            symbol: Símbolo a analizar
            signal_context: Contexto de la señal (opcional)
            
        Returns:
            Resultado del análisis de liquidez
        """
        start_time = time.time()
        self.metrics['total_analyses'] += 1
        
        try:
            # Verificar circuit breaker
            if not self.circuit_breaker.allow_request():
                logger.warning("🔒 Circuit breaker activado - usando análisis conservador")
                return await self._conservative_fallback_analysis(symbol)

            # Obtener datos del order book L2
            order_book_analysis = await self._analyze_order_book(symbol)
            if not order_book_analysis:
                logger.error("❌ No se pudo obtener análisis del order book")
                return await self._conservative_fallback_analysis(symbol)

            # Realizar análisis completo de liquidez
            analysis_result = await self._perform_comprehensive_analysis(
                order_book_analysis, symbol, signal_context
            )

            # Aplicar guardrails de seguridad
            analysis_result = self._apply_liquidity_guardrails(analysis_result)

            # Actualizar histórico
            self._update_historical_data(analysis_result)

            # Registrar éxito
            self.circuit_breaker.record_success()
            self.metrics['successful_analyses'] += 1

            # Actualizar métricas
            processing_time = time.time() - start_time
            analysis_result.processing_time = processing_time
            self._update_analysis_metrics(analysis_result, processing_time)

            # Enviar métricas a HealthMonitor
            await self._update_health_metrics(analysis_result)

            logger.info(
                f"💧 Análisis de liquidez completado: {analysis_result.liquidity_regime.value} | "
                f"Score: {analysis_result.liquidity_score:.3f} | "
                f"Imbalance: {analysis_result.imbalance_direction.value} | "
                f"Decisión: {analysis_result.decision.value}",
                extra=asdict(analysis_result)
            )

            return analysis_result

        except Exception as e:
            logger.error(f"❌ Error en análisis de liquidez: {e}")
            self.metrics['failed_analyses'] += 1
            self.circuit_breaker.record_failure()
            return await self._conservative_fallback_analysis(symbol)

    async def _analyze_order_book(self, symbol: str) -> Optional[OrderBookAnalysis]:
        """Analiza el order book L2 en profundidad"""
        try:
            # Obtener imbalance actual
            current_imbalance = self.market_data_collector.get_order_book_imbalance(symbol)
            if current_imbalance is None:
                logger.warning("⚠️ No hay datos de imbalance disponibles")
                # Usar valor por defecto para desarrollo
                current_imbalance = 0.1

            # Obtener datos de mercado en tiempo real
            market_data = await self.market_data_collector.get_real_time_price(symbol)
            if not market_data:
                logger.error("❌ No se pudieron obtener datos de mercado")
                return None
            
            # Calcular métricas del order book
            spread = market_data.ask - market_data.bid
            mid_price = (market_data.bid + market_data.ask) / 2
            spread_ratio = spread / mid_price if mid_price > 0 else 0

            # Determinar dirección del imbalance
            imbalance_direction = self._classify_imbalance(current_imbalance)

            # Analizar calidad del order book
            depth_quality = self._calculate_depth_quality(market_data)
            order_book_quality = self._calculate_order_book_quality(
                spread_ratio, depth_quality, current_imbalance
            )

            # Identificar zonas de liquidez
            liquidity_zones = await self._identify_liquidity_zones(symbol)

            # Calcular profundidad de mercado
            market_depth = self._calculate_market_depth(market_data)

            return OrderBookAnalysis(
                symbol=symbol,
                timestamp=datetime.now(),
                best_bid=market_data.bid,
                best_ask=market_data.ask,
                spread=spread,
                total_bid_size=market_data.additional_data.get('bid_size', 5000),
                total_ask_size=market_data.additional_data.get('ask_size', 5000),
                imbalance=current_imbalance,
                imbalance_direction=imbalance_direction,
                depth_quality=depth_quality,
                liquidity_zones=liquidity_zones,
                market_depth=market_depth,
                order_book_quality=order_book_quality
            )

        except Exception as e:
            logger.error(f"❌ Error analizando order book: {e}")
            return None

    async def _perform_comprehensive_analysis(self,
                                            order_book: OrderBookAnalysis,
                                            symbol: str,
                                            signal_context: Optional[Dict[str, Any]]) -> LiquidityAnalysisResult:
        """Realiza análisis comprehensivo de liquidez"""
        
        # Calcular score de liquidez principal
        liquidity_score = self._calculate_liquidity_score(order_book)
        
        # Determinar régimen de liquidez
        liquidity_regime = self._determine_liquidity_regime(liquidity_score, order_book)
        
        # Tomar decisión basada en análisis
        decision, risk_multiplier = self._make_liquidity_decision(
            liquidity_score, order_book, signal_context
        )
        
        # Calcular confianza del análisis
        confidence = self._calculate_analysis_confidence(order_book)
        
        # Métricas de análisis detalladas
        analysis_metrics = self._calculate_analysis_metrics(order_book, liquidity_score)
        
        # Pasos de razonamiento
        reasoning_steps = self._generate_reasoning_steps(order_book, liquidity_score, decision)
        
        # Verificar violaciones de guardrails
        guardrail_violations = self._check_guardrail_violations(order_book, liquidity_score)

        return LiquidityAnalysisResult(
            liquidity_score=liquidity_score,
            liquidity_regime=liquidity_regime,
            imbalance_direction=order_book.imbalance_direction,
            decision=decision,
            risk_multiplier=risk_multiplier,
            confidence=confidence,
            analysis_metrics=analysis_metrics,
            reasoning_steps=reasoning_steps,
            order_book_snapshot=order_book,
            processing_time=0.0,  # Se actualizará después
            timestamp=datetime.now(),
            guardrail_violations=guardrail_violations,
            metadata={
                "symbol": symbol,
                "signal_context": signal_context,
                "spread_ratio": order_book.spread / ((order_book.best_bid + order_book.best_ask) / 2),
                "volume_conditions": self._assess_volume_conditions(order_book)
            }
        )

    def _calculate_liquidity_score(self, order_book: OrderBookAnalysis) -> float:
        """Calcula score de liquidez compuesto"""
        score_components = []
        
        # Componente 1: Calidad del order book (30%)
        ob_quality_score = order_book.order_book_quality
        score_components.append(ob_quality_score * 0.3)
        
        # Componente 2: Spread y costo de transacción (25%)
        spread_ratio = order_book.spread / ((order_book.best_bid + order_book.best_ask) / 2)
        spread_score = max(0, 1 - (spread_ratio / self.thresholds['max_spread_ratio']))
        score_components.append(spread_score * 0.25)
        
        # Componente 3: Profundidad del mercado (20%)
        depth_score = order_book.depth_quality
        score_components.append(depth_score * 0.2)
        
        # Componente 4: Condiciones de imbalance (15%)
        imbalance_score = self._calculate_imbalance_score(order_book.imbalance)
        score_components.append(imbalance_score * 0.15)
        
        # Componente 5: Estabilidad del mercado (10%)
        stability_score = self._calculate_market_stability()
        score_components.append(stability_score * 0.1)
        
        # Calcular score final
        final_score = sum(score_components)
        return max(0.0, min(1.0, final_score))

    def _calculate_imbalance_score(self, imbalance: float) -> float:
        """Calcula score basado en imbalance del order book"""
        # Imbalances moderados son mejores para la ejecución
        abs_imbalance = abs(imbalance)
        if abs_imbalance < 0.2:
            return 0.9  # Balanceado - óptimo
        elif abs_imbalance < 0.5:
            return 0.7  # Moderado - aceptable
        elif abs_imbalance < 0.7:
            return 0.4  # Fuerte - subóptimo
        else:
            return 0.1  # Extremo - peligroso

    def _calculate_market_stability(self) -> float:
        """Calcula estabilidad del mercado basado en datos históricos"""
        if len(self.historical_analysis['liquidity_scores']) < 10:
            return 0.7  # Valor por defecto
        
        try:
            recent_scores = self.historical_analysis['liquidity_scores'][-10:]
            volatility = np.std(recent_scores) if len(recent_scores) > 1 else 0.1
            
            # Menor volatilidad = mayor estabilidad
            stability = max(0, 1 - (volatility * 10))
            return stability
        except Exception as e:
            logger.debug(f"Error calculando estabilidad: {e}")
            return 0.7

    def _determine_liquidity_regime(self, 
                                  liquidity_score: float, 
                                  order_book: OrderBookAnalysis) -> LiquidityRegime:
        """Determina el régimen de liquidez actual"""
        spread_ratio = order_book.spread / ((order_book.best_bid + order_book.best_ask) / 2)
        
        if liquidity_score >= 0.8 and spread_ratio <= 0.001:
            return LiquidityRegime.HIGH_LIQUIDITY
        elif liquidity_score >= 0.6 and spread_ratio <= 0.002:
            return LiquidityRegime.NORMAL_LIQUIDITY
        elif liquidity_score >= 0.4:
            return LiquidityRegime.LOW_LIQUIDITY
        else:
            return LiquidityRegime.CRITICAL_LIQUIDITY

    def _make_liquidity_decision(self,
                               liquidity_score: float,
                               order_book: OrderBookAnalysis,
                               signal_context: Optional[Dict[str, Any]]) -> Tuple[LiquidityDecision, float]:
        """Toma decisión de liquidez y calcula risk multiplier"""
        
        spread_ratio = order_book.spread / ((order_book.best_bid + order_book.best_ask) / 2)
        
        # Condiciones de kill switch
        if (spread_ratio > self.thresholds['kill_switch_spread'] or 
            order_book.order_book_quality < 0.3):
            self.metrics['kill_switch_activations'] += 1
            return LiquidityDecision.KILL_SWITCH, 0.0
        
        # Decisiones basadas en score y condiciones
        if liquidity_score >= 0.8:
            return LiquidityDecision.OPTIMAL, 1.2
        elif liquidity_score >= 0.7:
            return LiquidityDecision.OPTIMAL, 1.1
        elif liquidity_score >= 0.6:
            return LiquidityDecision.ACCEPTABLE, 1.0
        elif liquidity_score >= 0.5:
            return LiquidityDecision.SUBOPTIMAL, 0.8
        elif liquidity_score >= 0.4:
            return LiquidityDecision.SUBOPTIMAL, 0.6
        else:
            return LiquidityDecision.AVOID, 0.3

    def _calculate_analysis_confidence(self, order_book: OrderBookAnalysis) -> float:
        """Calcula confianza del análisis de liquidez"""
        confidence = 0.7  # Base
        
        # Mejorar confianza con calidad de datos
        confidence += order_book.order_book_quality * 0.2
        
        # Mejorar con profundidad del análisis
        confidence += order_book.depth_quality * 0.1
        
        return min(0.95, confidence)

    def _calculate_analysis_metrics(self, 
                                  order_book: OrderBookAnalysis, 
                                  liquidity_score: float) -> Dict[str, float]:
        """Calcula métricas detalladas del análisis"""
        spread_ratio = order_book.spread / ((order_book.best_bid + order_book.best_ask) / 2)
        
        return {
            "spread_ratio": spread_ratio,
            "imbalance_magnitude": abs(order_book.imbalance),
            "depth_quality": order_book.depth_quality,
            "order_book_quality": order_book.order_book_quality,
            "volume_ratio": order_book.total_bid_size / order_book.total_ask_size if order_book.total_ask_size > 0 else 1.0,
            "liquidity_score": liquidity_score,
            "market_depth_score": self._calculate_market_depth_score(order_book.market_depth)
        }

    def _generate_reasoning_steps(self,
                                order_book: OrderBookAnalysis,
                                liquidity_score: float,
                                decision: LiquidityDecision) -> List[str]:
        """Genera pasos de razonamiento para el análisis"""
        steps = []
        
        spread_pips = order_book.spread / ((order_book.best_bid + order_book.best_ask) / 2) * 10000
        steps.append(f"1. Análisis de spread: {order_book.spread:.4f} ({spread_pips:.1f} pips)")
        steps.append(f"2. Imbalance del order book: {order_book.imbalance:.3f} ({order_book.imbalance_direction.value})")
        steps.append(f"3. Calidad del order book: {order_book.order_book_quality:.3f}")
        steps.append(f"4. Profundidad de mercado: {order_book.depth_quality:.3f}")
        steps.append(f"5. Score de liquidez calculado: {liquidity_score:.3f}")
        steps.append(f"6. Régimen identificado: {self._determine_liquidity_regime(liquidity_score, order_book).value}")
        steps.append(f"7. Decisión final: {decision.value}")
        
        return steps

    def _check_guardrail_violations(self, 
                                  order_book: OrderBookAnalysis, 
                                  liquidity_score: float) -> List[str]:
        """Verifica violaciones de guardrails de liquidez"""
        violations = []
        
        spread_ratio = order_book.spread / ((order_book.best_bid + order_book.best_ask) / 2)
        
        if spread_ratio > self.thresholds['max_spread_ratio']:
            violations.append("spread_exceeded")
        
        if order_book.order_book_quality < self.thresholds['min_order_book_quality']:
            violations.append("low_order_book_quality")
        
        if liquidity_score < self.thresholds['min_liquidity_score']:
            violations.append("low_liquidity_score")
        
        if order_book.depth_quality < self.thresholds['min_depth_quality']:
            violations.append("insufficient_market_depth")
        
        return violations

    def _classify_imbalance(self, imbalance: float) -> ImbalanceDirection:
        """Clasifica la dirección del imbalance"""
        if imbalance > self.thresholds['imbalance_threshold_strong']:
            return ImbalanceDirection.STRONG_BID_IMBALANCE
        elif imbalance > self.thresholds['imbalance_threshold_moderate']:
            return ImbalanceDirection.MODERATE_BID_IMBALANCE
        elif imbalance < -self.thresholds['imbalance_threshold_strong']:
            return ImbalanceDirection.STRONG_ASK_IMBALANCE
        elif imbalance < -self.thresholds['imbalance_threshold_moderate']:
            return ImbalanceDirection.MODERATE_ASK_IMBALANCE
        else:
            return ImbalanceDirection.BALANCED

    def _calculate_depth_quality(self, market_data) -> float:
        """Calcula calidad de la profundidad del mercado"""
        try:
            # Implementación mejorada con datos reales del order book L2
            bid_size = market_data.additional_data.get('bid_size', 0)
            ask_size = market_data.additional_data.get('ask_size', 0)
            
            total_size = bid_size + ask_size
            if total_size == 0:
                return 0.0
            
            # Calcular calidad basada en distribución y profundidad
            depth_quality = 0.0
            
            # Factor 1: Volumen total (40%)
            volume_score = min(1.0, total_size / 15000)
            depth_quality += volume_score * 0.4
            
            # Factor 2: Balance bid/ask (30%)
            if total_size > 0:
                balance_ratio = min(bid_size, ask_size) / max(bid_size, ask_size) if max(bid_size, ask_size) > 0 else 0
                depth_quality += balance_ratio * 0.3
            
            # Factor 3: Consistencia histórica (30%)
            if len(self.historical_analysis['order_book_quality']) > 0:
                avg_quality = np.mean(self.historical_analysis['order_book_quality'][-10:])
                depth_quality += avg_quality * 0.3
            
            return max(0.0, min(1.0, depth_quality))
            
        except Exception as e:
            logger.debug(f"Error calculando depth quality: {e}")
            return 0.5

    def _calculate_order_book_quality(self, spread_ratio: float, depth_quality: float, imbalance: float) -> float:
        """Calcula calidad general del order book"""
        try:
            # Componente de spread (40%)
            spread_score = max(0, 1 - (spread_ratio / self.thresholds['max_spread_ratio']))
            
            # Componente de profundidad (40%)
            depth_score = depth_quality
            
            # Componente de balance (20%)
            balance_score = 1 - min(1.0, abs(imbalance))
            
            quality_score = (spread_score * 0.4) + (depth_score * 0.4) + (balance_score * 0.2)
            return max(0.0, min(1.0, quality_score))
        except Exception as e:
            logger.debug(f"Error calculando order book quality: {e}")
            return 0.5

    async def _identify_liquidity_zones(self, symbol: str) -> List[Dict[str, Any]]:
        """Identifica zonas de liquidez clave usando datos históricos y actuales"""
        try:
            zones = []
            
            # Obtener datos históricos de precios
            historical_data = await self.market_data_collector.get_historical_data(
                symbol, period="1d", interval="5m"
            )
            
            if historical_data and len(historical_data) > 0:
                # Calcular niveles de soporte y resistencia basados en volumen
                price_levels = [bar.close for bar in historical_data]
                volume_levels = [bar.volume for bar in historical_data]
                
                # Identificar clusters de volumen
                if len(price_levels) >= 10:
                    # Encontrar máximos de volumen como zonas de liquidez
                    volume_threshold = np.percentile(volume_levels, 70)
                    
                    for i, (price, volume) in enumerate(zip(price_levels, volume_levels)):
                        if volume > volume_threshold and i > 0 and i < len(price_levels) - 1:
                            zone_type = "SUPPORT" if price_levels[i-1] > price < price_levels[i+1] else "RESISTANCE"
                            
                            zones.append({
                                "price_level": float(price),
                                "zone_type": zone_type,
                                "liquidity_score": min(1.0, volume / max(volume_levels)),
                                "volume_cluster": "HIGH" if volume > np.percentile(volume_levels, 85) else "MEDIUM",
                                "timestamp": historical_data[i].timestamp
                            })
            
            # Si no hay suficientes datos, usar zonas por defecto
            if not zones:
                zones = [
                    {
                        "price_level": 3870.0,
                        "zone_type": "SUPPORT",
                        "liquidity_score": 0.8,
                        "volume_cluster": "HIGH"
                    },
                    {
                        "price_level": 3880.0,
                        "zone_type": "RESISTANCE", 
                        "liquidity_score": 0.7,
                        "volume_cluster": "MEDIUM"
                    }
                ]
            
            return zones[:5]  # Limitar a 5 zonas principales
            
        except Exception as e:
            logger.warning(f"⚠️ Error identificando zonas de liquidez: {e}")
            # Fallback a zonas por defecto
            return [
                {
                    "price_level": 3870.0,
                    "zone_type": "SUPPORT",
                    "liquidity_score": 0.8,
                    "volume_cluster": "HIGH"
                }
            ]

    def _calculate_market_depth(self, market_data) -> Dict[str, float]:
        """Calcula métricas de profundidad de mercado"""
        try:
            bid_size = market_data.additional_data.get('bid_size', 5000)
            ask_size = market_data.additional_data.get('ask_size', 5000)
            
            return {
                "immediate_depth": bid_size + ask_size,
                "depth_quality": self._calculate_depth_quality(market_data),
                "volume_imbalance": (bid_size - ask_size) / (bid_size + ask_size) if (bid_size + ask_size) > 0 else 0,
                "bid_depth": bid_size,
                "ask_depth": ask_size
            }
        except Exception as e:
            logger.debug(f"Error calculando market depth: {e}")
            return {
                "immediate_depth": 0,
                "depth_quality": 0,
                "volume_imbalance": 0,
                "bid_depth": 0,
                "ask_depth": 0
            }

    def _calculate_market_depth_score(self, market_depth: Dict[str, float]) -> float:
        """Calcula score de profundidad de mercado"""
        try:
            immediate_depth = market_depth.get('immediate_depth', 0)
            depth_quality = market_depth.get('depth_quality', 0)
            
            # Normalizar profundidad inmediata
            depth_normalized = min(1.0, immediate_depth / 10000)
            
            # Score combinado
            return (depth_normalized * 0.6) + (depth_quality * 0.4)
        except Exception as e:
            logger.debug(f"Error calculando market depth score: {e}")
            return 0.5

    def _assess_volume_conditions(self, order_book: OrderBookAnalysis) -> Dict[str, Any]:
        """Evalúa condiciones de volumen"""
        try:
            total_volume = order_book.total_bid_size + order_book.total_ask_size
            
            if total_volume > 15000:
                volume_condition = "VERY_HIGH"
            elif total_volume > 10000:
                volume_condition = "HIGH"
            elif total_volume > 5000:
                volume_condition = "NORMAL"
            elif total_volume > 2000:
                volume_condition = "LOW"
            else:
                volume_condition = "VERY_LOW"
                
            return {
                "total_volume": total_volume,
                "volume_condition": volume_condition,
                "bid_ask_ratio": order_book.total_bid_size / order_book.total_ask_size if order_book.total_ask_size > 0 else 1.0,
                "volume_imbalance": abs(order_book.total_bid_size - order_book.total_ask_size) / total_volume if total_volume > 0 else 0
            }
        except Exception as e:
            logger.debug(f"Error evaluando condiciones de volumen: {e}")
            return {
                "total_volume": 0,
                "volume_condition": "UNKNOWN",
                "bid_ask_ratio": 1.0,
                "volume_imbalance": 0
            }

    def _apply_liquidity_guardrails(self, result: LiquidityAnalysisResult) -> LiquidityAnalysisResult:
        """Aplica guardrails de seguridad al resultado"""
        # Si hay violaciones de guardrail, forzar decisión conservadora
        if result.guardrail_violations:
            result.decision = LiquidityDecision.AVOID
            result.risk_multiplier = max(0.3, result.risk_multiplier * 0.5)
            self.metrics['guardrail_violations'] += len(result.guardrail_violations)
            logger.warning(f"🚫 Guardrails de liquidez activados: {result.guardrail_violations}")
        
        # Limitar risk multiplier según configuración EAS
        result.risk_multiplier = min(1.5, max(0.1, result.risk_multiplier))
        
        return result

    async def _conservative_fallback_analysis(self, symbol: str) -> LiquidityAnalysisResult:
        """Análisis de fallback conservador para errores"""
        self.metrics['kill_switch_activations'] += 1
        
        # Crear order book de fallback
        fallback_order_book = OrderBookAnalysis(
            symbol=symbol,
            timestamp=datetime.now(),
            best_bid=0,
            best_ask=0,
            spread=0,
            total_bid_size=0,
            total_ask_size=0,
            imbalance=0,
            imbalance_direction=ImbalanceDirection.BALANCED,
            depth_quality=0,
            liquidity_zones=[],
            market_depth={},
            order_book_quality=0
        )
        
        return LiquidityAnalysisResult(
            liquidity_score=0.3,
            liquidity_regime=LiquidityRegime.CRITICAL_LIQUIDITY,
            imbalance_direction=ImbalanceDirection.BALANCED,
            decision=LiquidityDecision.KILL_SWITCH,
            risk_multiplier=0.0,
            confidence=0.1,
            analysis_metrics={"fallback_used": True},
            reasoning_steps=[
                "1. Fallback activado por error en análisis", 
                "2. Condiciones de mercado desconocidas", 
                "3. Decisión conservadora: KILL_SWITCH"
            ],
            order_book_snapshot=fallback_order_book,
            processing_time=0.0,
            timestamp=datetime.now(),
            guardrail_violations=["fallback_activation"],
            metadata={"fallback_reason": "error_recovery"}
        )

    def _update_historical_data(self, result: LiquidityAnalysisResult):
        """Actualiza datos históricos para análisis de tendencias"""
        try:
            self.historical_analysis['liquidity_scores'].append(result.liquidity_score)
            self.historical_analysis['imbalances'].append(result.order_book_snapshot.imbalance)
            self.historical_analysis['spreads'].append(result.order_book_snapshot.spread)
            self.historical_analysis['order_book_quality'].append(result.order_book_snapshot.order_book_quality)
            
            # Mantener tamaño del histórico
            for key in self.historical_analysis:
                if len(self.historical_analysis[key]) > self.max_history_size:
                    self.historical_analysis[key] = self.historical_analysis[key][-self.max_history_size:]
        except Exception as e:
            logger.debug(f"Error actualizando datos históricos: {e}")

    def _update_analysis_metrics(self, result: LiquidityAnalysisResult, processing_time: float):
        """Actualiza métricas del agente"""
        try:
            # Actualizar tiempo promedio de procesamiento
            self.metrics['total_processing_time'] += processing_time
            self.metrics['average_processing_time'] = (
                self.metrics['total_processing_time'] / self.metrics['successful_analyses']
            )
            
            # Distribución de regímenes
            regime = result.liquidity_regime.value
            self.metrics['liquidity_regime_distribution'][regime] = (
                self.metrics['liquidity_regime_distribution'].get(regime, 0) + 1
            )
            
            # Distribución de imbalances
            imbalance = result.imbalance_direction.value
            self.metrics['imbalance_distribution'][imbalance] = (
                self.metrics['imbalance_distribution'].get(imbalance, 0) + 1
            )
            
            self.metrics['last_analysis_time'] = datetime.now()
            
        except Exception as e:
            logger.debug(f"Error actualizando métricas de análisis: {e}")

    async def _update_health_metrics(self, result: LiquidityAnalysisResult):
        """Actualiza HealthMonitor con métricas del agente"""
        try:
            health_monitor = get_health_monitor()
            
            metrics = {
                "liquidity_score": result.liquidity_score,
                "liquidity_regime": result.liquidity_regime.value,
                "imbalance_direction": result.imbalance_direction.value,
                "decision": result.decision.value,
                "risk_multiplier": result.risk_multiplier,
                "confidence": result.confidence,
                "processing_time": result.processing_time,
                "guardrail_violations_count": len(result.guardrail_violations),
                "success_rate": (self.metrics['successful_analyses'] / self.metrics['total_analyses']) * 100 
                if self.metrics['total_analyses'] > 0 else 0,
                "average_processing_time": self.metrics['average_processing_time']
            }
            
            await health_monitor.update_agent_metrics("liquidity_analysis_agent", metrics)
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron enviar métricas a HealthMonitor: {e}")

    def _health_callback(self) -> Dict[str, Any]:
        """
        Callback para HealthMonitor - ajusta comportamiento basado en salud del sistema
        """
        status_info = {
            "status": "OK" if self.circuit_breaker.is_open() else "DEGRADED",
            "metrics": self.metrics,
            "circuit_breaker_state": self.circuit_breaker.state,
            "historical_data_points": sum(len(v) for v in self.historical_analysis.values()),
            "last_analysis_time": self.metrics['last_analysis_time'].isoformat() 
            if self.metrics['last_analysis_time'] else None
        }
        
        # Ajustar comportamiento basado en estado del sistema
        if status_info["status"] == "DEGRADED":
            # En modo degradado, ser más conservador
            self.thresholds['min_liquidity_score'] = 0.7
            self.thresholds['max_spread_ratio'] = 0.0015
            logger.info("🔧 Modo degradado: umbrales de liquidez ajustados a modo conservador")
        elif status_info["status"] == "OK":
            # Restaurar configuración normal
            self.thresholds['min_liquidity_score'] = 0.6
            self.thresholds['max_spread_ratio'] = 0.002
        
        return status_info

    def get_agent_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas del agente para monitoreo"""
        stats = self.metrics.copy()
        
        # Calcular tasa de éxito
        if stats['total_analyses'] > 0:
            stats['success_rate'] = (stats['successful_analyses'] / stats['total_analyses']) * 100
        else:
            stats['success_rate'] = 0
        
        stats['circuit_breaker_state'] = self.circuit_breaker.get_state()
        stats['historical_data_points'] = sum(len(v) for v in self.historical_analysis.values())
        
        return stats

    async def close(self):
        """Cierre seguro del agente"""
        logger.info("🔌 Cerrando Liquidity Analysis Agent...")
        
        try:
            # Enviar métricas finales a HealthMonitor
            await self._update_health_metrics(await self._conservative_fallback_analysis("XAUUSD"))
        except Exception as e:
            logger.warning(f"⚠️ Error enviando métricas finales: {e}")
        
        logger.info("✅ Liquidity Analysis Agent cerrado correctamente")

# Función de fábrica para integración con el sistema
def create_liquidity_analysis_agent(config: Dict[str, Any]) -> LiquidityAnalysisAgent:
    """Crea y configura el agente de análisis de liquidez"""
    return LiquidityAnalysisAgent(config)

# Ejemplo de uso
async def main():
    """Función principal de ejemplo"""
    config = {
        "liquidity_agent": {
            "analysis_config": {
                "depth_levels": 5,
                "volume_threshold": 1000,
                "refresh_interval": 2
            }
        }
    }
    
    try:
        # Crear agentes de ejemplo (simulados para la demo)
        class MockMarketDataCollector:
            async def get_real_time_price(self, symbol):
                class MockMarketData:
                    def __init__(self):
                        self.bid = 3875.0
                        self.ask = 3875.5
                        self.additional_data = {
                            'bid_size': 7500,
                            'ask_size': 6800,
                            'imbalance': 0.1
                        }
                return MockMarketData()
            
            def get_order_book_imbalance(self, symbol):
                return 0.1
            
            async def get_historical_data(self, symbol, period, interval):
                return []
            
            async def close(self):
                pass
        
        # Crear agente de liquidez
        agent = create_liquidity_analysis_agent(config)
        market_data_collector = MockMarketDataCollector()
        await agent.initialize(market_data_collector)
        
        # Ejecutar análisis de liquidez
        result = await agent.analyze_liquidity_conditions("XAUUSD")
        
        print(f"\n💧 Resultado de Análisis de Liquidez:")
        print(f"   Score: {result.liquidity_score:.3f}")
        print(f"   Régimen: {result.liquidity_regime.value}")
        print(f"   Imbalance: {result.imbalance_direction.value}")
        print(f"   Decisión: {result.decision.value}")
        print(f"   Risk Multiplier: {result.risk_multiplier:.2f}")
        print(f"   Confianza: {result.confidence:.3f}")
        
        # Mostrar métricas del agente
        metrics = agent.get_agent_metrics()
        print(f"\n📊 Métricas del Agente:")
        print(f"   Tasa de éxito: {metrics.get('success_rate', 0):.1f}%")
        print(f"   Tiempo promedio: {metrics.get('average_processing_time', 0):.3f}s")
        
    except KeyboardInterrupt:
        print("⏹️ Interrumpido por usuario")
    except Exception as e:
        print(f"❌ Error en ejemplo: {e}")
    finally:
        if 'agent' in locals():
            await agent.close()
        if 'market_data_collector' in locals():
            await market_data_collector.close()

if __name__ == "__main__":
    asyncio.run(main())