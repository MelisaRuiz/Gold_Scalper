[file name]: core/immutable_core.py
[file content begin]
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Núcleo Inmutable EAS Híbrido 2025
Implementa las reglas de disciplina rígida del documento de cumplimiento
Reglas INMUTABLES: 0.3% riesgo, 2 pérdidas consecutivas kill switch, sesión NY exclusiva
"""

import threading
from dataclasses import dataclass, asdict
from typing import Final, Dict, Any, List, Optional, Tuple
from enum import Enum
from datetime import datetime, time
import pytz
import logging

logger = logging.getLogger("HECTAGold.ImmutableCore")

class TradingSession(Enum):
    """Sesiones de trading EAS Híbrido 2025"""
    NY_OPEN = "NY_OPEN"
    LONDON_NY_OVERLAP = "LONDON_NY_OVERLAP"
    CLOSED = "CLOSED"

class SignalType(Enum):
    """Tipos de señal EAS inmutables"""
    BOS_RETEST_BULLISH = "BOS_RETEST_BULLISH"
    BOS_RETEST_BEARISH = "BOS_RETEST_BEARISH"
    LIQUIDITY_SWEEP_BULLISH = "LIQUIDITY_SWEEP_BULLISH" 
    LIQUIDITY_SWEEP_BEARISH = "LIQUIDITY_SWEEP_BEARISH"

@dataclass(frozen=True)
class PatternData:
    """Estructura inmutable para datos de patrón EAS"""
    break_confirmed: bool
    retest_successful: bool
    volume_confirmation: bool
    momentum_aligned: bool
    confidence: float
    liquidity_sweep: bool
    orderblock_retest: bool
    session: str
    timestamp: datetime

    def __post_init__(self):
        # Validar confianza mínima
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError("Confidence must be between 0 and 1")

class ImmutableCore:
    """
    Núcleo inmutable EAS Híbrido 2025
    Implementa las reglas fundamentales que NO pueden modificarse durante la ejecución
    """
    
    # CONSTANTES INMUTABLES (Final) - NÚCLEO EAS 2025
    RISK_PERCENT: Final[float] = 0.3                    # 0.3% riesgo por operación
    MAX_CONSECUTIVE_LOSSES: Final[int] = 2             # Kill Switch
    TRADING_SESSION: Final[TradingSession] = TradingSession.NY_OPEN
    MIN_CONFIDENCE: Final[float] = 0.75                # 75% confianza mínima
    RR_RATIO: Final[float] = 2.0                       # Ratio riesgo/recompensa
    ALLOWED_SYMBOL: Final[str] = "XAUUSD"              # Instrumento exclusivo
    
    # HORARIOS INMUTABLES - Sesión NY (09:30-11:30 ET)
    SESSION_START: Final[time] = time(9, 30)           # 09:30 ET
    SESSION_END: Final[time] = time(11, 30)            # 11:30 ET
    
    def __init__(self):
        self._consecutive_losses = 0
        self._trading_enabled = True
        self._kill_switch_triggered = False
        self._lock = threading.RLock()
        self._initialized = True
        
        # Hacer las constantes verdaderamente inmutables
        self.__dict__['RISK_PERCENT'] = 0.3
        self.__dict__['MAX_CONSECUTIVE_LOSSES'] = 2
        self.__dict__['TRADING_SESSION'] = TradingSession.NY_OPEN
        self.__dict__['MIN_CONFIDENCE'] = 0.75
        self.__dict__['RR_RATIO'] = 2.0
        self.__dict__['ALLOWED_SYMBOL'] = "XAUUSD"
        
        logger.info("🛡️ Núcleo Inmutable EAS Híbrido 2025 inicializado")
        logger.info(f"🎯 Reglas: {self.RISK_PERCENT}% riesgo | {self.MAX_CONSECUTIVE_LOSSES} pérdidas kill switch")
        logger.info(f"🕐 Sesión: {self.SESSION_START}-{self.SESSION_END} ET")

    def __setattr__(self, name, value):
        """Previene cualquier modificación de las constantes inmutables"""
        immutable_constants = [
            'RISK_PERCENT', 'MAX_CONSECUTIVE_LOSSES', 'TRADING_SESSION',
            'MIN_CONFIDENCE', 'RR_RATIO', 'ALLOWED_SYMBOL', 'SESSION_START', 'SESSION_END'
        ]
        
        if name in immutable_constants and hasattr(self, '_initialized'):
            raise AttributeError(f"🚨 {name} es INMUTABLE en EAS Híbrido 2025")
        super().__setattr__(name, value)

    def validate_bos_retest(self, pattern_data: PatternData) -> Tuple[bool, str]:
        """
        Valida patrones Break of Structure + Retest con reglas EAS estrictas
        Implementa la lógica hard-coded del documento EAS
        
        Returns:
            Tuple[bool, str]: (Es válido, Razón)
        """
        with self._lock:
            # 1. Verificar kill switch
            if not self._trading_enabled:
                return False, "Kill switch activado - trading deshabilitado"

            # 2. Verificar sesión de trading
            if not self._is_trading_session_active():
                return False, "Fuera de sesión NY (09:30-11:30 ET)"

            # 3. Kill Switch - 2 pérdidas consecutivas
            if self._consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES:
                self._activate_kill_switch()
                return False, f"Kill switch: {self._consecutive_losses} pérdidas consecutivas"

            # 4. Validación de confianza mínima EAS
            if pattern_data.confidence < self.MIN_CONFIDENCE:
                return False, f"Confianza {pattern_data.confidence:.2f} < {self.MIN_CONFIDENCE}"

            # 5. Validación estricta del patrón BOS + Retest (EAS Híbrido 2025)
            pattern_conditions = [
                (pattern_data.break_confirmed, "Break of Structure no confirmado"),
                (pattern_data.retest_successful, "Retest no exitoso"),
                (pattern_data.volume_confirmation, "Sin confirmación de volumen"),
                (pattern_data.momentum_aligned, "Momentum no alineado"),
                (pattern_data.liquidity_sweep, "Sin liquidity sweep"),  # Requerido EAS
                (pattern_data.orderblock_retest, "Sin order block retest")  # Requerido EAS
            ]

            for condition, reason in pattern_conditions:
                if not condition:
                    return False, reason

            # 6. Verificar sesión del patrón coincide con sesión actual
            if pattern_data.session != self.TRADING_SESSION.value:
                return False, f"Sesión del patrón {pattern_data.session} no coincide con {self.TRADING_SESSION.value}"

            logger.info(f"✅ Patrón BOS_RETEST validado - Confianza: {pattern_data.confidence:.2f}")
            return True, "Patrón BOS_RETEST validado exitosamente"

    def calculate_position_size(self, account_balance: float, stop_loss_pips: float, symbol: str = "XAUUSD") -> float:
        """
        Calcula tamaño de posición con riesgo fijo 0.3% (INMUTABLE)
        
        Args:
            account_balance: Balance de la cuenta
            stop_loss_pips: Stop loss en pips
            symbol: Símbolo de trading (debe ser XAUUSD)
            
        Returns:
            float: Tamaño de posición en lotes
            
        Raises:
            ValueError: Si el símbolo no es XAUUSD o stop_loss_pips es inválido
        """
        with self._lock:
            # Validar símbolo permitido
            if symbol != self.ALLOWED_SYMBOL:
                raise ValueError(f"🚨 Símbolo {symbol} no permitido. Solo {self.ALLOWED_SYMBOL}")

            # Validaciones de seguridad
            if account_balance <= 0:
                raise ValueError("Balance de cuenta debe ser positivo")
                
            if stop_loss_pips <= 0:
                raise ValueError("Stop loss debe ser mayor a 0")

            # Cálculo de riesgo INMUTABLE 0.3%
            risk_amount = account_balance * (self.RISK_PERCENT / 100.0)
            
            # Para XAUUSD, 1 pip = $1 por lote estándar
            pip_value = 1.0  # $1 por pip por lote estándar en XAUUSD
            
            # Cálculo del tamaño de posición
            position_size = risk_amount / (stop_loss_pips * pip_value)
            
            # Normalización a límites del broker
            min_lot = 0.01
            max_lot = 50.0  # Límite conservador
            lot_step = 0.01
            
            # Aplicar límites
            position_size = max(min_lot, min(max_lot, position_size))
            position_size = round(position_size / lot_step) * lot_step
            
            logger.debug(f"📊 Cálculo posición: Balance=${account_balance:.2f}, "
                        f"Riesgo=${risk_amount:.2f}, SL={stop_loss_pips}pips, "
                        f"Lotes={position_size:.2f}")
            
            return position_size

    def record_trade_result(self, is_win: bool, pnl: float = 0.0):
        """
        Registra resultado de operación para el kill switch EAS
        
        Args:
            is_win: True si la operación fue ganadora
            pnl: Profit & Loss de la operación
        """
        with self._lock:
            if is_win:
                self._consecutive_losses = 0  # Resetear contador
                logger.info(f"✅ Operación ganadora - PnL: ${pnl:.2f}")
            else:
                self._consecutive_losses += 1
                logger.warning(f"❌ Operación perdedora - PnL: ${pnl:.2f} | "
                              f"Pérdidas consecutivas: {self._consecutive_losses}")

            # Activar kill switch si se alcanza el límite INMUTABLE
            if self._consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES:
                self._activate_kill_switch()

    def _is_trading_session_active(self) -> bool:
        """
        Verifica si estamos en la sesión de trading NY (09:30-11:30 ET)
        Implementación INMUTABLE del horario EAS
        """
        try:
            eastern = pytz.timezone('US/Eastern')
            now = datetime.now(eastern)
            current_time = now.time()
            
            # Verificar día hábil (Lunes-Viernes)
            if now.weekday() >= 5:  # 5=Sábado, 6=Domingo
                return False
            
            # Verificar horario de sesión NY
            session_active = self.SESSION_START <= current_time <= self.SESSION_END
            
            return session_active
            
        except Exception as e:
            logger.error(f"❌ Error verificando sesión: {e}")
            return False

    def _activate_kill_switch(self):
        """Activa kill switch EAS por pérdidas consecutivas"""
        self._trading_enabled = False
        self._kill_switch_triggered = True
        
        logger.critical(f"🔴 KILL SWITCH ACTIVADO - {self._consecutive_losses} pérdidas consecutivas")
        
        # Aquí se podría integrar con el sistema de alertas
        # self._send_kill_switch_alert()

    def reset_kill_switch(self, reason: str = "Intervención manual") -> bool:
        """
        Resetea el kill switch (solo para condiciones controladas)
        
        Args:
            reason: Razón para el reset
            
        Returns:
            bool: True si se pudo resetear
        """
        with self._lock:
            if not self._kill_switch_triggered:
                logger.warning("⚠️ Intento de resetear kill switch no activo")
                return False
                
            self._consecutive_losses = 0
            self._trading_enabled = True
            self._kill_switch_triggered = False
            
            logger.warning(f"🟢 Kill Switch reseteado - Razón: {reason}")
            return True

    def validate_signal_against_rules(self, signal_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Valida señal completa contra todas las reglas EAS inmutables
        
        Args:
            signal_data: Datos de la señal a validar
            
        Returns:
            Tuple[bool, str]: (Es válida, Razón)
        """
        try:
            # 1. Validar símbolo
            symbol = signal_data.get('symbol', '')
            if symbol != self.ALLOWED_SYMBOL:
                return False, f"Símbolo {symbol} no permitido"

            # 2. Validar sesión
            if not self._is_trading_session_active():
                return False, "Fuera de sesión NY"

            # 3. Validar kill switch
            if self._kill_switch_triggered:
                return False, "Kill switch activado"

            # 4. Validar confianza
            confidence = signal_data.get('confidence', 0)
            if confidence < self.MIN_CONFIDENCE:
                return False, f"Confianza {confidence:.2f} < {self.MIN_CONFIDENCE}"

            # 5. Validar riesgo
            risk_percent = signal_data.get('risk_percent', 0)
            if risk_percent > self.RISK_PERCENT:
                return False, f"Riesgo {risk_percent}% > {self.RISK_PERCENT}%"

            # 6. Validar ratio R/R
            rr_ratio = signal_data.get('risk_reward_ratio', 0)
            if rr_ratio < self.RR_RATIO:
                return False, f"Ratio R/R {rr_ratio} < {self.RR_RATIO}"

            return True, "Señal válida según reglas EAS"

        except Exception as e:
            return False, f"Error en validación: {str(e)}"

    def get_immutable_status(self) -> Dict[str, Any]:
        """Retorna estado completo del núcleo inmutable (para monitoreo)"""
        with self._lock:
            return {
                "trading_enabled": self._trading_enabled,
                "consecutive_losses": self._consecutive_losses,
                "kill_switch_triggered": self._kill_switch_triggered,
                "immutable_rules": {
                    "risk_percent": self.RISK_PERCENT,
                    "max_consecutive_losses": self.MAX_CONSECUTIVE_LOSSES,
                    "trading_session": self.TRADING_SESSION.value,
                    "min_confidence": self.MIN_CONFIDENCE,
                    "rr_ratio": self.RR_RATIO,
                    "allowed_symbol": self.ALLOWED_SYMBOL,
                    "session_hours": f"{self.SESSION_START}-{self.SESSION_END} ET"
                },
                "current_session_active": self._is_trading_session_active(),
                "system_uptime": getattr(self, '_start_time', datetime.now()).isoformat()
            }

    def emergency_stop(self, reason: str = "Emergencia"):
        """
        Parada de emergencia del sistema EAS
        Sobreescribe cualquier estado y desactiva trading
        """
        with self._lock:
            self._trading_enabled = False
            self._kill_switch_triggered = True
            
            logger.critical(f"🚨 PARADA DE EMERGENCIA: {reason}")

# Instancia global del núcleo inmutable
IMMUTABLE_CORE = ImmutableCore()
[file content end]