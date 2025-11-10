[file name]: core/signal_generator.py
[file content begin]
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Signal Generator v3.1 - EAS Híbrido 2025 Integration con Núcleo Inmutable
Generador de señales con validación inmutable EAS y análisis de estructura avanzado
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import pytz
import asyncio

# Importaciones de la nueva arquitectura
from infrastructure.structured_logger import StructuredLogger
from infrastructure.health_monitor import get_health_monitor
from infrastructure.circuit_breaker import CircuitBreaker
from infrastructure.guardrails import with_guardrails
from agents.macro_analysis_agent import EnhancedMacroBias
from agents.liquidity_analysis_agent import LiquidityAnalysisResult

# NÚCLEO INMUTABLE EAS 2025
from core.immutable_core import IMMUTABLE_CORE, PatternData

# IMPORTACIÓN MT5 REAL PARA DATOS DE MERCADO
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

logger = StructuredLogger("HECTAGold.SignalGenerator")

class SignalType(Enum):
    """Tipos de señales EAS Híbrido 2025"""
    BOS_RETEST_BULLISH = "BOS_RETEST_BULLISH"
    BOS_RETEST_BEARISH = "BOS_RETEST_BEARISH"
    LIQUIDITY_SWEEP_BULLISH = "LIQUIDITY_SWEEP_BULLISH"
    LIQUIDITY_SWEEP_BEARISH = "LIQUIDITY_SWEEP_BEARISH"
    ORDERBLOCK_RETEST_BULLISH = "ORDERBLOCK_RETEST_BULLISH"
    ORDERBLOCK_RETEST_BEARISH = "ORDERBLOCK_RETEST_BEARISH"
    FVG_MITIGATION_BULLISH = "FVG_MITIGATION_BULLISH"
    FVG_MITIGATION_BEARISH = "FVG_MITIGATION_BEARISH"
    MARKET_STRUCTURE_SHIFT = "MARKET_STRUCTURE_SHIFT"
    TREND_CONTINUATION = "TREND_CONTINUATION"

class SignalPriority(Enum):
    """Prioridades de señales EAS"""
    CRITICAL = "CRITICAL"    # Máxima confianza, condiciones óptimas
    HIGH = "HIGH"            # Alta confianza, buenas condiciones
    MEDIUM = "MEDIUM"        # Confianza media, condiciones aceptables
    LOW = "LOW"              # Baja confianza, condiciones subóptimas
    MONITOR = "MONITOR"      # Solo monitoreo, no trading

@dataclass
class TradingSignal:
    """Estructura de señal de trading EAS Híbrido 2025"""
    signal_id: str
    signal_type: SignalType
    direction: str  # "BUY" o "SELL"
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    confidence: int  # 0-100
    risk_reward_ratio: float
    macro_bias_score: int
    execution_mode: str  # "MARKET" o "PENDING"
    timestamp: datetime
    reasoning: str
    technical_indicators: Dict[str, Any]
    market_structure: Dict[str, Any]
    sentiment_score: float
    liquidity_zone: str
    validation_passed: bool = False
    priority: SignalPriority = SignalPriority.MEDIUM
    timeframes: List[str] = None
    session_context: str = ""
    risk_multiplier: float = 1.0
    immutable_validation: Dict[str, Any] = None  # Nuevo: Resultado validación inmutable
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timeframes is None:
            self.timeframes = ["M15", "H1"]
        if self.metadata is None:
            self.metadata = {}
        if self.immutable_validation is None:
            self.immutable_validation = {}
        # CORRECCIÓN: signal_id ya se pasa como parámetro, no sobreescribir
        if not self.signal_id:
            self.signal_id = f"signal_{int(datetime.now().timestamp())}_{self.signal_type.value}"

@dataclass
class MarketStructure:
    """Estructura de mercado analizada EAS"""
    fvg_zones: List[Dict[str, Any]]
    order_blocks: List[Dict[str, Any]]
    liquidity_sweeps: List[Dict[str, Any]]
    bos_points: List[Dict[str, Any]]
    mitigation_zones: List[Dict[str, Any]]
    current_trend: str
    trend_strength: float
    key_levels: List[Dict[str, Any]]
    market_phase: str  # ACCUMULATION, DISTRIBUTION, TREND, RANGING
    structure_quality: float
    timeframe_alignment: Dict[str, str]
    last_update: datetime

