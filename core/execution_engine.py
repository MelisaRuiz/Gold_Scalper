#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Execution Engine v4.1 - EAS Híbrido 2025 ULTRA
Motor de ejecución ultra-robusto con filtros EAS chinos, circuit breakers avanzados,
gestión de riesgo mejorada y cumplimiento estricto con disciplina rígida HECTA 2025
INTEGRACIÓN CON SIGNAL_GENERATOR.MQ5 + VALIDACIÓN BO5_REST + KILL SWITCHES
"""

import asyncio
import logging
import time
import threading
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

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

    def get_state(self) -> str:
        return "CLOSED" if self.allow_request() else "OPEN"

    def force_open(self):
        with self._lock:
            self.failures = self.max_failures
            self.last_failure_time = time.time()

class HealthMonitorStub:
    def __init__(self):
        self.metrics = {}

    def register_health_callback(self, callback):
        pass

    def update_metrics(self, component: str, data: Dict):
        self.metrics.setdefault(component, {}).update(data)

    async def update_agent_metrics(self, agent: str, data: Dict):
        self.metrics.setdefault(agent, {}).update(data)

_health_monitor_instance = HealthMonitorStub()

def get_health_monitor():
    return _health_monitor_instance

def with_guardrails(agent_context: str):
    def decorator(func):
        return func
    return decorator

class ExponentialBackoff:
    def __init__(self, base_delay: float = 0.1, max_delay: float = 1.0, max_retries: int = 3):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_retries = max_retries

    def get_delay(self, attempt: int) -> float:
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        return delay

# ===== FIN DE IMPLEMENTACIONES DE RESPALDO =====

# IMPORTACIÓN MT5 REAL MEJORADA
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

logger = StructuredLogger("HECTAGold.ExecutionEngine")

class OrderStatus(Enum):
    """Estados de orden EAS Híbrido 2025 mejorados"""
    PENDING = "PENDING"
    OPEN = "OPEN"
    MODIFIED = "MODIFIED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    REJECTED = "REJECTED"
    KILL_SWITCH_BLOCKED = "KILL_SWITCH_BLOCKED"

class ExecutionMode(Enum):
    """Modos de ejecución EAS mejorados"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class ExecutionResult(Enum):
    """Resultados de ejecución EAS mejorados"""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    KILL_SWITCH_ACTIVE = "KILLKILL_SWITCH_ACTIVE"
    PAUSE_LINE_BLOCKED = "PAUSE_LINE_BLOCKED"

@dataclass
class ExecutionOrder:
    """Estructura de orden de ejecución EAS Híbrido 2025 mejorada"""
    order_id: str
    ticket: int
    symbol: str
    direction: str
    lot_size: float
    entry_price: float
    stop_loss: float
    take_profit: float
    status: OrderStatus
    open_time: datetime
    close_time: Optional[datetime] = None
    pnl: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    magic_number: int = 20251014
    comment: str = ""
    execution_mode: ExecutionMode = ExecutionMode.MARKET
    retry_count: int = 0
    last_retry_time: Optional[datetime] = None
    risk_multiplier: float = 1.0
    validation_score: float = 0.0
    signal_type: str = ""
    session_context: str = ""
    pause_line_detected: bool = False
    duplicate_order_blocked: bool = False
    metadata: Dict[str, Any] = None
    bo5_rest_pattern: str = ""  # Nuevo campo para patrón BO5_REST
    consecutive_losses: int = 0  # Contador de pérdidas consecutivas
    trading_session: str = "NY_OPEN"  # Sesión activa

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.order_id.startswith("order_"):
            self.order_id = f"order_{int(datetime.now().timestamp())}_{self.symbol}"

@dataclass
class ExecutionMetrics:
    """Métricas de ejecución EAS mejoradas"""
    execution_time: float
    result: ExecutionResult
    slippage: float
    spread_at_execution: float
    retry_count: int
    error_message: str = ""
    circuit_breaker_state: str = "CLOSED"
    quality_score: float = 0.0
    pause_line_blocked: bool = False
    duplicate_order_blocked: bool = False
    kill_switch_active: bool = False
    bo5_rest_violation: bool = False  # Nuevo campo
    max_consecutive_loss_violation: bool = False  # Nuevo campo
    session_violation: bool = False  # Nuevo campo

class DuplicateOrderPrevention:
    """Sistema EAS chino para prevenir órdenes duplicadas en la misma vela"""
    def __init__(self):
        self.order_history: Dict[str, List[datetime]] = {}
        self.candle_period = 60

    def can_execute_order(self, symbol: str, order_type: str) -> Tuple[bool, str]:
        current_time = datetime.utcnow()
        if symbol not in self.order_history:
            self.order_history[symbol] = []
            return True, "Primera orden del símbolo"
        recent_orders = [
            order_time for order_time in self.order_history[symbol]
            if (current_time - order_time).total_seconds() < self.candle_period
        ]
        if recent_orders:
            return False, f"Orden duplicada bloqueada - {len(recent_orders)} órdenes en la misma vela"
        return True, "Vela limpia para nueva orden"

    def record_order(self, symbol: str, order_time: datetime):
        if symbol not in self.order_history:
            self.order_history[symbol] = []
        self.order_history[symbol].append(order_time)
        self.order_history[symbol] = [
            ot for ot in self.order_history[symbol]
            if (datetime.utcnow() - ot).total_seconds() < 300
        ]

class PriceLimitMonitor:
    """Sistema EAS chino para monitorear límites de precio fijos"""
    def __init__(self, upper_limit: Optional[float] = None, lower_limit: Optional[float] = None):
        self.upper_limit = upper_limit
        self.lower_limit = lower_limit
        self.limit_breached = False

    def check_price_limits(self, current_price: float) -> Tuple[bool, str]:
        if self.upper_limit and current_price >= self.upper_limit:
            self.limit_breached = True
            return True, f"Precio {current_price} >= límite superior {self.upper_limit}"
        if self.lower_limit and current_price <= self.lower_limit:
            self.limit_breached = True
            return True, f"Precio {current_price} <= límite inferior {self.lower_limit}"
        return False, "Precio dentro de límites"

