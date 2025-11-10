[file name]: core/immutable_config.py
[file content begin]
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gestor de Configuración Inmutable EAS Híbrido 2025
Carga y valida configuraciones que NO pueden modificarse durante ejecución
CON VALIDACIÓN DE INFRAESTRUCTURA INTEGRADA
"""

import json
import threading
from pathlib import Path
from typing import Final, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger("HECTAGold.ImmutableConfig")

@dataclass(frozen=True)
class ImmutableTradingConfig:
    """Configuración de trading inmutable EAS 2025"""
    risk_per_trade: float = 0.3
    max_consecutive_losses: int = 2
    trading_session: str = "NY_OPEN"
    min_confidence: float = 0.75
    risk_reward_ratio: float = 2.0
    allowed_instruments: tuple = ("XAUUSD",)
    timeframes: tuple = ("M15", "H1", "D1")

class ImmutableConfigManager:
    """
    Gestor de configuración inmutable EAS Híbrido 2025
    Una vez cargada, la configuración NO puede modificarse
    """
    
    def __init__(self, config_path: Path = Path("config/trading_config.json")):
        self.config_path = config_path
        self._config: Optional[ImmutableTradingConfig] = None
        self._lock = threading.RLock()
        self._loaded = False
        
        # Cargar configuración al inicializar
        self._load_immutable_config()

    def _load_immutable_config(self):
        """Carga y valida la configuración inmutable"""
        with self._lock:
            if self._loaded:
                return
                
            try:
                if not self.config_path.exists():
                    logger.warning(f"⚠️ Archivo de configuración no encontrado: {self.config_path}")
                    self._config = ImmutableTradingConfig()
                    logger.info("✅ Usando configuración inmutable por defecto EAS 2025")
                    return

                with open(self.config_path, 'r') as f:
                    raw_config = json.load(f)

                # Extraer y validar reglas inmutables
                immutable_rules = raw_config.get('immutable_rules', {})
                core_rules = raw_config.get('core_rules', {})
                
                # NUEVO: Validar configuración de infraestructura
                infrastructure_config = raw_config.get('infrastructure', {})
                if not self.validate_infrastructure_config(infrastructure_config):
                    logger.error("🚨 Configuración de infraestructura inválida")
                    # Fallback a valores por defecto
                    self._config = ImmutableTradingConfig()
                    self._loaded = True
                    return

                # Validar valores críticos
                risk_per_trade = immutable_rules.get('risk_per_trade', 0.3)
                if risk_per_trade != 0.3:
                    logger.warning(f"🚨 Riesgo por trade configurado como {risk_per_trade}, forzando 0.3%")
                    risk_per_trade = 0.3

                max_losses = immutable_rules.get('max_consecutive_losses', 2)
                if max_losses != 2:
                    logger.warning(f"🚨 Máximo pérdidas configurado como {max_losses}, forzando 2")
                    max_losses = 2

                # Crear configuración inmutable
                self._config = ImmutableTradingConfig(
                    risk_per_trade=risk_per_trade,
                    max_consecutive_losses=max_losses,
                    trading_session=immutable_rules.get('trading_session', 'NY_OPEN'),
                    min_confidence=immutable_rules.get('min_confidence', 0.75),
                    risk_reward_ratio=immutable_rules.get('risk_reward_ratio', 2.0),
                    allowed_instruments=tuple(immutable_rules.get('allowed_instruments', ['XAUUSD'])),
                    timeframes=tuple(immutable_rules.get('timeframes', ['M15', 'H1', 'D1']))
                )

                self._loaded = True
                logger.info("✅ Configuración inmutable EAS 2025 cargada y validada")

            except Exception as e:
                logger.error(f"❌ Error cargando configuración inmutable: {e}")
                # Fallback a valores por defecto EAS
                self._config = ImmutableTradingConfig()
                self._loaded = True

    def validate_infrastructure_config(self, infrastructure_config: Dict[str, Any]) -> bool:
        """
        Valida configuración de infraestructura contra reglas inmutables
        
        Args:
            infrastructure_config: Configuración de infraestructura a validar
            
        Returns:
            bool: True si la configuración es válida
        """
        if not infrastructure_config:
            logger.warning("⚠️ No se encontró configuración de infraestructura")
            return True  # No es obligatoria, pero recomendada

        # Validar circuit breaker (umbrales de seguridad)
        cb_config = infrastructure_config.get('circuit_breaker', {})
        if cb_config.get('enabled', False):
            mt5_circuit = cb_config.get('circuit_types', {}).get('mt5_connection', {})
            failure_threshold = mt5_circuit.get('failure_threshold', 0)
            if failure_threshold > 3:
                logger.error("🚨 Circuit breaker MT5 muy permisivo (threshold > 3)")
                return False

        # Validar guardrails (seguridad crítica)
        guardrails_config = infrastructure_config.get('guardrails', {})
        if guardrails_config.get('enabled', False):
            validation_schema = guardrails_config.get('validation_schema', {})
            risk_multiplier_max = validation_schema.get('risk_multiplier_max', 1.5)
            if risk_multiplier_max > 1.5:
                logger.error("🚨 Risk multiplier máximo excede límite inmutable (1.5)")
                return False

        # Validar health monitor (umbrales de riesgo)
        health_config = infrastructure_config.get('health_monitor', {})
        if health_config.get('enabled', False):
            risk_thresholds = health_config.get('risk_thresholds', {})
            drawdown_alert = risk_thresholds.get('drawdown_alert', 0.6)
            if drawdown_alert > 0.8:  # Máximo 80% del drawdown permitido
                logger.error("🚨 Umbral de alerta de drawdown muy alto (>80%)")
                return False

        logger.info("✅ Configuración de infraestructura validada correctamente")
        return True

    def get_immutable_config(self) -> ImmutableTradingConfig:
        """Obtiene la configuración inmutable"""
        if not self._loaded:
            self._load_immutable_config()
        
        if self._config is None:
            raise RuntimeError("Configuración inmutable no disponible")
            
        return self._config

    def validate_config_against_core(self, core_rules: Dict[str, Any]) -> bool:
        """
        Valida que la configuración sea compatible con el núcleo inmutable
        
        Args:
            core_rules: Reglas del núcleo a validar
            
        Returns:
            bool: True si es compatible
        """
        if not self._config:
            return False

        # Validar reglas críticas
        checks = [
            (core_rules.get('risk_per_trade', 0) == self._config.risk_per_trade, "Risk per trade"),
            (core_rules.get('max_consecutive_losses', 0) == self._config.max_consecutive_losses, "Max consecutive losses"),
            (core_rules.get('risk_reward_ratio', 0) == self._config.risk_reward_ratio, "Risk/reward ratio")
        ]

        for check_passed, rule_name in checks:
            if not check_passed:
                logger.error(f"🚨 Incompatibilidad en regla: {rule_name}")
                return False

        return True

    def get_config_summary(self) -> Dict[str, Any]:
        """Resumen de la configuración inmutable para logging/monitoreo"""
        if not self._config:
            return {}
            
        return {
            "risk_per_trade": self._config.risk_per_trade,
            "max_consecutive_losses": self._config.max_consecutive_losses,
            "trading_session": self._config.trading_session,
            "min_confidence": self._config.min_confidence,
            "risk_reward_ratio": self._config.risk_reward_ratio,
            "allowed_instruments": list(self._config.allowed_instruments),
            "timeframes": list(self._config.timeframes),
            "config_source": str(self.config_path),
            "loaded_successfully": self._loaded
        }

# Instancia global del gestor de configuración
IMMUTABLE_CONFIG = ImmutableConfigManager()
[file content end]