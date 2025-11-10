[file name]: infrastructure/infrastructure_manager.py
[file content begin]
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gestor de Infraestructura EAS Híbrido 2025
Coordina la inicialización de circuit breakers, backoff, guardrails y health monitor
"""

import logging
from typing import Dict, Any, Optional
from infrastructure.circuit_breaker import CircuitBreakerManager
from infrastructure.exponential_backoff import BackoffManager, EASBackoffConfigs
from infrastructure.guardrails import get_guardrail_orchestrator
from infrastructure.health_monitor import initialize_health_monitor, get_health_monitor

logger = logging.getLogger("HECTAGold.InfrastructureManager")

class InfrastructureManager:
    """
    Gestor principal de infraestructura EAS 2025
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.infrastructure_config = config.get('infrastructure', {})
        
        # Componentes de infraestructura
        self.circuit_manager: Optional[CircuitBreakerManager] = None
        self.backoff_manager: Optional[BackoffManager] = None
        self.guardrail_orchestrator = None
        self.health_monitor = None
        
        # Estado
        self.initialized = False
        self.components_status = {}
        
    async def initialize(self):
        """Inicializa toda la infraestructura"""
        try:
            logger.info("🚀 Inicializando infraestructura EAS 2025...")
            
            # 1. Circuit Breaker Manager
            if self.infrastructure_config.get('circuit_breaker', {}).get('enabled', True):
                self.circuit_manager = CircuitBreakerManager()
                logger.info("✅ Circuit Breaker Manager inicializado")
            
            # 2. Exponential Backoff Manager
            if self.infrastructure_config.get('exponential_backoff', {}).get('enabled', True):
                self.backoff_manager = BackoffManager()
                logger.info("✅ Exponential Backoff Manager inicializado")
            
            # 3. Guardrails
            if self.infrastructure_config.get('guardrails', {}).get('enabled', True):
                self.guardrail_orchestrator = get_guardrail_orchestrator()
                logger.info("✅ Guardrails inicializados")
            
            # 4. Health Monitor
            if self.infrastructure_config.get('health_monitor', {}).get('enabled', True):
                self.health_monitor = initialize_health_monitor(self.config)
                logger.info("✅ Health Monitor inicializado")
            
            self.initialized = True
            logger.info("🎯 Infraestructura EAS 2025 completamente inicializada")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando infraestructura: {e}")
            raise
    
    def get_circuit_breaker(self, circuit_type: str, name: str = None):
        """Obtiene circuit breaker específico"""
        if not self.circuit_manager:
            return None
            
        if name is None:
            name = circuit_type
            
        return self.circuit_manager.create_circuit(name, circuit_type=circuit_type)
    
    def get_backoff_config(self, operation_type: str):
        """Obtiene configuración de backoff predefinida"""
        config_map = {
            "trade_execution": EASBackoffConfigs.trade_execution(),
            "market_data": EASBackoffConfigs.market_data(),
            "ia_validation": EASBackoffConfigs.ia_validation()
        }
        return config_map.get(operation_type)
    
    def get_health_status(self):
        """Obtiene estado de salud de la infraestructura"""
        if not self.initialized:
            return {"status": "NOT_INITIALIZED"}
            
        status = {
            "status": "OPERATIONAL",
            "components": {
                "circuit_breaker": bool(self.circuit_manager),
                "exponential_backoff": bool(self.backoff_manager),
                "guardrails": bool(self.guardrail_orchestrator),
                "health_monitor": bool(self.health_monitor)
            }
        }
        
        # Añadir métricas específicas si están disponibles
        if self.health_monitor:
            health_report = self.health_monitor.get_system_health_report()
            status["health_report"] = health_report
            
        return status
    
    async def shutdown(self):
        """Cierre seguro de la infraestructura"""
        logger.info("🔌 Cerrando infraestructura EAS...")
        
        if self.health_monitor:
            self.health_monitor.stop_monitoring()
            
        self.initialized = False
        logger.info("✅ Infraestructura EAS cerrada correctamente")

# Instancia global
_infrastructure_manager: Optional[InfrastructureManager] = None

async def initialize_global_infrastructure(config: Dict[str, Any]) -> InfrastructureManager:
    """Inicializa la infraestructura global del sistema"""
    global _infrastructure_manager
    _infrastructure_manager = InfrastructureManager(config)
    await _infrastructure_manager.initialize()
    return _infrastructure_manager

def get_infrastructure_manager() -> InfrastructureManager:
    """Obtiene el gestor de infraestructura global"""
    global _infrastructure_manager
    if _infrastructure_manager is None:
        raise RuntimeError("InfrastructureManager no ha sido inicializado")
    return _infrastructure_manager
[file content end]