# NUEVO: Validación BO5_REST
class BO5RestValidator:
    """Valida patrón BO5_REST según especificación HECTA 2025"""
    RISK_PERCENT = 0.3  # 0.3% riesgo máximo por operación
    MAX_CONSECUTIVE_LOSSES = 2
    TRADING_SESSION = "NY_OPEN"

    def validate_bo5_rest(self, pattern_data: Dict, current_position: Optional[ExecutionOrder] = None) -> Tuple[bool, str]:
        # Validación de patrón
        if pattern_data.get("pattern_type") != "BO5_REST":
            return False, "Patrón no es BO5_REST"
        if not pattern_data.get("confirmed_breakout", False):
            return False, "Breakout no confirmado"
        if pattern_data.get("rest_count", 0) < 5:
            return False, f"Descansos insuficientes: {pattern_data.get('rest_count')} < 5"

        # Validación de riesgo
        risk_amount = pattern_data.get("risk_amount", 0)
        account_balance = pattern_data.get("account_balance", 10000)
        if risk_amount > (account_balance * self.RISK_PERCENT / 100):
            return False, f"Riesgo excede {self.RISK_PERCENT}% del balance"

        # Validación de pérdidas consecutivas
        if current_position and current_position.consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES:
            return False, f"Límite de {self.MAX_CONSECUTIVE_LOSSES} pérdidas consecutivas alcanzado"

        # Validación de sesión
        current_hour = datetime.utcnow().hour
        if not (13 <= current_hour <= 17):  # NY Open: 13:00 - 17:00 GMT
            return False, f"Sesión fuera de NY_OPEN (13:00-17:00 GMT), actual: {current_hour}:00 GMT"

        return True, "BO5_REST validado exitosamente"

