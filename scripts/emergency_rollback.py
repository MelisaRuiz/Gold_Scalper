#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Emergency Rollback Script - EAS Híbrido 2025
Sistema de rollback de emergencia para recuperación ante fallos críticos
"""

import asyncio
import json
import logging
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import shutil
import subprocess

# Importar componentes EAS
from infrastructure.structured_logger import get_eas_logger, log_eas_error, log_eas_info, log_eas_warning
from infrastructure.config_manager import ConfigManager

logger = get_eas_logger("EmergencyRollback")

class EmergencyRollbackSystem:
    """
    Sistema de rollback de emergencia para EAS Híbrido 2025
    """
    
    def __init__(self, config_dir: Path = Path("config")):
        self.config_dir = config_dir
        self.backup_dir = Path("backups")
        self.rollback_log_file = Path("logs/rollback_history.json")
        
        # Crear directorios necesarios
        self.backup_dir.mkdir(exist_ok=True)
        self.rollback_log_file.parent.mkdir(exist_ok=True)
        
        self.config_manager = ConfigManager(config_dir)
        
        logger.info("🚨 Emergency Rollback System initialized")

    async def create_backup(self, backup_name: str = None) -> str:
        """
        Crear backup de la configuración actual
        """
        if not backup_name:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        try:
            # Backup de configuraciones
            config_files = [
                "trading_config.json",
                "agents_config.json", 
                "risk_config.json"
            ]
            
            for config_file in config_files:
                source = self.config_dir / config_file
                if source.exists():
                    destination = backup_path / config_file
                    shutil.copy2(source, destination)
                    logger.info(f"✅ Backed up {config_file}")
            
            # Backup de estado del sistema
            system_state = {
                "backup_timestamp": datetime.now().isoformat(),
                "backup_name": backup_name,
                "config_files": config_files,
                "system_version": "EAS_Hybrid_2025_v1.0"
            }
            
            state_file = backup_path / "system_state.json"
            with open(state_file, 'w') as f:
                json.dump(system_state, f, indent=2)
            
            logger.info(f"✅ Backup created: {backup_name}")
            return backup_name
            
        except Exception as e:
            logger.error(f"❌ Backup creation failed: {e}")
            raise

    async def execute_rollback(self, reason: str, backup_name: str = None, 
                             force: bool = False) -> Dict[str, Any]:
        """
        Ejecutar rollback de emergencia
        """
        rollback_start = datetime.now()
        
        try:
            log_eas_warning("EMERGENCY_ROLLBACK_TRIGGERED", {
                "reason": reason,
                "backup_name": backup_name,
                "force_mode": force
            })
            
            # 1. Encontrar backup apropiado
            backup_to_restore = await self._find_backup_to_restore(backup_name)
            if not backup_to_restore:
                if force:
                    logger.warning("⚠️ No backup found, but force mode enabled - using defaults")
                    backup_to_restore = await self._restore_default_configs()
                else:
                    raise Exception("No suitable backup found and force mode disabled")
            
            # 2. Validar backup
            if not await self._validate_backup(backup_to_restore):
                if not force:
                    raise Exception("Backup validation failed")
                else:
                    logger.warning("⚠️ Backup validation failed, but force mode enabled")
            
            # 3. Detener sistema si está corriendo
            await self._stop_running_system()
            
            # 4. Restaurar configuración
            await self._restore_configuration(backup_to_restore)
            
            # 5. Validar configuración restaurada
            validation_result = await self._validate_restored_configuration()
            if not validation_result["valid"] and not force:
                raise Exception(f"Restored configuration validation failed: {validation_result['errors']}")
            
            # 6. Registrar rollback
            rollback_data = await self._log_rollback_event(
                reason, backup_to_restore, rollback_start, "SUCCESS"
            )
            
            logger.info("✅ Emergency rollback completed successfully")
            
            return {
                "success": True,
                "backup_used": backup_to_restore,
                "rollback_id": rollback_data["rollback_id"],
                "validation_result": validation_result,
                "duration_seconds": (datetime.now() - rollback_start).total_seconds()
            }
            
        except Exception as e:
            error_msg = f"Rollback failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            # Log failed rollback
            await self._log_rollback_event(
                reason, backup_name, rollback_start, "FAILED", str(e)
            )
            
            return {
                "success": False,
                "error": error_msg,
                "duration_seconds": (datetime.now() - rollback_start).total_seconds()
            }

    async def _find_backup_to_restore(self, backup_name: str = None) -> Optional[str]:
        """
        Encontrar el backup apropiado para restaurar
        """
        if backup_name:
            # Usar backup específico
            backup_path = self.backup_dir / backup_name
            if backup_path.exists():
                return backup_name
            else:
                logger.warning(f"⚠️ Specified backup not found: {backup_name}")
                return None
        
        # Buscar el backup más reciente
        backups = []
        for backup_path in self.backup_dir.iterdir():
            if backup_path.is_dir():
                state_file = backup_path / "system_state.json"
                if state_file.exists():
                    with open(state_file, 'r') as f:
                        state_data = json.load(f)
                    backups.append({
                        "name": backup_path.name,
                        "timestamp": state_data["backup_timestamp"],
                        "path": backup_path
                    })
        
        if backups:
            # Ordenar por timestamp y tomar el más reciente
            backups.sort(key=lambda x: x["timestamp"], reverse=True)
            latest_backup = backups[0]
            logger.info(f"🔍 Found latest backup: {latest_backup['name']}")
            return latest_backup["name"]
        
        logger.warning("⚠️ No backups found")
        return None

    async def _validate_backup(self, backup_name: str) -> bool:
        """
        Validar integridad del backup
        """
        backup_path = self.backup_dir / backup_name
        
        required_files = [
            "trading_config.json",
            "agents_config.json",
            "risk_config.json",
            "system_state.json"
        ]
        
        try:
            for required_file in required_files:
                file_path = backup_path / required_file
                if not file_path.exists():
                    logger.error(f"❌ Missing file in backup: {required_file}")
                    return False
                
                # Validar JSON
                if required_file.endswith('.json'):
                    with open(file_path, 'r') as f:
                        json.load(f)  # Esto valida que sea JSON válido
            
            # Validar estado del sistema
            state_file = backup_path / "system_state.json"
            with open(state_file, 'r') as f:
                state_data = json.load(f)
            
            required_state_fields = ["backup_timestamp", "system_version"]
            for field in required_state_fields:
                if field not in state_data:
                    logger.error(f"❌ Missing field in system state: {field}")
                    return False
            
            logger.info(f"✅ Backup validation passed: {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Backup validation failed: {e}")
            return False

    async def _stop_running_system(self):
        """
        Intentar detener el sistema si está corriendo
        """
        try:
            # Buscar proceso del sistema EAS
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and any('main.py' in str(arg) for arg in cmdline):
                        logger.info(f"🛑 Stopping EAS system process: {proc.info['pid']}")
                        proc.terminate()
                        proc.wait(timeout=10)
                        logger.info("✅ EAS system stopped")
                        return
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    continue
            
            logger.info("ℹ️ No running EAS system found")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not stop running system: {e}")

    async def _restore_configuration(self, backup_name: str):
        """
        Restaurar configuración desde backup
        """
        backup_path = self.backup_dir / backup_name
        
        config_files = [
            "trading_config.json",
            "agents_config.json", 
            "risk_config.json"
        ]
        
        for config_file in config_files:
            source = backup_path / config_file
            destination = self.config_dir / config_file
            
            if source.exists():
                # Crear backup del archivo actual antes de restaurar
                if destination.exists():
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    pre_restore_backup = destination.parent / f"{destination.stem}_pre_restore_{timestamp}{destination.suffix}"
                    shutil.copy2(destination, pre_restore_backup)
                    logger.info(f"📦 Backed up current {config_file} before restore")
                
                # Restaurar archivo
                shutil.copy2(source, destination)
                logger.info(f"✅ Restored {config_file}")
            else:
                logger.warning(f"⚠️ Config file not found in backup: {config_file}")

    async def _restore_default_configs(self) -> str:
        """
        Restaurar configuraciones por defecto
        """
        logger.info("🔄 Restoring default configurations")
        
        default_configs = {
            "trading_config.json": {
                "instrument_specs": {
                    "primary_symbol": "XAUUSD",
                    "trading_session": "NY_OPEN"
                },
                "core_rules": {
                    "risk_per_trade": 0.3,
                    "max_daily_risk": 1.0,
                    "consecutive_loss_limit": 2
                }
            },
            "agents_config.json": {
                "enhanced_consistency_engine": {
                    "temperature": 0.0,
                    "validation_criteria": {
                        "bos_retest_required": True
                    }
                }
            },
            "risk_config.json": {
                "core_risk_parameters": {
                    "fixed_risk_per_trade_percent": 0.3,
                    "max_portfolio_risk_percent": 5.0
                }
            }
        }
        
        backup_name = f"default_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        for config_file, config_data in default_configs.items():
            file_path = self.config_dir / config_file
            with open(file_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            # También guardar en backup
            backup_file = backup_path / config_file
            with open(backup_file, 'w') as f:
                json.dump(config_data, f, indent=2)
        
        # Crear estado del sistema
        system_state = {
            "backup_timestamp": datetime.now().isoformat(),
            "backup_name": backup_name,
            "config_files": list(default_configs.keys()),
            "system_version": "EAS_Hybrid_2025_v1.0",
            "is_default_restore": True
        }
        
        state_file = backup_path / "system_state.json"
        with open(state_file, 'w') as f:
            json.dump(system_state, f, indent=2)
        
        logger.info(f"✅ Default configurations restored: {backup_name}")
        return backup_name

    async def _validate_restored_configuration(self) -> Dict[str, Any]:
        """
        Validar configuración restaurada
        """
        errors = []
        warnings = []
        
        try:
            # Recargar configuraciones
            await self.config_manager.load_all_configs()
            
            # Validar configuración de trading
            trading_config = self.config_manager.get_trading_config()
            if not trading_config.get('instrument_specs', {}).get('primary_symbol'):
                errors.append("Missing primary symbol in trading config")
            
            # Validar configuración de riesgo
            risk_config = self.config_manager.get_risk_config()
            risk_per_trade = risk_config.get('core_risk_parameters', {}).get('fixed_risk_per_trade_percent')
            if risk_per_trade is None or risk_per_trade > 1.0:
                errors.append("Invalid risk per trade configuration")
            
            # Validar configuración de agentes
            agents_config = self.config_manager.get_agents_config()
            if not agents_config.get('enhanced_consistency_engine', {}).get('temperature') == 0.0:
                warnings.append("Agent temperature not set to 0.0 (non-deterministic behavior)")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Configuration validation error: {str(e)}"],
                "warnings": []
            }

    async def _log_rollback_event(self, reason: str, backup_name: str, 
                                start_time: datetime, status: str, 
                                error: str = None) -> Dict[str, Any]:
        """
        Registrar evento de rollback
        """
        rollback_data = {
            "rollback_id": f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "backup_used": backup_name,
            "status": status,
            "duration_seconds": (datetime.now() - start_time).total_seconds(),
            "error": error
        }
        
        # Cargar historial existente
        rollback_history = []
        if self.rollback_log_file.exists():
            with open(self.rollback_log_file, 'r') as f:
                try:
                    rollback_history = json.load(f)
                except json.JSONDecodeError:
                    rollback_history = []
        
        # Agregar nuevo evento
        rollback_history.append(rollback_data)
        
        # Mantener solo los últimos 50 eventos
        if len(rollback_history) > 50:
            rollback_history = rollback_history[-50:]
        
        # Guardar historial
        with open(self.rollback_log_file, 'w') as f:
            json.dump(rollback_history, f, indent=2)
        
        # Log estructurado
        log_data = {
            "rollback_id": rollback_data["rollback_id"],
            "reason": reason,
            "backup_used": backup_name,
            "status": status,
            "duration_seconds": rollback_data["duration_seconds"]
        }
        
        if status == "SUCCESS":
            log_eas_info("EMERGENCY_ROLLBACK_COMPLETED", log_data)
        else:
            log_eas_error("EMERGENCY_ROLLBACK_FAILED", {**log_data, "error": error})
        
        return rollback_data

    async def get_rollback_history(self, limit: int = 10) -> list:
        """
        Obtener historial de rollbacks
        """
        if not self.rollback_log_file.exists():
            return []
        
        try:
            with open(self.rollback_log_file, 'r') as f:
                history = json.load(f)
            
            return history[-limit:]
        except Exception as e:
            logger.error(f"❌ Error reading rollback history: {e}")
            return []

    async def list_backups(self) -> list:
        """
        Listar todos los backups disponibles
        """
        backups = []
        
        for backup_path in self.backup_dir.iterdir():
            if backup_path.is_dir():
                state_file = backup_path / "system_state.json"
                if state_file.exists():
                    with open(state_file, 'r') as f:
                        state_data = json.load(f)
                    
                    backups.append({
                        "name": backup_path.name,
                        "timestamp": state_data["backup_timestamp"],
                        "files": [f.name for f in backup_path.iterdir() if f.is_file()],
                        "is_default_restore": state_data.get("is_default_restore", False)
                    })
        
        return sorted(backups, key=lambda x: x["timestamp"], reverse=True)


async def main():
    """Función principal del script de rollback"""
    parser = argparse.ArgumentParser(description='Emergency Rollback System - EAS Híbrido 2025')
    parser.add_argument('--reason', type=str, required=True,
                       help='Reason for rollback (e.g., "system_instability", "performance_degradation")')
    parser.add_argument('--backup', type=str,
                       help='Specific backup name to restore (optional)')
    parser.add_argument('--force', action='store_true',
                       help='Force rollback even if validation fails')
    parser.add_argument('--create-backup', action='store_true',
                       help='Create a backup before any operations')
    parser.add_argument('--list-backups', action='store_true',
                       help='List available backups')
    parser.add_argument('--history', action='store_true',
                       help='Show rollback history')
    
    args = parser.parse_args()
    
    rollback_system = EmergencyRollbackSystem()
    
    try:
        if args.list_backups:
            # Listar backups
            backups = await rollback_system.list_backups()
            print("\n📦 Available Backups:")
            print("=" * 50)
            for backup in backups:
                print(f"• {backup['name']} - {backup['timestamp']}")
                if backup.get('is_default_restore'):
                    print("  (Default configuration restore)")
            return
        
        if args.history:
            # Mostrar historial
            history = await rollback_system.get_rollback_history(10)
            print("\n📋 Rollback History:")
            print("=" * 50)
            for event in history:
                status_icon = "✅" if event['status'] == 'SUCCESS' else "❌"
                print(f"{status_icon} {event['rollback_id']} - {event['reason']}")
                print(f"  Backup: {event['backup_used']} | Status: {event['status']}")
                if event.get('error'):
                    print(f"  Error: {event['error']}")
            return
        
        if args.create_backup:
            # Crear backup
            backup_name = await rollback_system.create_backup()
            print(f"✅ Backup created: {backup_name}")
            return
        
        # Ejecutar rollback
        print("🚨 INITIATING EMERGENCY ROLLBACK...")
        print(f"Reason: {args.reason}")
        if args.backup:
            print(f"Backup: {args.backup}")
        if args.force:
            print("Force mode: ENABLED")
        
        result = await rollback_system.execute_rollback(
            reason=args.reason,
            backup_name=args.backup,
            force=args.force
        )
        
        if result["success"]:
            print(f"✅ ROLLBACK COMPLETED SUCCESSFULLY")
            print(f"Backup used: {result['backup_used']}")
            print(f"Rollback ID: {result['rollback_id']}")
            print(f"Duration: {result['duration_seconds']:.2f}s")
            
            if result['validation_result']['warnings']:
                print("\n⚠️ Warnings:")
                for warning in result['validation_result']['warnings']:
                    print(f"  • {warning}")
        else:
            print(f"❌ ROLLBACK FAILED")
            print(f"Error: {result['error']}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Rollback script failed: {e}")
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())