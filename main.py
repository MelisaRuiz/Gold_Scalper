#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EAS Híbrido 2025 - Sistema de Trading Automatizado con IA
Arquitectura multi-agente con disciplina rígida para XAUUSD
Integración completa con Núcleo Inmutable EAS 2025
"""

import asyncio
import json
import logging
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import signal
import atexit

# Importar componentes EAS 2025
from infrastructure.structured_logger import get_eas_logger, log_eas_info, log_eas_error, log_eas_warning
from infrastructure.config_manager import ConfigManager
from infrastructure.health_monitor import HealthMonitor
from agents.agent_orchestrator import AgentOrchestrator
from core.risk_manager import RiskManager
from core.execution_engine import ExecutionEngine
from core.session_manager import SessionManager
from monitoring.metrics_dashboard import get_metrics_dashboard
from monitoring.alert_system import get_alert_system

# NÚCLEO INMUTABLE EAS 2025 - NUEVA INTEGRACIÓN
from core.immutable_core import IMMUTABLE_CORE
from config.immutable_config import IMMUTABLE_CONFIG

class EASHybrid2025:
    """
    Sistema principal EAS Híbrido 2025
    Combina disciplina rígida con validación IA para scalping de XAUUSD
    Integrado con Núcleo Inmutable EAS 2025
    """
    
    def __init__(self, config_dir: Path = Path("config"), mode: str = "paper"):
        self.config_dir = config_dir
        self.mode = mode
        self.is_running = False
        
        # Inicializar componentes core
        self.config_manager = ConfigManager(config_dir)
        self.logger = get_eas_logger("EAS_Main")
        self.health_monitor = HealthMonitor()
        self.metrics_dashboard = get_metrics_dashboard()
        self.alert_system = get_alert_system()
        
        # Componentes de trading
        self.agent_orchestrator = None
        self.risk_manager = None
        self.execution_engine = None
        self.session_manager = None
        
        # Estado del sistema
        self.start_time = None
        self.system_status = "STOPPED"
        
        # Registrar handlers de shutdown
        self._register_shutdown_handlers()
        
        log_eas_info("SYSTEM_INITIALIZED", {
            "version": "EAS_Hybrid_2025_v1.0",
            "mode": mode,
            "config_dir": str(config_dir),
            "immutable_core_integrated": True
        })
    
    def _register_shutdown_handlers(self):
        """Registra handlers para shutdown graceful"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        atexit.register(self._atexit_handler)
    
    def _signal_handler(self, signum, frame):
        """Handler para señales de sistema"""
        log_eas_info("SYSTEM_SIGNAL_RECEIVED", {
            "signal": signum,
            "signal_name": signal.Signals(signum).name
        })
        asyncio.create_task(self.stop())
    
    def _atexit_handler(self):
        """Handler para exit del programa"""
        if self.is_running:
            log_eas_warning("SYSTEM_ATEXIT_CALLED", {"status": "FORCED_SHUTDOWN"})
            # Intentar shutdown graceful
            try:
                asyncio.run(self.stop())
            except:
                pass
    
    async def initialize(self):
        """Inicializa todos los componentes del sistema con verificación de núcleo inmutable"""
        try:
            log_eas_info("SYSTEM_INITIALIZATION_STARTED", {})
            
            # Cargar configuraciones
            await self.config_manager.load_all_configs()
            
            # VERIFICACIÓN NÚCLEO INMUTABLE - NUEVA INTEGRACIÓN
            if not await self._initialize_immutable_core():
                log_eas_error("SYSTEM_IMMUTABLE_CORE_FAILED", {
                    "error": "Núcleo inmutable no pudo inicializarse correctamente"
                })
                return False
            
            # Inicializar componentes en orden
            await self._initialize_core_components()
            await self._initialize_trading_components()
            await self._initialize_monitoring_systems()
            
            # Verificar salud del sistema
            health_status = await self.health_monitor.check_system_health()
            if health_status['overall_status'] != 'HEALTHY':
                log_eas_error("SYSTEM_HEALTH_CHECK_FAILED", health_status)
                raise Exception("System health check failed")
            
            self.system_status = "INITIALIZED"
            log_eas_info("SYSTEM_INITIALIZATION_COMPLETED", {
                "status": self.system_status,
                "health": health_status['overall_status'],
                "immutable_core_status": IMMUTABLE_CORE.get_immutable_status()['trading_enabled']
            })
            
            return True
            
        except Exception as e:
            log_eas_error("SYSTEM_INITIALIZATION_FAILED", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            await self.stop()
            return False
    
    async def _initialize_immutable_core(self) -> bool:
        """
        Inicializa y verifica el núcleo inmutable EAS 2025
        """
        try:
            log_eas_info("IMMUTABLE_CORE_INITIALIZATION_STARTED", {})
            
            # 1. Verificar estado del núcleo inmutable
            immutable_status = IMMUTABLE_CORE.get_immutable_status()
            if not immutable_status['trading_enabled']:
                log_eas_error("IMMUTABLE_CORE_TRADING_DISABLED", {
                    "reason": "Núcleo inmutable tiene trading deshabilitado al inicio",
                    "consecutive_losses": immutable_status['consecutive_losses'],
                    "kill_switch_triggered": immutable_status['kill_switch_triggered']
                })
                return False
            
            # 2. Verificar compatibilidad de configuración
            core_rules = self.config_manager.get_config().get('core_rules', {})
            if not IMMUTABLE_CONFIG.validate_config_against_core(core_rules):
                log_eas_error("IMMUTABLE_CONFIG_INCOMPATIBLE", {
                    "config_rules": core_rules,
                    "immutable_rules": IMMUTABLE_CONFIG.get_immutable_config()
                })
                return False
            
            # 3. Verificar que estamos en sesión válida
            current_time = datetime.now()
            session_active = IMMUTABLE_CORE._is_trading_session_active()
            if not session_active:
                log_eas_warning("IMMUTABLE_CORE_OUTSIDE_SESSION", {
                    "current_time": current_time.isoformat(),
                    "session_hours": "09:30-11:30 ET"
                })
                # No es fatal, pero se registra
            
            # 4. Registrar métricas del núcleo inmutable
            self.metrics_dashboard.register_metric({
                "name": "immutable.core_consecutive_losses",
                "type": "gauge",
                "description": "Pérdidas consecutivas del núcleo inmutable"
            })
            
            self.metrics_dashboard.register_metric({
                "name": "immutable.core_trading_enabled",
                "type": "gauge", 
                "description": "Estado de trading del núcleo inmutable"
            })
            
            log_eas_info("IMMUTABLE_CORE_INITIALIZATION_COMPLETED", {
                "status": "SUCCESS",
                "trading_enabled": immutable_status['trading_enabled'],
                "consecutive_losses": immutable_status['consecutive_losses'],
                "rules": immutable_status['immutable_rules']
            })
            
            return True
            
        except Exception as e:
            log_eas_error("IMMUTABLE_CORE_INITIALIZATION_FAILED", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            return False
    
    async def _initialize_core_components(self):
        """Inicializa componentes core del sistema"""
        # Health Monitor
        await self.health_monitor.start()
        
        # Metrics Dashboard
        self.metrics_dashboard.register_metric({
            "name": "system.uptime_seconds",
            "type": "gauge",
            "description": "Tiempo de actividad del sistema"
        })
        
        log_eas_info("CORE_COMPONENTS_INITIALIZED", {})
    
    async def _initialize_trading_components(self):
        """Inicializa componentes de trading con integración de núcleo inmutable"""
        try:
            # Session Manager
            self.session_manager = SessionManager()
            await self.session_manager.initialize()
            
            # Risk Manager - Pasar configuración inmutable
            risk_config = self.config_manager.get_config().get('risk_config', {})
            self.risk_manager = RiskManager(risk_config)
            await self.risk_manager.initialize()
            
            # Agent Orchestrator - Integrado con núcleo inmutable vía signal_generator
            self.agent_orchestrator = AgentOrchestrator()
            await self.agent_orchestrator.initialize()
            
            # Execution Engine (solo en modo live/paper) - Integrado con núcleo inmutable
            if self.mode in ["live", "paper"]:
                execution_config = self.config_manager.get_config().get('execution_engine', {})
                self.execution_engine = ExecutionEngine(execution_config)
                await self.execution_engine.initialize()
            
            log_eas_info("TRADING_COMPONENTS_INITIALIZED", {
                "mode": self.mode,
                "immutable_core_integrated": True
            })
            
        except Exception as e:
            log_eas_error("TRADING_COMPONENTS_INITIALIZATION_FAILED", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise
    
    async def _initialize_monitoring_systems(self):
        """Inicializa sistemas de monitoreo"""
        # Configurar alertas
        await self.alert_system.initialize()
        
        # Registrar callbacks para métricas
        self.metrics_dashboard.register_alert_callback(
            self._handle_metric_alert
        )
        
        # Registrar callback específico para núcleo inmutable
        self.metrics_dashboard.register_alert_callback(
            self._handle_immutable_alert
        )
        
        log_eas_info("MONITORING_SYSTEMS_INITIALIZED", {})
    
    async def _handle_metric_alert(self, alert: str, metric_data: Dict[str, Any]):
        """Maneja alertas del sistema de métricas"""
        log_eas_warning("METRIC_ALERT_TRIGGERED", {
            "alert": alert,
            "metric_data": metric_data
        })
        
        # Enviar alerta a través del sistema de alertas
        await self.alert_system.send_alert({
            "type": "METRIC_ALERT",
            "message": alert,
            "severity": "MEDIUM",
            "timestamp": datetime.utcnow().isoformat(),
            "data": metric_data
        })
    
    async def _handle_immutable_alert(self, alert: str, metric_data: Dict[str, Any]):
        """Maneja alertas específicas del núcleo inmutable"""
        if "immutable" in alert.lower():
            log_eas_warning("IMMUTABLE_CORE_ALERT_TRIGGERED", {
                "alert": alert,
                "metric_data": metric_data
            })
            
            # Enviar alerta de alta prioridad para núcleo inmutable
            await self.alert_system.send_alert({
                "type": "IMMUTABLE_CORE_ALERT",
                "message": f"Núcleo Inmutable: {alert}",
                "severity": "HIGH",
                "timestamp": datetime.utcnow().isoformat(),
                "data": metric_data
            })
    
    async def start(self):
        """Inicia el sistema de trading con verificación de núcleo inmutable"""
        if self.is_running:
            log_eas_warning("SYSTEM_ALREADY_RUNNING", {})
            return
        
        try:
            log_eas_info("SYSTEM_STARTING", {"mode": self.mode})
            
            # VERIFICACIÓN FINAL DE NÚCLEO INMUTABLE ANTES DE INICIAR
            immutable_status = IMMUTABLE_CORE.get_immutable_status()
            if not immutable_status['trading_enabled']:
                log_eas_error("SYSTEM_START_BLOCKED_BY_IMMUTABLE_CORE", {
                    "reason": "Núcleo inmutable tiene trading deshabilitado",
                    "consecutive_losses": immutable_status['consecutive_losses'],
                    "kill_switch_triggered": immutable_status['kill_switch_triggered']
                })
                raise Exception("System start blocked by immutable core - trading disabled")
            
            # Inicializar si no está inicializado
            if self.system_status != "INITIALIZED":
                success = await self.initialize()
                if not success:
                    raise Exception("Initialization failed")
            
            # Iniciar loop principal
            self.is_running = True
            self.start_time = datetime.utcnow()
            self.system_status = "RUNNING"
            
            # Iniciar componentes
            await self.session_manager.start()
            await self.agent_orchestrator.start()
            
            if self.execution_engine:
                await self.execution_engine.start()
            
            log_eas_info("SYSTEM_STARTED", {
                "start_time": self.start_time.isoformat(),
                "mode": self.mode,
                "immutable_core_status": immutable_status
            })
            
            # Loop principal del sistema
            await self._main_loop()
            
        except Exception as e:
            log_eas_error("SYSTEM_START_FAILED", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            await self.stop()
            raise
    
    async def _main_loop(self):
        """Loop principal del sistema con monitoreo de núcleo inmutable"""
        iteration = 0
        
        while self.is_running:
            try:
                iteration += 1
                
                # Actualizar métricas del sistema
                await self._update_system_metrics()
                
                # Verificar salud del sistema
                await self._check_system_health()
                
                # Verificar estado del núcleo inmutable (cada 10 iteraciones)
                if iteration % 10 == 0:
                    await self._check_immutable_core_status()
                
                # Procesar ciclo de trading si la sesión está activa
                if await self._should_process_trading_cycle():
                    await self._process_trading_cycle()
                
                # Log cada 100 iteraciones
                if iteration % 100 == 0:
                    log_eas_info("SYSTEM_MAIN_LOOP_ITERATION", {
                        "iteration": iteration,
                        "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
                        "immutable_core_status": IMMUTABLE_CORE.get_immutable_status()
                    })
                
                # Esperar antes del siguiente ciclo
                await asyncio.sleep(1)  # 1 segundo entre ciclos
                
            except asyncio.CancelledError:
                log_eas_info("MAIN_LOOP_CANCELLED", {"iteration": iteration})
                break
            except Exception as e:
                log_eas_error("MAIN_LOOP_ERROR", {
                    "iteration": iteration,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                await asyncio.sleep(5)  # Esperar 5 segundos antes de reintentar
    
    async def _update_system_metrics(self):
        """Actualiza métricas del sistema incluyendo núcleo inmutable"""
        try:
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
            
            self.metrics_dashboard.record_metric("system.uptime_seconds", uptime)
            
            # Obtener métricas de componentes
            component_metrics = {
                "session_manager": await self.session_manager.get_metrics(),
                "risk_manager": await self.risk_manager.get_metrics(),
                "agent_orchestrator": await self.agent_orchestrator.get_metrics(),
            }
            
            if self.execution_engine:
                component_metrics["execution_engine"] = await self.execution_engine.get_metrics()
            
            # Obtener métricas del núcleo inmutable
            immutable_status = IMMUTABLE_CORE.get_immutable_status()
            component_metrics["immutable_core"] = {
                "consecutive_losses": immutable_status['consecutive_losses'],
                "trading_enabled": immutable_status['trading_enabled'],
                "kill_switch_triggered": immutable_status['kill_switch_triggered'],
                "current_session_active": immutable_status['current_session_active']
            }
            
            # Registrar métricas del núcleo inmutable
            self.metrics_dashboard.record_metric(
                "immutable.core_consecutive_losses", 
                immutable_status['consecutive_losses']
            )
            self.metrics_dashboard.record_metric(
                "immutable.core_trading_enabled", 
                1 if immutable_status['trading_enabled'] else 0
            )
            
            # Registrar métricas consolidadas
            self.metrics_dashboard.record_eas_metrics(component_metrics)
            
        except Exception as e:
            log_eas_error("METRICS_UPDATE_ERROR", {"error": str(e)})
    
    async def _check_immutable_core_status(self):
        """Verifica el estado del núcleo inmutable y toma acciones si es necesario"""
        try:
            immutable_status = IMMUTABLE_CORE.get_immutable_status()
            
            # Si el kill switch está activado, detener el sistema
            if immutable_status['kill_switch_triggered'] and self.is_running:
                log_eas_critical("IMMUTABLE_CORE_KILL_SWITCH_ACTIVATED", {
                    "consecutive_losses": immutable_status['consecutive_losses'],
                    "reason": "Kill switch activado por núcleo inmutable - deteniendo sistema"
                })
                
                await self.alert_system.send_alert({
                    "type": "IMMUTABLE_CORE_KILL_SWITCH",
                    "message": "KILL SWITCH ACTIVADO - Sistema detenido por núcleo inmutable",
                    "severity": "CRITICAL",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": immutable_status
                })
                
                # Detener sistema graceful
                await self.stop()
                
        except Exception as e:
            log_eas_error("IMMUTABLE_CORE_STATUS_CHECK_ERROR", {"error": str(e)})
    
    async def _check_system_health(self):
        """Verifica la salud del sistema incluyendo núcleo inmutable"""
        try:
            health_status = await self.health_monitor.check_system_health()
            
            # Incluir estado del núcleo inmutable en health check
            immutable_status = IMMUTABLE_CORE.get_immutable_status()
            health_status['immutable_core'] = {
                'trading_enabled': immutable_status['trading_enabled'],
                'kill_switch_triggered': immutable_status['kill_switch_triggered'],
                'consecutive_losses': immutable_status['consecutive_losses']
            }
            
            # Si el núcleo inmutable tiene kill switch activado, sistema en estado CRITICAL
            if immutable_status['kill_switch_triggered']:
                health_status['overall_status'] = 'CRITICAL'
                health_status['components']['immutable_core'] = 'CRITICAL'
            
            if health_status['overall_status'] == 'CRITICAL':
                log_eas_error("SYSTEM_HEALTH_CRITICAL", health_status)
                await self.alert_system.send_alert({
                    "type": "SYSTEM_HEALTH_CRITICAL",
                    "message": "System health is CRITICAL - Immediate attention required",
                    "severity": "CRITICAL",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": health_status
                })
                
            elif health_status['overall_status'] == 'DEGRADED':
                log_eas_warning("SYSTEM_HEALTH_DEGRADED", health_status)
                
        except Exception as e:
            log_eas_error("HEALTH_CHECK_ERROR", {"error": str(e)})
    
    async def _should_process_trading_cycle(self) -> bool:
        """Determina si debe procesarse un ciclo de trading incluyendo verificación de núcleo inmutable"""
        try:
            # 1. Verificar núcleo inmutable primero (más importante)
            immutable_status = IMMUTABLE_CORE.get_immutable_status()
            if not immutable_status['trading_enabled']:
                log_eas_warning("TRADING_CYCLE_BLOCKED_BY_IMMUTABLE_CORE", {
                    "reason": "Núcleo inmutable tiene trading deshabilitado",
                    "consecutive_losses": immutable_status['consecutive_losses']
                })
                return False
            
            # 2. Verificar si la sesión está activa
            if not await self.session_manager.is_trading_session_active():
                return False
            
            # 3. Verificar circuit breakers
            if await self.risk_manager.is_circuit_breaker_active():
                return False
            
            # 4. Verificar kill switches del risk manager
            if await self.risk_manager.is_kill_switch_active():
                return False
            
            return True
            
        except Exception as e:
            log_eas_error("TRADING_CYCLE_CHECK_ERROR", {"error": str(e)})
            return False
    
    async def _process_trading_cycle(self):
        """Procesa un ciclo completo de trading con integración de núcleo inmutable"""
        try:
            # VERIFICACIÓN FINAL DE NÚCLEO INMUTABLE ANTES DE PROCESAR SEÑAL
            immutable_status = IMMUTABLE_CORE.get_immutable_status()
            if not immutable_status['trading_enabled']:
                log_eas_warning("TRADING_CYCLE_ABORTED_IMMUTABLE_DISABLED", {
                    "reason": "Núcleo inmutable deshabilitó trading durante el ciclo"
                })
                return

            # 1. Obtener señal del orchestrator de agentes (ya integrado con núcleo inmutable vía signal_generator)
            signal = await self.agent_orchestrator.generate_signal()
            if not signal or not signal.get('valid', False):
                return
            
            # 2. Validar con risk manager
            risk_approval = await self.risk_manager.validate_signal(signal)
            if not risk_approval.get('approved', False):
                log_eas_info("SIGNAL_REJECTED_BY_RISK_MANAGER", {
                    "signal_id": signal.get('id'),
                    "reason": risk_approval.get('reason', 'Unknown')
                })
                return
            
            # 3. Ejecutar (solo en modos live/paper)
            if self.execution_engine and self.mode in ["live", "paper"]:
                execution_result = await self.execution_engine.execute_signal(
                    signal, risk_approval
                )
                
                if execution_result.get('success', False):
                    log_eas_info("TRADE_EXECUTED_SUCCESSFULLY", {
                        "signal_id": signal.get('id'),
                        "order_id": execution_result.get('order_id'),
                        "direction": signal.get('direction'),
                        "immutable_core_validation": signal.get('immutable_validation', {})
                    })
                    
                    # ACTUALIZAR NÚCLEO INMUTABLE CON RESULTADO (éxito)
                    IMMUTABLE_CORE.record_trade_result(True, execution_result.get('pnl', 0))
                    
                else:
                    log_eas_error("TRADE_EXECUTION_FAILED", {
                        "signal_id": signal.get('id'),
                        "error": execution_result.get('error', 'Unknown')
                    })
                    
                    # ACTUALIZAR NÚCLEO INMUTABLE CON RESULTADO (fallo)
                    IMMUTABLE_CORE.record_trade_result(False, execution_result.get('pnl', 0))
            
            # 4. Actualizar métricas
            self.metrics_dashboard.record_metric(
                "trading.signals_processed", 
                1, 
                {"type": "valid_signal"}
            )
            
        except Exception as e:
            log_eas_error("TRADING_CYCLE_ERROR", {
                "error": str(e),
                "error_type": type(e).__name__
            })
    
    async def stop(self):
        """Detiene el sistema de forma graceful incluyendo núcleo inmutable"""
        if not self.is_running:
            return
        
        log_eas_info("SYSTEM_STOPPING", {})
        self.is_running = False
        self.system_status = "STOPPING"
        
        try:
            # Detener componentes en orden inverso
            if self.execution_engine:
                await self.execution_engine.stop()
            
            if self.agent_orchestrator:
                await self.agent_orchestrator.stop()
            
            if self.session_manager:
                await self.session_manager.stop()
            
            # Detener monitoreo
            await self.health_monitor.stop()
            
            # Generar reporte final
            await self._generate_shutdown_report()
            
            self.system_status = "STOPPED"
            log_eas_info("SYSTEM_STOPPED", {
                "total_uptime": (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0,
                "final_immutable_status": IMMUTABLE_CORE.get_immutable_status()
            })
            
        except Exception as e:
            log_eas_error("SYSTEM_STOP_ERROR", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            self.system_status = "ERROR"
    
    async def _generate_shutdown_report(self):
        """Genera reporte de shutdown incluyendo estado del núcleo inmutable"""
        try:
            final_metrics = self.metrics_dashboard.get_eas_metrics()
            health_status = await self.health_monitor.check_system_health()
            immutable_status = IMMUTABLE_CORE.get_immutable_status()
            
            shutdown_report = {
                "shutdown_time": datetime.utcnow().isoformat(),
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "total_uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0,
                "final_metrics": final_metrics,
                "health_status": health_status,
                "immutable_core_status": immutable_status,
                "system_status": self.system_status,
                "mode": self.mode
            }
            
            log_eas_info("SHUTDOWN_REPORT_GENERATED", shutdown_report)
            
            # Guardar reporte a archivo
            report_file = Path("reports") / f"shutdown_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            report_file.parent.mkdir(exist_ok=True)
            
            with open(report_file, 'w') as f:
                json.dump(shutdown_report, f, indent=2, default=str)
                
        except Exception as e:
            log_eas_error("SHUTDOWN_REPORT_ERROR", {"error": str(e)})
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual del sistema incluyendo núcleo inmutable"""
        immutable_status = IMMUTABLE_CORE.get_immutable_status()
        
        return {
            "system_status": self.system_status,
            "is_running": self.is_running,
            "mode": self.mode,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0,
            "config_dir": str(self.config_dir),
            "immutable_core": {
                "trading_enabled": immutable_status['trading_enabled'],
                "consecutive_losses": immutable_status['consecutive_losses'],
                "kill_switch_triggered": immutable_status['kill_switch_triggered'],
                "current_session_active": immutable_status['current_session_active']
            }
        }
    
    def emergency_stop_immutable_core(self, reason: str = "Emergency stop"):
        """
        Parada de emergencia del núcleo inmutable
        Útil para intervención manual en casos críticos
        """
        IMMUTABLE_CORE.emergency_stop(reason)
        log_eas_critical("IMMUTABLE_CORE_EMERGENCY_STOP", {"reason": reason})
    
    def reset_immutable_kill_switch(self, reason: str = "Manual reset"):
        """
        Resetea el kill switch del núcleo inmutable
        Solo para uso en condiciones controladas
        """
        success = IMMUTABLE_CORE.reset_kill_switch(reason)
        if success:
            log_eas_warning("IMMUTABLE_CORE_KILL_SWITCH_RESET", {"reason": reason})
        else:
            log_eas_warning("IMMUTABLE_CORE_KILL_SWITCH_RESET_FAILED", {"reason": reason})
        
        return success


async def main():
    """Función principal del sistema EAS Híbrido 2025 con núcleo inmutable"""
    parser = argparse.ArgumentParser(description='EAS Híbrido 2025 - Sistema de Trading con IA y Núcleo Inmutable')
    parser.add_argument('--mode', choices=['backtest', 'paper', 'live'], 
                       default='paper', help='Modo de operación')
    parser.add_argument('--config-dir', type=str, default='config',
                       help='Directorio de configuración')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Nivel de logging')
    parser.add_argument('--reset-kill-switch', action='store_true',
                       help='Resetear kill switch del núcleo inmutable al inicio')
    
    args = parser.parse_args()
    
    # Configurar logging básico (el structured logger se configura después)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear sistema
    system = EASHybrid2025(
        config_dir=Path(args.config_dir),
        mode=args.mode
    )
    
    # Resetear kill switch si se solicita
    if args.reset_kill_switch:
        print("🔄 Reseteando kill switch del núcleo inmutable...")
        success = system.reset_immutable_kill_switch("Command line reset")
        if success:
            print("✅ Kill switch reseteado exitosamente")
        else:
            print("❌ No se pudo resetear kill switch")
    
    try:
        await system.start()
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested by user...")
    except Exception as e:
        print(f"❌ System failed with error: {e}")
        sys.exit(1)
    finally:
        await system.stop()


if __name__ == "__main__":
    # Verificar versión de Python
    if sys.version_info < (3, 9):
        print("❌ Python 3.9 or higher is required")
        sys.exit(1)
    
    # Ejecutar sistema
    asyncio.run(main())