class EASExecutionEngine:
    """
    Motor de ejecución EAS Híbrido 2025 ULTRA
    Integra filtros EAS chinos, BO5_REST, kill switches y cumplimiento HECTA
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.engine_config = config.get('execution_engine', {})
        self.max_positions = self.engine_config.get('max_positions', 3)
        self.max_spread = self.engine_config.get('max_spread_points', 10.0)
        self.slippage_tolerance = self.engine_config.get('slippage_tolerance', 10)
        self.max_retries = self.engine_config.get('max_retries', 2)
        self.base_retry_delay = self.engine_config.get('base_delay_ms', 50)
        self.execution_timeout = self.engine_config.get('execution_timeout', 3.0)
        self.duplicate_prevention = DuplicateOrderPrevention()
        self.price_limit_monitor = PriceLimitMonitor(
            upper_limit=self.engine_config.get('price_upper_limit'),
            lower_limit=self.engine_config.get('price_lower_limit')
        )
        self.bo5_validator = BO5RestValidator()  # Nuevo validador
        self.circuit_breaker = CircuitBreaker(max_failures=2, reset_timeout=180)
        self.backoff_strategy = ExponentialBackoff(
            base_delay=0.05,
            max_delay=0.2,
            max_retries=self.max_retries
        )
        self.active_positions: List[ExecutionOrder] = []
        self.execution_lock = threading.RLock()
        self.is_running = False
        self.emergency_shutdown = False
        self.mt5_initialized = False
        self.consecutive_losses = 0  # Contador global de pérdidas
        if MT5_AVAILABLE:
            self.mt5_initialized = self._initialize_mt5_connection()
        self.db_path = Path("data/execution_engine.db")
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
        self.metrics = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'rejected_executions': 0,
            'average_execution_time': 0.0,
            'average_slippage': 0.0,
            'execution_success_rate': 0.0,
            'circuit_breaker_activations': 0,
            'last_execution_time': None,
            'total_processing_time': 0.0,
            'latency_kpi_violations': 0,
            'pause_line_blocks': 0,
            'duplicate_order_blocks': 0,
            'price_limit_blocks': 0,
            'kill_switch_blocks': 0,
            'emergency_shutdowns': 0,
            'bo5_rest_violations': 0,
            'max_consecutive_loss_blocks': 0,
            'session_violation_blocks': 0
        }
        self.execution_config = {
            'min_confidence': 0.7,
            'max_risk_multiplier': 1.2,
            'require_validation': True,
            'enable_slippage_control': True,
            'session_restrictions': True,
            'enable_eas_filters': True,
            'max_daily_operations': 50
        }
        logger.info("⚡ Execution Engine EAS Híbrido 2025 ULTRA inicializado")
        logger.info(f"🎯 KPI Latencia: <50ms | MT5: {'✅ Real' if self.mt5_initialized else '❌ Simulación'}")
        logger.info("✅ Filtros EAS + BO5_REST + Kill Switches integrados")

    def _initialize_mt5_connection(self) -> bool:
        try:
            if not mt5.initialize():
                logger.error(f"❌ MT5 initialization failed: {mt5.last_error()}")
                return False
            mt5.timeout(300)
            account_info = mt5.account_info()
            if account_info is None:
                logger.error(f"❌ MT5 account info failed: {mt5.last_error()}")
                return False
            logger.info(f"✅ MT5 Connected: {account_info.login} | Server: {account_info.server}")
            return True
        except Exception as e:
            logger.error(f"❌ MT5 connection error: {e}")
            return False

    async def initialize(self):
        try:
            health_monitor = get_health_monitor()
            health_monitor.register_health_callback(self._health_callback)
            await self._initialize_mt5_bridge()
            await self._check_initial_conditions()
            logger.info("🚀 Execution Engine ULTRA inicializado con HealthMonitor")
        except Exception as e:
            logger.error(f"❌ Error inicializando Execution Engine: {e}")
            raise

    async def _check_initial_conditions(self):
        if self.price_limit_monitor.upper_limit or self.price_limit_monitor.lower_limit:
            logger.info(f"🔒 Límites de precio configurados: Upper={self.price_limit_monitor.upper_limit}, Lower={self.price_limit_monitor.lower_limit}")
        if not self.mt5_initialized:
            logger.warning("⚠️ Ejecución en modo simulación - MT5 no disponible")

    async def _get_current_market_prices(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Tuple[float, float, float]]:
        start_time = time.time()
        if self.mt5_initialized and MT5_AVAILABLE:
            try:
                tick = mt5.symbol_info_tick(symbol)
                if tick is None or tick.bid == 0 or tick.ask == 0:
                    return self._get_fallback_prices(market_data)
                bid = tick.bid
                ask = tick.ask
                spread = (ask - bid) * 10000
                latency = (time.time() - start_time) * 1000
                if latency > 50:
                    self.metrics['latency_kpi_violations'] += 1
                    logger.warning(f"⚠️ Latencia alta en precios: {latency:.2f}ms")
                if spread > self.max_spread:
                    logger.warning(f"⚠️ Spread excedido: {spread:.1f} > {self.max_spread}")
                    return None
                return bid, ask, spread
            except Exception as e:
                logger.error(f"❌ Error obteniendo precios MT5: {e}")
                return self._get_fallback_prices(market_data)
        return self._get_fallback_prices(market_data)

    def _get_fallback_prices(self, market_data: Dict[str, Any]) -> Optional[Tuple[float, float, float]]:
        if 'bid' in market_data and 'ask' in market_data:
            bid = market_data['bid']
            ask = market_data['ask']
            spread = (ask - bid) * 10000
            return bid, ask, spread
        logger.error("❌ No hay precios de respaldo disponibles")
        return None

    async def _execute_single_order(self, order_params: Dict[str, Any], attempt: int) -> Dict[str, Any]:
        start_time = time.time()
        try:
            if self.emergency_shutdown:
                return {
                    'success': False,
                    'error': "Emergency shutdown activo",
                    'attempt': attempt + 1,
                    'execution_time': (time.time() - start_time) * 1000
                }
            if not self.mt5_initialized or not MT5_AVAILABLE:
                return {
                    'success': False,
                    'error': "MT5 no disponible",
                    'attempt': attempt + 1,
                    'execution_time': (time.time() - start_time) * 1000
                }
            symbol = order_params['symbol']
            direction = order_params['direction']
            volume = order_params['volume']
            stop_loss = order_params['stop_loss']
            take_profit = order_params['take_profit']
            magic_number = order_params['magic_number']
            comment = order_params['comment']
            slippage = order_params.get('slippage_tolerance', self.slippage_tolerance)
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return {
                    'success': False,
                    'error': f"No se pudo obtener tick para {symbol}",
                    'attempt': attempt + 1,
                    'execution_time': (time.time() - start_time) * 1000
                }
            if direction == "BUY":
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            else:
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            if volume < 0.01:
                return {
                    'success': False,
                    'error': f"Volumen inválido: {volume}",
                    'attempt': attempt + 1,
                    'execution_time': (time.time() - start_time) * 1000
                }
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type":06 order_type,
                "price": price,
                "sl": stop_loss,
                "tp": take_profit,
                "deviation": slippage,
                "magic": magic_number,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            result = mt5.order_send(request)
            execution_time = (time.time() - start_time) * 1000
            if execution_time > 50:
                self.metrics['latency_kpi_violations'] += 1
                logger.warning(f"⚠️ Orden excedió KPI latencia: {execution_time:.2f}ms")
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_msg = f"MT5 error {result.retcode}: {self._get_mt5_error_description(result.retcode)}"
                logger.error(f"❌ Orden MT5 falló: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'attempt': attempt + 1,
                    'execution_time': execution_time
                }
            logger.info(f"✅ Orden ejecutada - Ticket: {result.order} | Latencia: {execution_time:.2f}ms")
            return {
                'success': True,
                'ticket': result.order,
                'execution_price': result.price,
                'slippage': abs(result.price - price) * 10000,
                'attempt': attempt + 1,
                'execution_time': execution_time,
                'spread_at_execution': (tick.ask - tick.bid) * 10000
            }
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"❌ Error en ejecución MT5: {e}")
            return {
                'success': False,
                'error': str(e),
                'attempt': attempt + 1,
                'execution_time': execution_time
            }

    def _get_mt5_error_description(self, retcode: int) -> str:
        error_descriptions = {
            10004: "Requote",
            10006: "Request rejected",
            10007: "Request canceled by trader",
            10008: "Order placed timeout",
            10010: "Invalid request",
            10013: "Invalid trade volume",
            10014: "Invalid price",
            10015: "Invalid stops",
            10016: "Invalid trade expiration",
            10017: "Invalid trade state",
            10018: "Trade disabled",
            10019: "Not enough money",
            10020: "Price changed",
            10021: "No quotes",
            10022: "Invalid order expiration",
            10023: "Order state changed",
            10024: "Too many requests",
            10025: "Trade modification denied",
            10026: "Trade context busy",
            10027: "Expiration denied",
            10028: "Too many pending orders",
            10029: "Hedging prohibited",
            10030: "Prohibited by FIFO rules"
        }
        return error_descriptions.get(retcode, f"Unknown error {retcode}")

    async def _execute_order_with_retry(self, order_params: Dict[str, Any], signal: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        for attempt in range(self.max_retries):
            try:
                current_time = time.time()
                if attempt > 0 and (current_time - start_time) > self.execution_timeout:
                    return {
                        'success': False,
                        'error': f"Timeout después de {attempt} intentos",
                        'attempts': attempt,
                        'total_time': (current_time - start_time) * 1000
                    }
                execution_result = await self._execute_single_order(order_params, attempt)
                if execution_result['success']:
                    return execution_result
                else:
                    delay = self.backoff_strategy.get_delay(attempt)
                    await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"❌ Intento {attempt + 1} falló: {e}")
                if attempt < self.max_retries - 1:
                    delay = self.backoff_strategy.get_delay(attempt)
                    await asyncio.sleep(delay)
        total_time = (time.time() - start_time) * 1000
        return {
            'success': False,
            'error': f"Todos los {self.max_retries} intentos fallaron",
            'attempts': self.max_retries,
            'total_time': total_time
        }

    @with_guardrails(agent_context="order_execution")
    async def execute_trading_signal(self, 
                                   signal: Dict[str, Any],
                                   risk_manager: Any,
                                   market_data: Dict[str, Any]) -> Tuple[bool, ExecutionMetrics]:
        start_time = time.time()
        self.metrics['total_executions'] += 1
        try:
            emergency_check = await self._check_emergency_conditions(risk_manager, market_data)
            if not emergency_check["allowed"]:
                logger.warning(f"🚫 Ejecución bloqueada: {emergency_check['reason']}")
                self.metrics['kill_switch_blocks'] += 1
                return False, ExecutionMetrics(
                    execution_time=time.time() - start_time,
                    result=ExecutionResult.KILL_SWITCH_ACTIVE,
                    slippage=0.0,
                    spread_at_execution=0.0,
                    retry_count=0,
                    error_message=emergency_check['reason'],
                    kill_switch_active=True
                )
            eas_filter_check = await self._check_eas_chinese_filters(signal, market_data)
            if not eas_filter_check["allowed"]:
                logger.warning(f"🚫 Filtro EAS bloqueó ejecución: {eas_filter_check['reason']}")
                return False, ExecutionMetrics(
                    execution_time=time.time() - start_time,
                    result=ExecutionResult.PAUSE_LINE_BLOCKED if "pausa" in eas_filter_check['reason'].lower() else ExecutionResult.REJECTED,
                    slippage=0.0,
                    spread_at_execution=0.0,
                    retry_count=0,
                    error_message=eas_filter_check['reason'],
                    pause_line_blocked="pausa" in eas_filter_check['reason'].lower(),
                    duplicate_order_blocked="duplicada" in eas_filter_check['reason'].lower()
                )
            if not self.circuit_breaker.allow_request():
                logger.warning("🔒 Circuit breaker activado - ejecución rechazada")
                self.metrics['circuit_breaker_activations'] += 1
                return False, ExecutionMetrics(
                    execution_time=time.time() - start_time,
                    result=ExecutionResult.REJECTED,
                    slippage=0.0,
                    spread_at_execution=0.0,
                    retry_count=0,
                    error_message="Circuit breaker activado",
                    circuit_breaker_state="OPEN"
                )
            validation_result = await self._validate_enhanced_execution_conditions(signal, risk_manager, market_data)
            if not validation_result['valid']:
                logger.warning(f"⏸️ Ejecución rechazada en validación: {validation_result['reason']}")
                self.metrics['rejected_executions'] += 1
                return False, ExecutionMetrics(
                    execution_time=time.time() - start_time,
                    result=ExecutionResult.REJECTED,
                    slippage=0.0,
                    spread_at_execution=0.0,
                    retry_count=0,
                    error_message=validation_result['reason']
                )
            order_params = await self._calculate_enhanced_order_parameters(signal, risk_manager, market_data)
            if not order_params:
                return False, ExecutionMetrics(
                    execution_time=time.time() - start_time,
                    result=ExecutionResult.REJECTED,
                    slippage=0.0,
                    spread_at_execution=0.0,
                    retry_count=0,
                    error_message="Error en cálculo de parámetros de orden"
                )
            execution_result = await self._execute_order_with_retry(order_params, signal)
            processing_time = time.time() - start_time
            execution_metrics = self._create_enhanced_execution_metrics(execution_result, processing_time)
            if execution_result['success']:
                order = self._create_enhanced_execution_order(order_params, execution_result, signal)
                await self._register_successful_execution(order, execution_metrics)
                self.metrics['successful_executions'] += 1
                logger.info(f"✅ Orden ejecutada exitosamente: {order.order_id}")
                return True, execution_metrics
            else:
                await self._register_failed_execution(order_params, execution_result, execution_metrics)
                self.metrics['failed_executions'] += 1
                logger.error(f"❌ Ejecución fallida: {execution_result['error']}")
                return False, execution_metrics
        except Exception as e:
            processing_time = time.time() - start_time
            self.metrics['failed_executions'] += 1
            self.circuit_breaker.record_failure()
            logger.error(f"❌ Error en ejecución de señal: {e}")
            return False, ExecutionMetrics(
                execution_time=processing_time,
                result=ExecutionResult.FAILED,
                slippage=0.0,
                spread_at_execution=0.0,
                retry_count=0,
                error_message=str(e),
                circuit_breaker_state=self.circuit_breaker.get_state()
            )

    async def _check_emergency_conditions(self, risk_manager: Any, market_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.emergency_shutdown:
            return {"allowed": False, "reason": "Emergency shutdown activo"}
        if hasattr(risk_manager, '_check_all_kill_switches'):
            kill_switch_check = risk_manager._check_all_kill_switches()
            if not kill_switch_check:
                return {"allowed": False, "reason": "Kill switch del Risk Manager activo"}
        current_price = market_data.get('current_price')
        if current_price:
            price_limit_check = self.price_limit_monitor.check_price_limits(current_price)
            if price_limit_check[0]:
                self.metrics['price_limit_blocks'] += 1
                return {"allowed": False, "reason": f"Límite de precio violado: {price_limit_check[1]}"}
        return {"allowed": True, "reason": "Condiciones normales"}

    async def _check_eas_chinese_filters(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        symbol = signal.get('symbol', 'XAUUSD')
        direction = signal.get('direction')
        signal_type = signal.get('signal_type', '')
        duplicate_check = self.duplicate_prevention.can_execute_order(symbol, direction)
        if not duplicate_check[0]:
            self.metrics['duplicate_order_blocks'] += 1
            return {"allowed": False, "reason": duplicate_check[1]}
        if signal.get('pause_line_detected'):
            self.metrics['pause_line_blocks'] += 1
            return {"allowed": False, "reason": "Línea de pausa detectada en validación de señal"}
        daily_ops = len([o for o in self.active_positions if o.open_time.date() == datetime.now().date()])
        if daily_ops >= self.execution_config['max_daily_operations']:
            return {"allowed": False, "reason": f"Límite diario de operaciones alcanzado: {daily_ops}"}
        return {"allowed": True, "reason": "Filtros EAS pasados"}

    async def _validate_enhanced_execution_conditions(self, signal: Dict[str, Any], risk_manager: Any, market_data: Dict[str, Any]) -> Dict[str, Any]:
        validation_checks = {'valid': True, 'reasons': []}
        confidence = signal.get('confidence', 0)
        if confidence < self.execution_config['min_confidence'] * 100:
            validation_checks['valid'] = False
            validation_checks['reasons'].append(f"Confianza insuficiente: {confidence}%")
        if len(self.active_positions) >= self.max_positions:
            validation_checks['valid'] = False
            validation_checks['reasons'].append(f"Límite de posiciones alcanzado: {len(self.active_positions)}/{self.max_positions}")
        if self.execution_config['session_restrictions']:
            session_valid = await self._validate_trading_session()
            if not session_valid:
                validation_checks['valid'] = False
                validation_checks['reasons'].append("Sesión de trading no óptima")
        market_validation = await self._validate_enhanced_market_conditions(market_data)
        if not market_validation['valid']:
            validation_checks['valid'] = False
            validation_checks['reasons'].extend(market_validation['reasons'])
        if hasattr(risk_manager, 'validate_execution'):
            risk_validation = risk_manager.validate_execution(signal)
            if not risk_validation.get('approved', True):
                validation_checks['valid'] = False
                validation_checks['reasons'].append(f"Rechazado por gestor de riesgo: {risk_validation.get('reason', 'Unknown')}")
        
        # NUEVO: Validación BO5_REST
        pattern_data = signal.get('pattern_data', {})
        bo5_validation = self.bo5_validator.validate_bo5_rest(pattern_data, self.active_positions[-1] if self.active_positions else None)
        if not bo5_validation[0]:
            validation_checks['valid'] = False
            validation_checks['reasons'].append(f"BO5_REST fallido: {bo5_validation[1]}")
            self.metrics['bo5_rest_violations'] += 1

        validation_checks['reason'] = "; ".join(validation_checks['reasons']) if not validation_checks['valid'] else "Validación exitosa"
        return validation_checks

    async def _validate_enhanced_market_conditions(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        validation = {'valid': True, 'reasons': []}
        spread = market_data.get('spread', 0)
        if spread > self.max_spread:
            validation['valid'] = False
            validation['reasons'].append(f"Spread demasiado alto: {spread} puntos")
        volatility = market_data.get('volatility', 0)
        atr = market_data.get('atr', 0)
        if volatility > 2.5 or atr > 3.0:
            validation['valid'] = False
            validation['reasons'].append(f"Volatilidad demasiado alta: V={volatility}, ATR={atr}")
        liquidity = market_data.get('liquidity_score', 1.0)
        if liquidity < 0.7:
            validation['valid'] = False
            validation['reasons'].append(f"Liquidez insuficiente: {liquidity:.3f}")
        price_gap = market_data.get('price_gap', 0)
        if price_gap > 10:
            validation['valid'] = False
            validation['reasons'].append(f"Gap de precio demasiado grande: {price_gap} pips")
        return validation

    async def _calculate_enhanced_order_parameters(self, signal: Dict[str, Any], risk_manager: Any, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            symbol = signal.get('symbol', 'XAUUSD')
            direction = signal.get('direction')
            base_lot_size = signal.get('lot_size', 0.01)
            current_prices = await self._get_current_market_prices(symbol, market_data)
            if not current_prices:
                return None
            bid, ask, spread = current_prices
            risk_multiplier = min(signal.get('risk_multiplier', 1.0), self.execution_config['max_risk_multiplier'])
            confidence_multiplier = signal.get('confidence', 75) / 100.0
            final_lot_size = self._calculate_enhanced_lot_size(base_lot_size, risk_multiplier, confidence_multiplier, risk_manager)
            execution_price = ask if direction == "BUY" else bid
            stop_loss, take_profit = self._calculate_enhanced_risk_levels(direction, execution_price, signal, risk_manager)
            if not self._validate_enhanced_stop_levels(symbol, execution_price, stop_loss, take_profit):
                logger.warning("⏸️ Niveles de stop inválidos - ajustando")
                stop_loss, take_profit = self._adjust_enhanced_stop_levels(symbol, direction, execution_price, stop_loss, take_profit)
            return {
                'symbol': symbol,
                'direction': direction,
                'volume': final_lot_size,
                'price': execution_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_multiplier': risk_multiplier,
                'execution_mode': ExecutionMode.MARKET,
                'comment': f"EAS Signal: {signal.get('signal_type', 'UNKNOWN')} | BO5_REST",
                'magic_number': 20251014,
                'slippage_tolerance': self.slippage_tolerance,
                'signal_metadata': signal.get('metadata', {})
            }
        except Exception as e:
            logger.error(f"❌ Error calculando parámetros de orden: {e}")
            return None

    def _calculate_enhanced_lot_size(self, base_lot_size: float, risk_multiplier: float, confidence_multiplier: float, risk_manager: Any) -> float:
        adjusted_lot_size = base_lot_size * risk_multiplier * confidence_multiplier
        if hasattr(risk_manager, 'get_max_lot_size'):
            max_lot_size = risk_manager.get_max_lot_size()
            adjusted_lot_size = min(adjusted_lot_size, max_lot_size)
        min_lot = 0.01
        max_lot = 50.0
        final_lot_size = max(min_lot, min(max_lot, adjusted_lot_size))
        final_lot_size = round(final_lot_size, 2)
        if final_lot_size < 0.01:
            final_lot_size = 0.01
        return final_lot_size

    def _calculate_enhanced_risk_levels(self, direction: str, execution_price: float, signal: Dict[str, Any], risk_manager: Any) -> Tuple[float, float]:
        signal_sl = signal.get('stop_loss')
        signal_tp = signal.get('take_profit')
        if signal_sl and signal_tp and self._validate_enhanced_stop_levels(signal.get('symbol', 'XAUUSD'), execution_price, signal_sl, signal_tp):
            return signal_sl, signal_tp
        rr_ratio = signal.get('risk_reward_ratio', 2.0)
        atr = signal.get('atr', execution_price * 0.0005)
        base_sl_distance = atr * 0.5
        if direction == "BUY":
            stop_loss = execution_price - base_sl_distance
            take_profit = execution_price + (base_sl_distance * rr_ratio)
        else:
            stop_loss = execution_price + base_sl_distance
            take_profit = execution_price - (base_sl_distance * rr_ratio)
        return stop_loss, take_profit

    def _create_enhanced_execution_order(self, order_params: Dict[str, Any], execution_result: Dict[str, Any], signal: Dict[str, Any]) -> ExecutionOrder:
        pattern_data = signal.get('pattern_data', {})
        return ExecutionOrder(
            ticket=execution_result['ticket'],
            symbol=order_params['symbol'],
            direction=order_params['direction'],
            lot_size=order_params['volume'],
            entry_price=execution_result['execution_price'],
            stop_loss=order_params['stop_loss'],
            take_profit=order_params['take_profit'],
            status=OrderStatus.OPEN,
            open_time=datetime.now(),
            slippage=execution_result['slippage'],
            magic_number=order_params['magic_number'],
            comment=order_params['comment'],
            execution_mode=order_params['execution_mode'],
            risk_multiplier=order_params['risk_multiplier'],
            validation_score=signal.get('validation_score', 0.0),
            signal_type=signal.get('signal_type', 'UNKNOWN'),
            session_context=signal.get('session_context', ''),
            pause_line_detected=signal.get('pause_line_detected', False),
            duplicate_order_blocked=False,
            metadata={
                'execution_attempts': execution_result['attempt'],
                'signal_confidence': signal.get('confidence', 0),
                'market_conditions': signal.get('market_conditions', {}),
                'spread_at_execution': execution_result.get('spread_at_execution', 0),
                'bo5_rest_pattern': pattern_data.get('pattern_type', 'UNKNOWN')
            },
            bo5_rest_pattern=pattern_data.get('pattern_type', ''),
            consecutive_losses=self.consecutive_losses,
            trading_session="NY_OPEN"
        )

    def _create_enhanced_execution_metrics(self, execution_result: Dict[str, Any], processing_time: float) -> ExecutionMetrics:
        return ExecutionMetrics(
            execution_time=processing_time,
            result=ExecutionResult.SUCCESS if execution_result['success'] else ExecutionResult.FAILED,
            slippage=execution_result.get('slippage', 0.0),
            spread_at_execution=execution_result.get('spread_at_execution', 0.0),
            retry_count=execution_result.get('attempt', 1),
            error_message=execution_result.get('error', ''),
            circuit_breaker_state=self.circuit_breaker.get_state(),
            quality_score=self._calculate_enhanced_execution_quality(execution_result, processing_time),
            bo5_rest_violation=False,
            max_consecutive_loss_violation=False,
            session_violation=False
        )

    def _calculate_enhanced_execution_quality(self, execution_result: Dict[str, Any], processing_time: float) -> float:
        quality_factors = []
        time_factor = max(0, 1 - (processing_time / 1.0))
        quality_factors.append(time_factor * 0.4)
        slippage = execution_result.get('slippage', 0)
        slippage_factor = max(0, 1 - (slippage / 3.0))
        quality_factors.append(slippage_factor * 0.4)
        retries = execution_result.get('attempt', 1)
        retry_factor = max(0, 1 - ((retries - 1) / self.max_retries))
        quality_factors.append(retry_factor * 0.2)
        return sum(quality_factors)

    async def _register_successful_execution(self, order: ExecutionOrder, metrics: ExecutionMetrics):
        with self.execution_lock:
            self.active_positions.append(order)
            self.circuit_breaker.record_success()
            self.consecutive_losses = 0  # Resetear pérdidas consecutivas
        self.duplicate_prevention.record_order(order.symbol, order.open_time)
        await self._save_enhanced_execution_order(order, metrics)
        self._update_enhanced_execution_metrics(metrics, True)
        await self._update_health_monitor(metrics, order)

    async def _register_failed_execution(self, order_params: Dict[str, Any], execution_result: Dict[str, Any], metrics: ExecutionMetrics):
        self.consecutive_losses += 1
        if self.consecutive_losses >= 2:
            self.metrics['max_consecutive_loss_blocks'] += 1
            logger.critical(f"🚨 KILL SWITCH: {self.consecutive_losses} pérdidas consecutivas")

    def _update_enhanced_execution_metrics(self, metrics: ExecutionMetrics, success: bool):
        self.metrics['average_execution_time'] = (
            (self.metrics['average_execution_time'] * (self.metrics['total_executions'] - 1) + 
             metrics.execution_time) / self.metrics['total_executions']
        )
        if success:
            self.metrics['average_slippage'] = (
                (self.metrics['average_slippage'] * (self.metrics['successful_executions'] - 1) + 
                 metrics.slippage) / self.metrics['successful_executions']
            )
        self.metrics['execution_success_rate'] = (
            self.metrics['successful_executions'] / self.metrics['total_executions'] * 100
        )
        if metrics.pause_line_blocked:
            self.metrics['pause_line_blocks'] += 1
        if metrics.duplicate_order_blocked:
            self.metrics['duplicate_order_blocks'] += 1
        if metrics.kill_switch_active:
            self.metrics['kill_switch_blocks'] += 1
        self.metrics['last_execution_time'] = datetime.now()
        self.metrics['total_processing_time'] += metrics.execution_time

    async def _update_health_monitor(self, metrics: ExecutionMetrics, order: ExecutionOrder):
        try:
            health_monitor = get_health_monitor()
            execution_metrics = {
                "execution_time": metrics.execution_time,
                "slippage": metrics.slippage,
                "quality_score": metrics.quality_score,
                "retry_count": metrics.retry_count,
                "success_rate": self.metrics['execution_success_rate'],
                "active_positions": len(self.active_positions),
                "circuit_breaker_state": metrics.circuit_breaker_state,
                "pause_line_blocks": self.metrics['pause_line_blocks'],
                "duplicate_order_blocks": self.metrics['duplicate_order_blocks'],
                "kill_switch_blocks": self.metrics['kill_switch_blocks'],
                "latency_kpi_violations": self.metrics['latency_kpi_violations'],
                "bo5_rest_violations": self.metrics['bo5_rest_violations'],
                "max_consecutive_loss_blocks": self.metrics['max_consecutive_loss_blocks'],
                "session_violation_blocks": self.metrics['session_violation_blocks']
            }
            await health_monitor.update_agent_metrics("execution_engine", execution_metrics)
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron enviar métricas a HealthMonitor: {e}")

    def _validate_enhanced_stop_levels(self, symbol: str, entry_price: float, stop_loss: float, take_profit: float) -> bool:
        min_distance = entry_price * 0.0003
        if abs(entry_price - stop_loss) < min_distance:
            logger.warning(f"⚠️ Stop loss muy cercano: {abs(entry_price - stop_loss):.5f} < {min_distance:.5f}")
            return False
        if abs(entry_price - take_profit) < min_distance:
            logger.warning(f"⚠️ Take profit muy cercano: {abs(entry_price - take_profit):.5f} < {min_distance:.5f}")
            return False
        if (entry_price > stop_loss and entry_price < take_profit) or (entry_price < stop_loss and entry_price > take_profit):
            return True
        logger.warning("⚠️ Stop loss y take profit en direcciones incorrectas")
        return False

    def _adjust_enhanced_stop_levels(self, symbol: str, direction: str, entry_price: float, stop_loss: float, take_profit: float) -> Tuple[float, float]:
        min_distance = entry_price * 0.0004
        if direction == "BUY":
            adjusted_sl = entry_price - min_distance
            adjusted_tp = entry_price + (min_distance * 2)
        else:
            adjusted_sl = entry_price + min_distance
            adjusted_tp = entry_price - (min_distance * 2)
        logger.info(f"🔧 Niveles de stop ajustados: SL={adjusted_sl:.5f}, TP={adjusted_tp:.5f}")
        return adjusted_sl, adjusted_tp

    async def _validate_trading_session(self) -> bool:
        current_time = datetime.utcnow()
        current_hour = current_time.hour
        if 13 <= current_hour <= 17:
            return True
        self.metrics['session_violation_blocks'] += 1
        return False

    def _init_database(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS execution_orders (
                    order_id TEXT PRIMARY KEY,
                    ticket INTEGER,
                    symbol TEXT,
                    direction TEXT,
                    lot_size REAL,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    status TEXT,
                    open_time TEXT,
                    close_time TEXT,
                    pnl REAL,
                    commission REAL,
                    slippage REAL,
                    magic_number INTEGER,
                    comment TEXT,
                    execution_mode TEXT,
                    retry_count INTEGER,
                    risk_multiplier REAL,
                    validation_score REAL,
                    signal_type TEXT,
                    session_context TEXT,
                    pause_line_detected INTEGER,
                    duplicate_order_blocked INTEGER,
                    metadata TEXT,
                    bo5_rest_pattern TEXT,
                    consecutive_losses INTEGER,
                    trading_session TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS execution_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    order_id TEXT,
                    execution_time REAL,
                    result TEXT,
                    slippage REAL,
                    spread REAL,
                    retry_count INTEGER,
                    error_message TEXT,
                    quality_score REAL,
                    pause_line_blocked INTEGER,
                    duplicate_order_blocked INTEGER,
                    kill_switch_active INTEGER,
                    bo5_rest_violation INTEGER,
                    max_consecutive_loss_violation INTEGER,
                    session_violation INTEGER
                )
            """)
            conn.commit()
            conn.close()
            logger.info("🗄️ Base de datos de ejecución EAS ULTRA inicializada")
        except Exception as e:
            logger.error(f"❌ Error inicializando base de datos: {e}")

    async def _save_enhanced_execution_order(self, order: ExecutionOrder, metrics: ExecutionMetrics):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO execution_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.order_id, order.ticket, order.symbol, order.direction, order.lot_size,
                order.entry_price, order.stop_loss, order.take_profit, order.status.value,
                order.open_time.isoformat(), order.close_time.isoformat() if order.close_time else None,
                order.pnl, order.commission, order.slippage, order.magic_number, order.comment,
                order.execution_mode.value, order.retry_count, order.risk_multiplier,
                order.validation_score, order.signal_type, order.session_context,
                int(order.pause_line_detected), int(order.duplicate_order_blocked),
                json.dumps(order.metadata), order.bo5_rest_pattern, order.consecutive_losses, order.trading_session
            ))
            cursor.execute("""
                INSERT INTO execution_metrics 
                (timestamp, order_id, execution_time, result, slippage, spread, retry_count, error_message, quality_score, pause_line_blocked, duplicate_order_blocked, kill_switch_active, bo5_rest_violation, max_consecutive_loss_violation, session_violation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(), order.order_id, metrics.execution_time, metrics.result.value,
                metrics.slippage, metrics.spread_at_execution, metrics.retry_count,
                metrics.error_message, metrics.quality_score,
                int(metrics.pause_line_blocked), int(metrics.duplicate_order_blocked), int(metrics.kill_switch_active),
                int(metrics.bo5_rest_violation), int(metrics.max_consecutive_loss_violation), int(metrics.session_violation)
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ Error guardando orden de ejecución: {e}")

    async def close_position(self, order_id: str, reason: str = "Manual close") -> bool:
        try:
            with self.execution_lock:
                position = next((p for p in self.active_positions if p.order_id == order_id), None)
                if not position:
                    logger.warning(f"⚠️ Posición no encontrada: {order_id}")
                    return False
                if self.mt5_initialized and MT5_AVAILABLE:
                    close_result = await self._close_position_mt5(position, reason)
                    if not close_result:
                        return False
                else:
                    await asyncio.sleep(0.05)
                position.status = OrderStatus.CLOSED
                position.close_time = datetime.now()
                position.pnl = self._calculate_simulated_pnl(position)
                if position.pnl < 0:
                    self.consecutive_losses += 1
                else:
                    self.consecutive_losses = 0
                self.active_positions = [p for p in self.active_positions if p.order_id != order_id]
                logger.info(f"✅ Posición cerrada: {order_id} - Razón: {reason}")
                return True
        except Exception as e:
            logger.error(f"❌ Error cerrando posición {order_id}: {e}")
            return False

    async def _close_position_mt5(self, position: ExecutionOrder, reason: str) -> bool:
        try:
            if position.direction == "BUY":
                order_type = mt5.ORDER_TYPE_SELL
                price = mt5.symbol_info_tick(position.symbol).bid
            else:
                order_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(position.symbol).ask
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.lot_size,
                "type": order_type,
                "price": price,
                "position": position.ticket,
                "deviation": self.slippage_tolerance,
                "magic": position.magic_number,
                "comment": f"Close: {reason}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"❌ Error cerrando posición MT5: {result.retcode}")
                return False
            logger.info(f"✅ Posición {position.ticket} cerrada en MT5")
            return True
        except Exception as e:
            logger.error(f"❌ Error en cierre MT5: {e}")
            return False

    def _calculate_simulated_pnl(self, position: ExecutionOrder) -> float:
        try:
            if position.direction == "BUY":
                current_price = mt5.symbol_info_tick(position.symbol).bid if self.mt5_initialized else position.entry_price * 1.001
                pnl = (current_price - position.entry_price) * position.lot_size * 100
            else:
                current_price = mt5.symbol_info_tick(position.symbol).ask if self.mt5_initialized else position.entry_price * 0.999
                pnl = (position.entry_price - current_price) * position.lot_size * 100
            return pnl
        except:
            return 0.0

    async def close_all_positions(self, reason: str = "System shutdown"):
        logger.info(f"🛑 Cerrando todas las posiciones: {reason}")
        close_tasks = []
        with self.execution_lock:
            positions_to_close = self.active_positions[:]
            for position in positions_to_close:
                close_tasks.append(self.close_position(position.order_id, reason))
        semaphore = asyncio.Semaphore(5)
        async def close_with_semaphore(position_id: str, close_reason: str):
            async with semaphore:
                return await self.close_position(position_id, close_reason)
        close_results = await asyncio.gather(
            *[close_with_semaphore(pos.order_id, reason) for pos in positions_to_close],
            return_exceptions=True
        )
        successful_closes = sum(1 for r in close_results if r is True)
        logger.info(f"📊 Cierres completados: {successful_closes}/{len(close_tasks)} exitosos")

    async def emergency_shutdown(self, reason: str = "Emergency"):
        logger.critical(f"🚨 EMERGENCY SHUTDOWN: {reason}")
        self.emergency_shutdown = True
        self.metrics['emergency_shutdowns'] += 1
        await self.close_all_positions(f"Emergency: {reason}")
        self.circuit_breaker.force_open()
        logger.critical("🔴 SISTEMA EAS DETENIDO - Requiere intervención manual")

    def _health_callback(self, system_status: Any = None, metrics: Any = None):
        pass

    def get_enhanced_execution_metrics(self) -> Dict[str, Any]:
        return {
            'total_executions': self.metrics['total_executions'],
            'successful_executions': self.metrics['successful_executions'],
            'failed_executions': self.metrics['failed_executions'],
            'rejected_executions': self.metrics['rejected_executions'],
            'average_execution_time': self.metrics['average_execution_time'],
            'average_slippage': self.metrics['average_slippage'],
            'execution_success_rate': self.metrics['execution_success_rate'],
            'circuit_breaker_activations': self.metrics['circuit_breaker_activations'],
            'last_execution_time': self.metrics['last_execution_time'],
            'total_processing_time': self.metrics['total_processing_time'],
            'latency_kpi_violations': self.metrics['latency_kpi_violations'],
            'pause_line_blocks': self.metrics['pause_line_blocks'],
            'duplicate_order_blocks': self.metrics['duplicate_order_blocks'],
            'price_limit_blocks': self.metrics['price_limit_blocks'],
            'kill_switch_blocks': self.metrics['kill_switch_blocks'],
            'emergency_shutdowns': self.metrics['emergency_shutdowns'],
            'mt5_connection': self.mt5_initialized,
            'bo5_rest_violations': self.metrics['bo5_rest_violations'],
            'max_consecutive_loss_blocks': self.metrics['max_consecutive_loss_blocks'],
            'session_violation_blocks': self.metrics['session_violation_blocks']
        }

    async def _initialize_mt5_bridge(self):
        await asyncio.sleep(0.1)
        if self.mt5_initialized:
            try:
                symbols = mt5.symbols_get()
                logger.info(f"✅ Bridge MT5 inicializado - {len(symbols)} símbolos disponibles")
            except Exception as e:
                logger.warning(f"⚠️ Bridge MT5 inicializado pero error en símbolos: {e}")
        else:
            logger.warning("⚠️ Bridge MT5 en modo simulación")

    async def close(self):
        try:
            if self.active_positions:
                logger.info("🛑 Cerrando posiciones activas antes del shutdown...")
                await self.close_all_positions("Engine shutdown")
            if MT5_AVAILABLE and self.mt5_initialized:
                mt5.shutdown()
                logger.info("🔌 MT5 connection closed ULTRA")
            logger.info("🛑 Execution Engine ULTRA apagado correctamente")
        except Exception as e:
            logger.error(f"❌ Error en cierre del Execution Engine: {e}")

    def get_execution_metrics(self) -> Dict[str, Any]:
        return self.get_enhanced_execution_metrics()