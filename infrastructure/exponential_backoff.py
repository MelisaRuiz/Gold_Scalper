#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exponential Backoff Mejorado - EAS Híbrido 2025
Sistema de reintentos adaptativo para scalping de alta frecuencia con integración de métricas
CORREGIDO Y FUNCIONAL
"""

import asyncio
import time
import random
from typing import Callable, Any, Optional, Dict, List, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import threading
from functools import wraps

# ===== IMPLEMENTACIÓN MÍNIMA DE LOGGER ESTRUCTURADO =====
try:
    from infrastructure.structured_logger import get_eas_logger, log_eas_warning, log_eas_error
except ImportError:
    # Fallback a logger estándar
    logging.basicConfig(level=logging.INFO)
    _fallback_logger = logging.getLogger("ExponentialBackoff")
    
    def get_eas_logger(name: str):
        return _fallback_logger
    
    def log_eas_warning(event_type: str, data: Dict[str, Any]):
        _fallback_logger.warning(f"{event_type}: {data}")
    
    def log_eas_error(event_type: str, data: Dict[str, Any]):
        _fallback_logger.error(f"{event_type}: {data}")

logger = get_eas_logger("ExponentialBackoff")

class BackoffStrategy(Enum):
    """Estrategias de backoff para diferentes escenarios"""
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci" 
    LINEAR = "linear"
    CONSTANT = "constant"
    AGGRESSIVE = "aggressive"  # Para recuperación rápida en HFT

@dataclass
class BackoffConfig:
    """Configuración de backoff para operaciones específicas"""
    operation_name: str
    max_retries: int = 3
    base_delay: float = 0.1  # 100ms base para HFT
    max_delay: float = 5.0   # 5 segundos máximo
    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    jitter: bool = True      # Jitter para evitar sincronización
    timeout: Optional[float] = None  # Timeout total de la operación
    
    # Umbrales específicos para trading
    critical_errors: List[str] = field(default_factory=list)
    retry_on_timeout: bool = True
    circuit_breaker_integration: bool = True
    
    # Métricas de performance
    target_latency_ms: float = 50.0  # Objetivo de latencia para scalping

@dataclass
class RetryMetrics:
    """Métricas de reintentos para monitoreo EAS"""
    operation_name: str
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    total_retry_delay: float = 0.0
    average_retry_time: float = 0.0
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    circuit_breaker_triggers: int = 0
    
    @property
    def success_rate(self) -> float:
        return self.successful_attempts / self.total_attempts if self.total_attempts > 0 else 0.0
    
    @property
    def estimated_impact_ms(self) -> float:
        """Impacto estimado en latencia para scalping"""
        return self.average_retry_time * self.failed_attempts

class ExponentialBackoff:
    """
    Sistema de reintentos mejorado para EAS Híbrido 2025
    Optimizado para scalping de alta frecuencia con métricas integradas
    """
    
    def __init__(self, config: BackoffConfig):
        self.config = config
        self.metrics = RetryMetrics(operation_name=config.operation_name)
        self._fibonacci_seq = self._generate_fibonacci(20)  # Pre-generar Fibonacci
        
        # Integración con circuit breaker
        if config.circuit_breaker_integration:
            try:
                from infrastructure.circuit_breaker import CircuitBreakerManager
                self.circuit_manager = CircuitBreakerManager()
                self.circuit = self.circuit_manager.create_circuit(
                    f"backoff_{config.operation_name}",
                    failure_threshold=3,
                    recovery_timeout=30
                )
            except ImportError:
                self.circuit = None
                log_eas_warning("CIRCUIT_BREAKER_UNAVAILABLE", {
                    "operation": config.operation_name,
                    "message": "Circuit breaker integration disabled"
                })
        else:
            self.circuit = None

    def _generate_fibonacci(self, n: int) -> List[int]:
        """Generar secuencia Fibonacci para backoff"""
        seq = [0, 1]
        for i in range(2, n):
            seq.append(seq[i-1] + seq[i-2])
        return seq

    def _calculate_delay(self, attempt: int) -> float:
        """Calcular delay basado en la estrategia seleccionada"""
        if attempt == 0:
            return 0
        
        if self.config.strategy == BackoffStrategy.EXPONENTIAL:
            delay = min(self.config.base_delay * (2 ** attempt), self.config.max_delay)
        
        elif self.config.strategy == BackoffStrategy.FIBONACCI:
            fib_index = min(attempt, len(self._fibonacci_seq) - 1)
            delay = min(self.config.base_delay * self._fibonacci_seq[fib_index], self.config.max_delay)
        
        elif self.config.strategy == BackoffStrategy.LINEAR:
            delay = min(self.config.base_delay * attempt, self.config.max_delay)
        
        elif self.config.strategy == BackoffStrategy.CONSTANT:
            delay = self.config.base_delay
        
        elif self.config.strategy == BackoffStrategy.AGGRESSIVE:
            # Backoff más agresivo para recuperación rápida
            delay = min(self.config.base_delay * (1.5 ** attempt), self.config.max_delay / 2)
        
        else:
            delay = self.config.base_delay

        # Aplicar jitter para evitar sincronización
        if self.config.jitter and delay > 0:
            delay = random.uniform(0.5 * delay, 1.5 * delay)
            
        return delay

    def _is_critical_error(self, error: Exception) -> bool:
        """Determinar si un error es crítico (no se reintenta)"""
        error_str = str(error).lower()
        
        # Errores críticos específicos de trading
        critical_patterns = [
            "insufficient margin",
            "invalid stops", 
            "market closed",
            "trade disabled",
            "not enough money",
            "invalid price"
        ] + self.config.critical_errors
        
        return any(pattern in error_str for pattern in critical_patterns)

    def _should_retry(self, error: Exception, attempt: int) -> bool:
        """Determinar si se debe reintentar basado en el error y el intento"""
        if attempt >= self.config.max_retries:
            return False
            
        if self._is_critical_error(error):
            return False
            
        if isinstance(error, asyncio.TimeoutError) and not self.config.retry_on_timeout:
            return False
            
        # Verificar circuit breaker si está integrado
        if self.circuit:
            circuit_state = self.circuit.get_state() if hasattr(self.circuit, 'get_state') else self.circuit.state
            if circuit_state == "open":
                return False
            
        return True

    async def execute_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecutar función asíncrona con backoff exponencial
        
        Args:
            func: Función asíncrona a ejecutar
            *args: Argumentos posicionales
            **kwargs: Argumentos keyword
            
        Returns:
            Resultado de la función
            
        Raises:
            Exception: Si todos los reintentos fallan
        """
        start_time = time.time()
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            self.metrics.total_attempts += 1
            
            try:
                # Verificar circuit breaker antes del intento
                if self.circuit:
                    circuit_state = self.circuit.get_state() if hasattr(self.circuit, 'get_state') else self.circuit.state
                    if circuit_state == "open":
                        raise Exception(f"Circuit breaker open for {self.config.operation_name}")
                
                # Calcular delay (0 para primer intento)
                delay = self._calculate_delay(attempt)
                if delay > 0:
                    await asyncio.sleep(delay)
                    self.metrics.total_retry_delay += delay
                
                # Ejecutar función con timeout si está configurado
                if self.config.timeout:
                    result = await asyncio.wait_for(
                        func(*args, **kwargs), 
                        timeout=self.config.timeout
                    )
                else:
                    result = await func(*args, **kwargs)
                
                # Éxito - actualizar métricas
                self.metrics.successful_attempts += 1
                self.metrics.consecutive_failures = 0
                
                # Log de éxito para operaciones críticas
                if attempt > 0:
                    log_eas_warning("RETRY_SUCCESS", {
                        "operation": self.config.operation_name,
                        "attempts": attempt + 1,
                        "total_delay": self.metrics.total_retry_delay,
                        "final_result": "SUCCESS"
                    })
                
                return result
                
            except Exception as e:
                last_error = e
                self.metrics.failed_attempts += 1
                self.metrics.consecutive_failures += 1
                self.metrics.last_error = str(e)
                
                # Log del error
                error_context = {
                    "operation": self.config.operation_name,
                    "attempt": attempt + 1,
                    "max_attempts": self.config.max_retries + 1,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "strategy": self.config.strategy.value
                }
                
                # Determinar si se reintenta
                if not self._should_retry(e, attempt):
                    log_eas_error("RETRY_CRITICAL_FAILURE", error_context)
                    break
                
                # Log warning para reintentos
                if attempt < self.config.max_retries:
                    log_eas_warning("RETRY_ATTEMPT", error_context)
                
                # Actualizar circuit breaker si está integrado
                if self.circuit:
                    self.circuit.record_failure()
        
        # Todos los reintentos fallaron
        total_time = time.time() - start_time
        self.metrics.average_retry_time = total_time / self.metrics.total_attempts
        
        # Log de fallo final
        log_eas_error("RETRY_FINAL_FAILURE", {
            "operation": self.config.operation_name,
            "total_attempts": self.metrics.total_attempts,
            "total_time": total_time,
            "final_error": str(last_error),
            "impact_ms": self.metrics.estimated_impact_ms
        })
        
        # Disparar circuit breaker si está integrado
        if self.circuit and self.metrics.consecutive_failures >= 3:
            self.metrics.circuit_breaker_triggers += 1
            
        raise last_error

    def execute_sync(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecutar función síncrona con backoff exponencial
        """
        async def async_wrapper():
            return func(*args, **kwargs)
        
        return asyncio.run(self.execute_async(async_wrapper))

    def get_metrics(self) -> Dict[str, Any]:
        """Obtener métricas completas del backoff"""
        return {
            "config": {
                "operation_name": self.config.operation_name,
                "strategy": self.config.strategy.value,
                "max_retries": self.config.max_retries,
                "base_delay": self.config.base_delay
            },
            "metrics": {
                "total_attempts": self.metrics.total_attempts,
                "successful_attempts": self.metrics.successful_attempts,
                "failed_attempts": self.metrics.failed_attempts,
                "success_rate": self.metrics.success_rate,
                "total_retry_delay": self.metrics.total_retry_delay,
                "average_retry_time": self.metrics.average_retry_time,
                "consecutive_failures": self.metrics.consecutive_failures,
                "circuit_breaker_triggers": self.metrics.circuit_breaker_triggers,
                "estimated_impact_ms": self.metrics.estimated_impact_ms
            }
        }

    def reset_metrics(self):
        """Resetear métricas para nuevo ciclo"""
        self.metrics = RetryMetrics(operation_name=self.config.operation_name)

    def get_error_rate(self) -> float:
        """Obtiene tasa de errores para HealthMonitor"""
        total = self.metrics.total_attempts
        return self.metrics.failed_attempts / max(total, 1) if total > 0 else 0.0

    def get_status(self) -> str:
        """Obtiene estado para HealthMonitor"""
        if self.circuit:
            return self.circuit.get_state() if hasattr(self.circuit, 'get_state') else self.circuit.state
        return "active"

# Configuraciones predefinidas para operaciones EAS
class EASBackoffConfigs:
    """Configuraciones predefinidas para operaciones EAS específicas"""
    
    @staticmethod
    def trade_execution() -> BackoffConfig:
        """Configuración para ejecución de órdenes (alta criticidad)"""
        return BackoffConfig(
            operation_name="trade_execution",
            max_retries=2,  # Mínimo para HFT
            base_delay=0.05,  # 50ms base
            max_delay=1.0,   # 1 segundo máximo
            strategy=BackoffStrategy.AGGRESSIVE,
            timeout=2.0,     # 2 segundos timeout total
            critical_errors=["invalid price", "market closed", "trade disabled"],
            retry_on_timeout=True
        )
    
    @staticmethod
    def market_data() -> BackoffConfig:
        """Configuración para obtención de datos de mercado"""
        return BackoffConfig(
            operation_name="market_data",
            max_retries=3,
            base_delay=0.1,
            max_delay=3.0,
            strategy=BackoffStrategy.EXPONENTIAL,
            timeout=5.0,
            critical_errors=["connection lost", "invalid symbol"]
        )
    
    @staticmethod
    def ia_validation() -> BackoffConfig:
        """Configuración para validaciones IA"""
        return BackoffConfig(
            operation_name="ia_validation", 
            max_retries=2,
            base_delay=0.2,
            max_delay=2.0,
            strategy=BackoffStrategy.LINEAR,
            timeout=3.0,
            critical_errors=["model unavailable", "invalid response"]
        )

# Decorador para uso simplificado
def with_exponential_backoff(config: BackoffConfig):
    """
    Decorador para aplicar backoff exponencial a funciones
    """
    def decorator(func):
        backoff = ExponentialBackoff(config)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await backoff.execute_async(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return backoff.execute_sync(func, *args, **kwargs)
        
        # Devolver el wrapper apropiado
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Funciones de conveniencia para uso rápido
async def execute_with_backoff(func: Callable, operation_name: str, *args, **kwargs) -> Any:
    """
    Ejecutar función con backoff usando configuración predefinida
    """
    config_map = {
        "trade_execution": EASBackoffConfigs.trade_execution(),
        "market_data": EASBackoffConfigs.market_data(), 
        "ia_validation": EASBackoffConfigs.ia_validation()
    }
    
    config = config_map.get(operation_name, BackoffConfig(operation_name=operation_name))
    backoff = ExponentialBackoff(config)
    
    if asyncio.iscoroutinefunction(func):
        return await backoff.execute_async(func, *args, **kwargs)
    else:
        return backoff.execute_sync(func, *args, **kwargs)

# Manager para gestión centralizada
class BackoffManager:
    """
    Gestor centralizado de instancias de backoff para el sistema EAS
    """
    
    def __init__(self):
        self._instances: Dict[str, ExponentialBackoff] = {}
        self._logger = get_eas_logger("BackoffManager")
        self._lock = threading.RLock()

    def get_backoff(self, config: BackoffConfig) -> ExponentialBackoff:
        """Obtener o crear instancia de backoff"""
        with self._lock:
            if config.operation_name not in self._instances:
                self._instances[config.operation_name] = ExponentialBackoff(config)
                self._logger.log_structured("INFO", "BACKOFF_INSTANCE_CREATED", {
                    "operation": config.operation_name,
                    "strategy": config.strategy.value,
                    "max_retries": config.max_retries
                })
        
        return self._instances[config.operation_name]
    
    def get_global_metrics(self) -> Dict[str, Any]:
        """Obtener métricas de todas las instancias"""
        with self._lock:
            metrics = {}
            for name, instance in self._instances.items():
                metrics[name] = instance.get_metrics()
            return metrics
    
    def reset_all_metrics(self):
        """Resetear métricas de todas las instancias"""
        with self._lock:
            for instance in self._instances.values():
                instance.reset_metrics()

# Instancia global del manager
global_backoff_manager = BackoffManager()

# Ejemplo de uso
async def example_usage():
    """
    Ejemplo de uso del sistema de backoff mejorado
    """
    
    # Uso con decorador
    @with_exponential_backoff(EASBackoffConfigs.trade_execution())
    async def execute_trade(symbol: str, volume: float):
        # Simular ejecución de trade
        await asyncio.sleep(0.1)
        return f"Trade executed: {symbol} {volume}"
    
    # Uso con manager
    manager = BackoffManager()
    backoff = manager.get_backoff(EASBackoffConfigs.market_data())
    
    async def fetch_market_data():
        await asyncio.sleep(0.05)
        return {"price": 1950.25, "spread": 0.15}
    
    try:
        # Ejecutar con backoff
        trade_result = await execute_trade("XAUUSD", 0.1)
        market_data = await backoff.execute_async(fetch_market_data)
        
        print(f"Trade: {trade_result}")
        print(f"Market: {market_data}")
        
        # Obtener métricas
        metrics = backoff.get_metrics()
        print(f"Métricas: {metrics}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Ejecutar ejemplo
    asyncio.run(example_usage())