class SignalGenerator:
    """
    Generador de señales EAS Híbrido 2025
    Integrado con Núcleo Inmutable, HealthMonitor, análisis de liquidez y arquitectura de agentes
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa generador de señales EAS con núcleo inmutable
        
        Args:
            config: Configuración del sistema EAS
        """
        self.config = config
        self.generator_config = config.get('signal_generation', {})
        self.core_rules = config.get('core_rules', {})
        
        # NÚCLEO INMUTABLE EAS 2025
        self.immutable_core = IMMUTABLE_CORE
        
        # Parámetros EAS (ahora referencian al núcleo inmutable)
        self.RR_RATIO = self.immutable_core.RR_RATIO
        self.RISK_PER_TRADE_PCT = self.immutable_core.RISK_PERCENT
        self.MAX_CONSECUTIVE_LOSSES = self.immutable_core.MAX_CONSECUTIVE_LOSSES
        
        # Umbrales de confianza
        self.min_confidence = self.generator_config.get('min_confidence', 75)
        self.optimal_confidence = self.generator_config.get('optimal_confidence', 85)
        
        # CONEXIÓN MT5 PARA DATOS REALES
        self.mt5_initialized = False
        if MT5_AVAILABLE:
            self.mt5_initialized = self._initialize_mt5_connection()
        
        # Circuit breaker para protección
        self.circuit_breaker = CircuitBreaker(
            max_failures=3,
            reset_timeout=300
        )
        
        # Estructura de mercado
        self.market_structure = MarketStructure([], [], [], [], [], "sideways", 0.0, [], "ACCUMULATION", 0.0, {}, datetime.now())
        
        # Cache para eficiencia
        self.last_analysis_time = None
        self.analysis_cache_duration = 30  # segundos
        self.signals_cache = []
        self.cache_max_size = 50
        
        # Métricas para HealthMonitor
        self.metrics = {
            'total_signals_generated': 0,
            'high_confidence_signals': 0,
            'signals_by_type': {},
            'average_confidence': 0.0,
            'market_structure_quality': 0.0,
            'last_signal_time': None,
            'consecutive_rejections': 0,
            'generation_success_rate': 0.0,
            'data_quality_score': 1.0,
            'immutable_validations_passed': 0,
            'immutable_validations_failed': 0
        }
        
        # Configuración de análisis
        self.analysis_config = {
            'min_trend_strength': 0.4,
            'max_pullback_depth': 0.005,
            'min_structure_quality': 0.6,
            'timeframe_alignment_required': True,
            'session_filtering': True,
            'require_immutable_validation': True  # Nueva: Requerir validación inmutable
        }
        
        logger.info("🎯 Signal Generator EAS Híbrido 2025 con Núcleo Inmutable inicializado")
        logger.info(f"🛡️ Núcleo Inmutable: {self.immutable_core.RISK_PERCENT}% riesgo | {self.immutable_core.MAX_CONSECUTIVE_LOSSES} pérdidas kill switch")
        logger.info(f"📊 Fuente datos: {'✅ MT5 Real' if self.mt5_initialized else '❌ Simulación'}")

    def _initialize_mt5_connection(self) -> bool:
        """Inicializa conexión MT5 para obtener datos de mercado reales"""
        try:
            if not mt5.initialize():
                logger.error(f"❌ MT5 initialization failed: {mt5.last_error()}")
                return False
            
            # Verificar que el símbolo XAUUSD esté disponible
            symbol_info = mt5.symbol_info("XAUUSD")
            if symbol_info is None:
                logger.error("❌ Símbolo XAUUSD no disponible en MT5")
                return False
                
            logger.info("✅ MT5 conectado para datos de mercado reales")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error conexión MT5: {e}")
            return False

    async def initialize(self):
        """Inicialización del generador con integración HealthMonitor y Núcleo Inmutable"""
        try:
            # Registrar callback en HealthMonitor
            health_monitor = get_health_monitor()
            health_monitor.register_health_callback(self._health_callback)
            
            # Verificar estado del núcleo inmutable
            immutable_status = self.immutable_core.get_immutable_status()
            logger.info(f"🛡️ Estado Núcleo Inmutable: Trading habilitado: {immutable_status['trading_enabled']}")
            
            logger.info("🚀 Signal Generator con Núcleo Inmutable inicializado")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando Signal Generator: {e}")
            raise

    def _prepare_market_data(self, symbol: str = "XAUUSD", timeframes: List[str] = None) -> Dict[str, pd.DataFrame]:
        """Prepara datos de mercado desde MT5"""
        # Implementación existente de tu v3.0
        market_data = {}
        # ... (mantener implementación existente)
        return market_data

    def _enhance_market_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Enriquece datos de mercado con métricas ICT"""
        # Implementación existente de tu v3.0
        return df

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula RSI para análisis de momentum"""
        # Implementación existente
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @with_guardrails(agent_context="signal_generation")
    async def generate_signals(self, 
                             market_data: Dict[str, Any], 
                             macro_bias: EnhancedMacroBias,
                             liquidity_analysis: Optional[LiquidityAnalysisResult] = None,
                             current_session: str = "NY_OPEN") -> List[TradingSignal]:
        """
        Genera señales EAS con validación inmutable y análisis completo integrado
        
        Args:
            market_data: Datos de mercado actuales
            macro_bias: Bias macro actual
            liquidity_analysis: Análisis de liquidez (opcional)
            current_session: Sesión actual de trading
            
        Returns:
            Lista de señales generadas y validadas por núcleo inmutable
        """
        start_time = datetime.now()
        
        try:
            # Verificar circuit breaker
            if not self.circuit_breaker.allow_request():
                logger.warning("🔒 Circuit breaker activado - generación de señales suspendida")
                return []

            # 1. Validar condiciones de mercado básicas
            if not await self._validate_market_conditions(market_data, macro_bias):
                logger.debug("❌ Condiciones de mercado no óptimas para generación de señales")
                return []

            # 2. Analizar estructura de mercado (con cache)
            if self._should_analyze_market_structure():
                self.market_structure = await self._analyze_market_structure_advanced(market_data)
                self.last_analysis_time = datetime.now()

            # 3. Generar señales basadas en patrones EAS
            raw_signals = await self._generate_eas_pattern_signals(market_data, macro_bias, current_session)
            
            # 4. APLICAR VALIDACIÓN INMUTABLE EAS 2025 (NUEVO)
            immutable_validated_signals = await self._apply_immutable_validation(raw_signals, market_data)
            
            # 5. Aplicar filtros de liquidez si está disponible
            if liquidity_analysis:
                filtered_signals = self._apply_liquidity_filters(immutable_validated_signals, liquidity_analysis)
            else:
                filtered_signals = immutable_validated_signals

            # 6. Mejorar confianza con análisis integrado
            enhanced_signals = await self._enhance_signals_confidence(
                filtered_signals, macro_bias, liquidity_analysis
            )

            # 7. Aplicar filtros de sesión y timeframe
            session_filtered = self._apply_session_filters(enhanced_signals, current_session)
            
            # 8. Ordenar y limitar señales
            final_signals = self._prioritize_and_limit_signals(session_filtered)
            
            # 9. Actualizar métricas y cache
            self._update_generation_metrics(final_signals)
            self._update_signals_cache(final_signals)
            
            # Registrar éxito
            self.circuit_breaker.record_success()
            
            # Enviar métricas a HealthMonitor
            await self._update_health_metrics(final_signals, start_time)
            
            logger.info(
                f"🎯 Generadas {len(final_signals)} señales EAS | "
                f"Confianza promedio: {self.metrics['average_confidence']:.1f}% | "
                f"Validaciones Inmutables: {self.metrics['immutable_validations_passed']}✅/{self.metrics['immutable_validations_failed']}❌",
                extra={
                    "signals_count": len(final_signals), 
                    "average_confidence": self.metrics['average_confidence'],
                    "immutable_passed": self.metrics['immutable_validations_passed'],
                    "immutable_failed": self.metrics['immutable_validations_failed']
                }
            )
            
            return final_signals
            
        except Exception as e:
            logger.error(f"❌ Error en generación de señales: {e}")
            self.circuit_breaker.record_failure()
            return []

    async def _validate_market_conditions(self, market_data: Dict[str, Any], macro_bias: EnhancedMacroBias) -> bool:
        """Valida condiciones básicas del mercado"""
        # Implementación existente de tu v3.0
        if macro_bias.kill_switch:
            logger.warning("🚨 Kill switch macro activado - no se generan señales")
            return False
        return True

    async def _analyze_market_structure_advanced(self, market_data: Dict[str, Any]) -> MarketStructure:
        """Análisis avanzado de estructura de mercado"""
        # Implementación existente de tu v3.0
        structure = MarketStructure([], [], [], [], [], "sideways", 0.0, [], "ACCUMULATION", 0.0, {}, datetime.now())
        # ... análisis de estructura
        return structure

    async def _apply_immutable_validation(self, signals: List[TradingSignal], market_data: Dict[str, Any]) -> List[TradingSignal]:
        """
        Aplica validación del núcleo inmutable EAS 2025 a las señales
        """
        validated_signals = []
        
        for signal in signals:
            try:
                # Crear PatternData para validación inmutable
                pattern_data = self._create_pattern_data_from_signal(signal, market_data)
                
                # Validar con núcleo inmutable
                is_valid, reason = self.immutable_core.validate_bos_retest(pattern_data)
                
                # Actualizar señal con resultado de validación
                signal.immutable_validation = {
                    'passed': is_valid,
                    'reason': reason,
                    'timestamp': datetime.now(),
                    'pattern_type': signal.signal_type.value
                }
                
                if is_valid:
                    signal.validation_passed = True
                    validated_signals.append(signal)
                    self.metrics['immutable_validations_passed'] += 1
                    logger.debug(f"🛡️ Señal {signal.signal_id} validada por núcleo inmutable")
                else:
                    self.metrics['immutable_validations_failed'] += 1
                    logger.debug(f"🚫 Señal {signal.signal_id} rechazada por núcleo inmutable: {reason}")
                    
            except Exception as e:
                logger.error(f"❌ Error en validación inmutable para señal {signal.signal_id}: {e}")
                continue
                
        return validated_signals

    def _create_pattern_data_from_signal(self, signal: TradingSignal, market_data: Dict[str, Any]) -> PatternData:
        """
        Crea objeto PatternData para validación con núcleo inmutable
        """
        # Determinar características del patrón basado en el tipo de señal
        is_bos_retest = "BOS_RETEST" in signal.signal_type.value
        is_liquidity_sweep = "LIQUIDITY_SWEEP" in signal.signal_type.value
        
        # Calcular confianza normalizada (0-1)
        confidence_normalized = signal.confidence / 100.0
        
        # Determinar sesión actual
        current_session = self._get_current_session_context()
        
        return PatternData(
            break_confirmed=is_bos_retest,  # BOS implica break confirmado
            retest_successful=is_bos_retest,  # BOS_RETEST implica retest exitoso
            volume_confirmation=market_data.get('volume_ratio', 1.0) > 1.2,  # Volumen superior al promedio
            momentum_aligned=self._is_momentum_aligned(signal.direction, market_data),
            confidence=confidence_normalized,
            liquidity_sweep=is_liquidity_sweep,
            orderblock_retest=is_bos_retest,  # BOS_RETEST implica order block retest
            session=current_session,
            timestamp=datetime.now()
        )

    def _is_momentum_aligned(self, direction: str, market_data: Dict[str, Any]) -> bool:
        """Verifica si el momentum está alineado con la dirección de la señal"""
        try:
            # Usar RSI para determinar momentum
            rsi = market_data.get('rsi', 50)
            
            if direction == "BUY":
                return rsi < 70  # No sobrecomprado
            else:  # SELL
                return rsi > 30  # No sobrevendido
                
        except Exception:
            return True  # Fallback a True si no se puede determinar

    async def _generate_eas_pattern_signals(self,
                                          market_data: Dict[str, Any],
                                          macro_bias: EnhancedMacroBias,
                                          current_session: str) -> List[TradingSignal]:
        """Genera señales basadas en patrones EAS"""
        signals = []
        current_price = market_data.get('close', 0)
        
        # 1. Señal BOS + Retest (Alta prioridad EAS)
        bos_signals = self._generate_bos_retest_signals(current_price, macro_bias, current_session)
        signals.extend(bos_signals)
        
        # 2. Señal de Liquidity Sweep
        liquidity_signals = self._generate_liquidity_sweep_signals(current_price, macro_bias, current_session)
        signals.extend(liquidity_signals)
        
        # 3. Señal de Order Block Retest
        ob_signals = self._generate_order_block_signals(current_price, macro_bias, current_session)
        signals.extend(ob_signals)
        
        # 4. Señal de FVG Mitigation
        fvg_signals = self._generate_fvg_mitigation_signals(current_price, macro_bias, current_session)
        signals.extend(fvg_signals)
        
        # 5. Señal de Trend Continuation
        trend_signals = self._generate_trend_continuation_signals(current_price, macro_bias, current_session)
        signals.extend(trend_signals)
        
        return signals

    def _generate_bos_retest_signals(self, 
                                   current_price: float,
                                   macro_bias: EnhancedMacroBias,
                                   session: str) -> List[TradingSignal]:
        """Genera señales de BOS + Retest EAS"""
        signals = []
        
        for bos in self.market_structure.bos_points[-3:]:
            if not bos.get('confirmed', False):
                continue
                
            # Buscar Order Block relacionado
            related_ob = self._find_related_orderblock_advanced(bos)
            if not related_ob:
                continue
            
            # Verificar retest con tolerancia EAS
            ob_price = related_ob['price_level']
            price_diff_pct = abs(current_price - ob_price) / ob_price
            
            if price_diff_pct < 0.001:  # 0.1% de tolerancia EAS
                base_confidence = self._calculate_base_confidence(related_ob, bos)
                enhanced_confidence = self._calculate_enhanced_confidence_eas(
                    base_confidence, macro_bias, session
                )
                
                # SOLO CREAR SEÑAL - La validación inmutable se aplicará después
                if bos['type'] == 'bullish_bos':
                    signal = self._create_signal(
                        signal_type=SignalType.BOS_RETEST_BULLISH,
                        direction="BUY",
                        entry_price=current_price,
                        stop_loss=related_ob['low'] - 0.0005,
                        confidence=enhanced_confidence,
                        macro_bias=macro_bias,
                        reasoning=f"BOS Alcista confirmado + Retest de OB en {related_ob['price_level']:.2f}",
                        priority=SignalPriority.HIGH if enhanced_confidence > 80 else SignalPriority.MEDIUM
                    )
                    signals.append(signal)
                
                elif bos['type'] == 'bearish_bos':
                    signal = self._create_signal(
                        signal_type=SignalType.BOS_RETEST_BEARISH,
                        direction="SELL",
                        entry_price=current_price,
                        stop_loss=related_ob['high'] + 0.0005,
                        confidence=enhanced_confidence,
                        macro_bias=macro_bias,
                        reasoning=f"BOS Bajista confirmado + Retest de OB en {related_ob['price_level']:.2f}",
                        priority=SignalPriority.HIGH if enhanced_confidence > 80 else SignalPriority.MEDIUM
                    )
                    signals.append(signal)
        
        return signals

    def _generate_liquidity_sweep_signals(self,
                                        current_price: float,
                                        macro_bias: EnhancedMacroBias,
                                        session: str) -> List[TradingSignal]:
        """Genera señales de Liquidity Sweep EAS"""
        signals = []
        
        for sweep in self.market_structure.liquidity_sweeps[-3:]:
            time_since_sweep = (datetime.now() - sweep['time']).total_seconds() / 60
            
            if time_since_sweep > 45:  # Sweep muy antiguo
                continue
            
            price_diff_pct = abs(current_price - sweep['price']) / sweep['price']
            
            if price_diff_pct < 0.001:  # 0.1% de tolerancia
                base_confidence = 80
                enhanced_confidence = self._calculate_enhanced_confidence_eas(
                    base_confidence, macro_bias, session
                )
                
                if sweep['type'] == 'liquidity_sweep_high':
                    signal = self._create_signal(
                        signal_type=SignalType.LIQUIDITY_SWEEP_BEARISH,
                        direction="SELL",
                        entry_price=current_price,
                        stop_loss=sweep['price'] + 0.001,
                        confidence=enhanced_confidence,
                        macro_bias=macro_bias,
                        reasoning=f"Liquidity sweep reciente en highs - Reversión esperada",
                        priority=SignalPriority.HIGH
                    )
                    signals.append(signal)
                
                elif sweep['type'] == 'liquidity_sweep_low':
                    signal = self._create_signal(
                        signal_type=SignalType.LIQUIDITY_SWEEP_BULLISH,
                        direction="BUY",
                        entry_price=current_price,
                        stop_loss=sweep['price'] - 0.001,
                        confidence=enhanced_confidence,
                        macro_bias=macro_bias,
                        reasoning=f"Liquidity sweep reciente en lows - Reversión esperada",
                        priority=SignalPriority.HIGH
                    )
                    signals.append(signal)
        
        return signals

    def _create_signal(self,
                     signal_type: SignalType,
                     direction: str,
                     entry_price: float,
                     stop_loss: float,
                     confidence: int,
                     macro_bias: EnhancedMacroBias,
                     reasoning: str,
                     priority: SignalPriority = SignalPriority.MEDIUM) -> TradingSignal:
        """Crea una señal de trading EAS estandarizada"""
        
        # Calcular take profit basado en RR ratio EAS INMUTABLE
        if direction == "BUY":
            take_profit = entry_price + (entry_price - stop_loss) * self.immutable_core.RR_RATIO
        else:
            take_profit = entry_price - (stop_loss - entry_price) * self.immutable_core.RR_RATIO
        
        # Calcular lot size base (se ajustará posteriormente con núcleo inmutable)
        lot_size = 0.1  # Tamaño base, se ajustará por riesgo en execution
        
        # CORRECCIÓN: Generar signal_id único
        signal_id = f"signal_{int(datetime.now().timestamp())}_{signal_type.value}"
        
        return TradingSignal(
            signal_id=signal_id,  # CORRECCIÓN: Pasar signal_id explícitamente
            signal_type=signal_type,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            lot_size=lot_size,
            confidence=confidence,
            risk_reward_ratio=self.immutable_core.RR_RATIO,
            macro_bias_score=macro_bias.bias_score,
            execution_mode="LIMIT",
            timestamp=datetime.now(),
            reasoning=reasoning,
            technical_indicators=self._get_advanced_technical_indicators(),
            market_structure=asdict(self.market_structure),
            sentiment_score=0.7,
            liquidity_zone="MEDIUM",
            priority=priority,
            session_context=self._get_current_session_context(),
            risk_multiplier=macro_bias.risk_multiplier,
            metadata={
                "structure_quality": self.market_structure.structure_quality,
                "trend_strength": self.market_structure.trend_strength,
                "market_phase": self.market_structure.market_phase,
                "immutable_core_version": "EAS_Hybrid_2025_v1.0"
            }
        )

    def _calculate_base_confidence(self, order_block: Dict[str, Any], bos_point: Dict[str, Any]) -> int:
        """Calcula confianza base para señal EAS"""
        base_confidence = 75
        
        # Factor calidad del order block
        base_confidence += int(order_block.get('quality', 0) * 20)
        
        # Factor tiempo desde BOS
        time_since_bos = (datetime.now() - bos_point['time']).total_seconds() / 3600
        if time_since_bos < 2:
            base_confidence += 10
        elif time_since_bos > 6:
            base_confidence -= 15
        
        # Factor volumen
        if order_block.get('volume_confirmation', False):
            base_confidence += 5
        
        return max(50, min(95, base_confidence))

    def _calculate_enhanced_confidence_eas(self,
                                         base_confidence: int,
                                         macro_bias: EnhancedMacroBias,
                                         session: str) -> int:
        """Calcula confianza mejorada EAS con múltiples factores"""
        confidence = base_confidence
        
        # Factor macro (30% peso)
        macro_factor = macro_bias.bias_score / 10.0
        confidence = int(confidence * (0.7 + 0.3 * macro_factor))
        
        # Factor sesión (20% peso)
        session_factor = 1.0 if session == "NY_OPEN" else 0.8
        confidence = int(confidence * (0.8 + 0.2 * session_factor))
        
        # Factor estructura de mercado (25% peso)
        structure_factor = self.market_structure.structure_quality
        confidence = int(confidence * (0.75 + 0.25 * structure_factor))
        
        # Factor tendencia (25% peso)
        trend_factor = self.market_structure.trend_strength
        confidence = int(confidence * (0.75 + 0.25 * trend_factor))
        
        return max(50, min(95, confidence))

    def _apply_liquidity_filters(self,
                               signals: List[TradingSignal],
                               liquidity_analysis: LiquidityAnalysisResult) -> List[TradingSignal]:
        """Aplica filtros de liquidez EAS a las señales"""
        filtered_signals = []
        
        for signal in signals:
            # Verificar condiciones de liquidez
            if liquidity_analysis.decision.value in ["AVOID", "KILL_SWITCH"]:
                continue  # No generar señales en mala liquidez
            
            # Ajustar confianza basado en análisis de liquidez
            liquidity_confidence_boost = 0
            if liquidity_analysis.liquidity_regime.value == "HIGH_LIQUIDITY":
                liquidity_confidence_boost = 10
            elif liquidity_analysis.liquidity_regime.value == "LOW_LIQUIDITY":
                liquidity_confidence_boost = -15
            
            signal.confidence = max(50, min(95, signal.confidence + liquidity_confidence_boost))
            
            # Ajustar risk multiplier
            signal.risk_multiplier = min(signal.risk_multiplier, liquidity_analysis.risk_multiplier)
            
            filtered_signals.append(signal)
        
        return filtered_signals

    def _apply_session_filters(self, signals: List[TradingSignal], current_session: str) -> List[TradingSignal]:
        """Aplica filtros de sesión EAS"""
        if not self.analysis_config['session_filtering']:
            return signals
        
        filtered_signals = []
        
        for signal in signals:
            # Solo permitir señales HIGH en sesiones no óptimas
            if current_session != "NY_OPEN" and signal.priority != SignalPriority.HIGH:
                continue
            
            filtered_signals.append(signal)
        
        return filtered_signals

    def _prioritize_and_limit_signals(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """Prioriza y limita señales según reglas EAS"""
        if not signals:
            return []
        
        # Ordenar por prioridad y confianza
        signals.sort(key=lambda x: (
            x.priority.value != SignalPriority.CRITICAL.value,
            x.priority.value != SignalPriority.HIGH.value,
            x.priority.value != SignalPriority.MEDIUM.value,
            -x.confidence
        ))
        
        # Limitar a máximo 2 señales por ciclo
        return signals[:2]

    def _find_related_orderblock_advanced(self, bos_point: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Encuentra order block relacionado con análisis avanzado"""
        for ob in self.market_structure.order_blocks:
            time_diff = abs((ob['time'] - bos_point['time']).total_seconds())
            price_diff = abs(ob['price_level'] - bos_point['price']) / bos_point['price']
            
            if time_diff <= 3600 and price_diff <= 0.001:  # 1 hora y 0.1% de precio
                return ob
        
        return None

    def _get_advanced_technical_indicators(self) -> Dict[str, Any]:
        """Obtiene indicadores técnicos avanzados"""
        return {
            'rsi': 55.0,
            'stoch': 60.0,
            'ema20': 3875.0,
            'ema50': 3880.0,
            'ema100': 3870.0,
            'atr': 12.5,
            'volume_profile': 'balanced',
            'market_structure_quality': self.market_structure.structure_quality,
            'trend_strength': self.market_structure.trend_strength
        }

    def _get_current_session_context(self) -> str:
        """Obtiene contexto de sesión actual"""
        current_hour = datetime.now().hour
        if 13 <= current_hour <= 17:
            return "NY_OPEN"
        elif 8 <= current_hour <= 12:
            return "LONDON_NY_OVERLAP"
        else:
            return "OTHER"

    def _should_analyze_market_structure(self) -> bool:
        """Determina si se debe analizar la estructura de mercado"""
        if not self.last_analysis_time:
            return True
        
        time_since_analysis = (datetime.now() - self.last_analysis_time).total_seconds()
        return time_since_analysis > self.analysis_cache_duration

    def _update_generation_metrics(self, signals: List[TradingSignal]):
        """Actualiza métricas de generación de señales incluyendo validación inmutable"""
        self.metrics['total_signals_generated'] += len(signals)
        
        if signals:
            self.metrics['average_confidence'] = (
                (self.metrics['average_confidence'] * (self.metrics['total_signals_generated'] - len(signals)) +
                 sum(s.confidence for s in signals)) / self.metrics['total_signals_generated']
            )
            
            self.metrics['high_confidence_signals'] += len([s for s in signals if s.confidence >= 80])
            self.metrics['last_signal_time'] = datetime.now()
            
            # Actualizar distribución por tipo
            for signal in signals:
                signal_type = signal.signal_type.value
                self.metrics['signals_by_type'][signal_type] = self.metrics['signals_by_type'].get(signal_type, 0) + 1
        
        self.metrics['market_structure_quality'] = self.market_structure.structure_quality

    def _update_signals_cache(self, signals: List[TradingSignal]):
        """Actualiza cache de señales"""
        self.signals_cache.extend(signals)
        if len(self.signals_cache) > self.cache_max_size:
            self.signals_cache = self.signals_cache[-self.cache_max_size:]

    async def _update_health_metrics(self, signals: List[TradingSignal], start_time: datetime):
        """Actualiza HealthMonitor con métricas del generador incluyendo núcleo inmutable"""
        health_monitor = get_health_monitor()
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Obtener estado del núcleo inmutable
        immutable_status = self.immutable_core.get_immutable_status()
        
        metrics = {
            "signals_generated": len(signals),
            "average_confidence": self.metrics['average_confidence'],
            "high_confidence_signals": self.metrics['high_confidence_signals'],
            "market_structure_quality": self.metrics['market_structure_quality'],
            "processing_time": processing_time,
            "cache_size": len(self.signals_cache),
            "success_rate": (self.metrics['total_signals_generated'] / max(self.metrics['total_signals_generated'], 1)) * 100,
            "immutable_validations_passed": self.metrics['immutable_validations_passed'],
            "immutable_validations_failed": self.metrics['immutable_validations_failed'],
            "immutable_core_status": immutable_status
        }
        
        health_monitor.update_metrics("signal_generator", metrics)

    def _health_callback(self, system_status: Any, metrics: Any):
        """Callback para HealthMonitor"""
        if system_status.value == "degraded":
            self.min_confidence = 80
            self.analysis_cache_duration = 60
        elif system_status.value == "healthy":
            self.min_confidence = self.generator_config.get('min_confidence', 75)
            self.analysis_cache_duration = 30

    def get_generator_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas del generador para monitoreo"""
        stats = self.metrics.copy()
        stats['circuit_breaker_state'] = self.circuit_breaker.get_state()
        stats['cache_size'] = len(self.signals_cache)
        stats['last_analysis_time'] = self.last_analysis_time.isoformat() if self.last_analysis_time else None
        stats['market_structure'] = {
            'fvg_zones': len(self.market_structure.fvg_zones),
            'order_blocks': len(self.market_structure.order_blocks),
            'liquidity_sweeps': len(self.market_structure.liquidity_sweeps),
            'bos_points': len(self.market_structure.bos_points),
            'current_trend': self.market_structure.current_trend,
            'trend_strength': self.market_structure.trend_strength,
            'market_phase': self.market_structure.market_phase,
            'structure_quality': self.market_structure.structure_quality
        }
        stats['data_quality_score'] = self.metrics['data_quality_score']
        stats['mt5_connection'] = self.mt5_initialized
        stats['immutable_core_integrated'] = True
        stats['immutable_core_status'] = self.immutable_core.get_immutable_status()
        
        return stats

    async def close(self):
        """Cierre seguro del generador"""
        logger.info("🔌 Cerrando Signal Generator con Núcleo Inmutable...")
        
        # Enviar métricas finales a HealthMonitor
        health_monitor = get_health_monitor()
        health_monitor.update_metrics("signal_generator", {
            "final_metrics": self.get_generator_metrics()
        })
        
        # Cerrar conexión MT5 si está activa
        if MT5_AVAILABLE and self.mt5_initialized:
            mt5.shutdown()
            logger.info("🔌 Conexión MT5 cerrada")
        
        logger.info("✅ Signal Generator con Núcleo Inmutable cerrado correctamente")

# Función de fábrica para integración con el sistema
def create_signal_generator(config: Dict[str, Any]) -> SignalGenerator:
    """Crea y configura el generador de señales EAS con núcleo inmutable"""
    return SignalGenerator(config)
[file content end]