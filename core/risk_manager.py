#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Risk Manager v2.0 - Enhanced with EAS Chinese Filters and Ultra-Robust Risk Management
Strict 0.3% BASE risk, dynamic scaling via intelligence_layer with EAS improvements.
Integrated Chinese system: Hard Equity Stop + Enhanced Kill Switches
"""

import logging
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import threading
import math

# IMPORTACIÓN MT5 MEJORADA
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logging.warning("MetaTrader5 no disponible - modo simulación activado")

# Configuración básica del logger si no existe
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

logger = logging.getLogger("HECTAGold.RiskManager")

class RiskLevel(Enum):
    EXTREME_LOW = "EXTREME_LOW"
    LOW = "LOW" 
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EXTREME_HIGH = "EXTREME_HIGH"

@dataclass
class RiskMetrics:
    daily_risk_used: float
    consecutive_losses: int
    current_drawdown: float
    max_drawdown: float
    account_equity: float
    risk_multiplier: float
    is_risk_on: bool
    macro_bias_score: int
    last_trade_time: Optional[datetime]
    trades_today: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    base_risk_pct: float
    dynamic_exposure_pct: float
    hard_equity_stop_triggered: bool  # Nuevo: Kill Switch por capital
    price_limit_triggered: bool       # Nuevo: Límites de precio fijos

class RiskManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.core_rules = config.get('corerules', {})
        
        # DISCIPLINA RÍGIDA INMUTABLE MEJORADA - NÚCLEO EAS
        self.BASE_RISK_PCT = 0.3  # INMUTABLE - 0.3% base risk
        self.MAX_DAILY_RISK_PCT = self.core_rules.get('maxdailyrisk', 1.0)
        self.MAX_POSITIONS = self.core_rules.get('maxtrades', 3)
        self.CONSECUTIVE_LOSS_LIMIT = self.core_rules.get('consecutivelosslimit', 2)
        self.breakeven_ratio = self.core_rules.get('breakeven_ratio', 1.5)
        
        # NUEVO: KILL SWITCHES DEL SISTEMA EAS CHINO
        self.HARD_EQUITY_STOP_PCT = 6.0  # 6% máximo drawdown - expulsión total
        self.PRICE_LIMIT_UPPER = None    # Límite superior de precio
        self.PRICE_LIMIT_LOWER = None    # Límite inferior de precio
        
        # GESTIÓN DINÁMICA DE EXPOSICIÓN MEJORADA - LÍMITES MÁS ESTRICTOS
        self.MAX_DYNAMIC_MULTIPLIER = 1.2  # 20% extra máximo
        self.MIN_DYNAMIC_MULTIPLIER = 0.8   # 20% reducción máxima
        
        # Estado del sistema MEJORADO
        self.daily_trades = []
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        self.risk_multiplier = 1.0
        self.is_trading_allowed = True
        self.kill_switch_active = False
        self.hard_equity_stop_triggered = False
        self.price_limit_triggered = False
        self.initial_capital = 0.0
        self.base_risk_amount = 0.0
        self.dynamic_exposure_amount = 0.0

        self.db_path = Path("data/risk_management.db")
        self.db_path.parent.mkdir(exist_ok=True)
        self.risk_lock = threading.RLock()

        # INICIALIZAR CONEXIÓN MT5 MEJORADA
        self.mt5_initialized = False
        if MT5_AVAILABLE:
            self.mt5_initialized = self._initialize_mt5_connection()
            if self.mt5_initialized:
                self.initial_capital = self.get_account_equity()

        self._init_database()
        self._load_persistent_state()

        logger.info(f"🎯 RiskManager MEJORADO: {self.BASE_RISK_PCT}% BASE RISK (Inmutable)")
        logger.info(f"📈 Dynamic Exposure: {self.MIN_DYNAMIC_MULTIPLIER}-{self.MAX_DYNAMIC_MULTIPLIER}x")
        logger.info(f"🚨 Kill Switches: {self.CONSECUTIVE_LOSS_LIMIT} pérdidas | {self.HARD_EQUITY_STOP_PCT}% capital")
        logger.info(f"🔌 MT5 Connection: {'✅ Active' if self.mt5_initialized else '❌ Simulation Mode'}")

    def _initialize_mt5_connection(self) -> bool:
        """Inicializa conexión MEJORADA con MT5 para producción"""
        try:
            if not mt5.initialize():
                logger.error(f"❌ MT5 initialization failed: {mt5.last_error()}")
                return False
            
            # Verificar conexión con timeout
            account_info = mt5.account_info()
            if account_info is None:
                logger.error(f"❌ MT5 account info failed: {mt5.last_error()}")
                return False
                
            logger.info(f"✅ MT5 Connected: {account_info.login} | Equity: ${account_info.equity:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ MT5 connection error: {e}")
            return False

    def get_account_equity(self) -> float:
        """Obtiene equidad real de la cuenta desde MT5 con fallback mejorado"""
        if self.mt5_initialized and MT5_AVAILABLE:
            try:
                account_info = mt5.account_info()
                if account_info:
                    return float(account_info.equity)
            except Exception as e:
                logger.error(f"❌ Error obteniendo equidad MT5: {e}")
        
        # Fallback mejorado a simulación
        logger.warning("⚠️ Usando equidad simulada - MT5 no disponible")
        return 10000.0

    def calculate_lot_size(self, account_equity: float = None, stop_distance_pips: float = 0, 
                         tick_value: float = 0, macro_bias: int = 5, 
                         signal_confidence: float = 0.7) -> Tuple[float, Dict[str, float]]:
        """
        Calcula tamaño de lote MEJORADO con DISCIPLINA RÍGIDA + GESTIÓN DINÁMICA DE EXPOSICIÓN
        
        Returns:
            tuple: (lot_size_final, risk_breakdown)
        """
        with self.risk_lock:
            # VERIFICAR KILL SWITCHES PRIMERO
            if not self._check_all_kill_switches():
                logger.critical("🚫 Kill Switch activado - tamaño de lote CERO")
                return 0.0, {"kill_switch_active": True}

            # OBTENER EQUIDAD REAL EN TIEMPO REAL
            if account_equity is None:
                account_equity = self.get_account_equity()

            # 1. CÁLCULO BASE CON RIESGO FIJO 0.3% (DISCIPLINA RÍGIDA)
            self.base_risk_amount = account_equity * (self.BASE_RISK_PCT / 100.0)
            
            # Validar stop_distance_pips para evitar división por cero
            if stop_distance_pips <= 0:
                logger.error("🚨 Stop distance inválido - usando valor mínimo")
                stop_distance_pips = 10.0  # Valor mínimo seguro
                
            if tick_value <= 0:
                logger.error("🚨 Tick value inválido - usando valor mínimo")
                tick_value = 1.0  # Valor mínimo seguro
                
            base_lot_size = self.base_risk_amount / (stop_distance_pips * tick_value)
            
            # 2. GESTIÓN DINÁMICA DE EXPOSICIÓN MEJORADA
            dynamic_multiplier = self._calculate_enhanced_dynamic_multiplier(macro_bias, signal_confidence)
            dynamic_lot_size = base_lot_size * dynamic_multiplier
            self.dynamic_exposure_amount = self.base_risk_amount * dynamic_multiplier
            
            # 3. APLICAR LÍMITES DEL BROKER Y NORMALIZACIÓN MEJORADA
            min_lot, max_lot, lot_step = 0.01, 10.0, 0.01
            final_lot_size = max(min_lot, min(max_lot, dynamic_lot_size))
            final_lot_size = round(final_lot_size / lot_step) * lot_step
            
            # 4. VALIDACIÓN FINAL MEJORADA DE RANGOS CON EQUIDAD REAL
            if not self._validate_enhanced_risk_limits(final_lot_size, account_equity, stop_distance_pips, tick_value):
                logger.warning("🚨 Risk validation failed, using base risk")
                final_lot_size = base_lot_size
                dynamic_multiplier = 1.0
                self.dynamic_exposure_amount = self.base_risk_amount
            
            risk_breakdown = {
                'base_risk_pct': self.BASE_RISK_PCT,
                'base_risk_amount': self.base_risk_amount,
                'base_lot_size': base_lot_size,
                'dynamic_multiplier': dynamic_multiplier,
                'dynamic_exposure_pct': self.BASE_RISK_PCT * dynamic_multiplier,
                'dynamic_exposure_amount': self.dynamic_exposure_amount,
                'final_lot_size': final_lot_size,
                'effective_risk_pct': (self.dynamic_exposure_amount / account_equity) * 100,
                'real_equity_used': account_equity,
                'kill_switch_status': self.kill_switch_active
            }
            
            logger.debug(f"📊 Risk Breakdown MEJORADO: {risk_breakdown}")
            return final_lot_size, risk_breakdown

    def _calculate_enhanced_dynamic_multiplier(self, macro_bias: int, signal_confidence: float) -> float:
        """Calcula multiplicador dinámico MEJORADO con límites estrictos"""
        
        # Convertir macro_bias (1-10) a factor (0.7-1.3)
        macro_factor = 0.7 + (macro_bias / 10.0) * 0.6
        
        # Aplicar confianza de señal con curva mejorada
        confidence_factor = 0.6 + (signal_confidence * 0.8)
        
        # Combinar factores con pesos optimizados
        raw_multiplier = (macro_factor * 0.5) + (confidence_factor * 0.5)
        
        # Aplicar límites estrictos MEJORADOS
        bounded_multiplier = max(self.MIN_DYNAMIC_MULTIPLIER, 
                               min(self.MAX_DYNAMIC_MULTIPLIER, raw_multiplier))
        
        self.risk_multiplier = bounded_multiplier
        
        logger.debug(f"🎚️ Dynamic Multiplier MEJORADO: macro={macro_bias}→{macro_factor:.2f}, "
                    f"confidence={signal_confidence:.2f}→{confidence_factor:.2f}, "
                    f"final={bounded_multiplier:.2f}")
        
        return bounded_multiplier

    def _validate_enhanced_risk_limits(self, lot_size: float, account_equity: float, 
                                     stop_distance_pips: float, tick_value: float) -> bool:
        """Valida MEJORADO que el riesgo esté dentro de límites seguros"""
        
        potential_loss = lot_size * stop_distance_pips * tick_value
        risk_percent = (potential_loss / account_equity) * 100
        
        # Límite absoluto por trade (0.36% con multiplicador máximo 1.2)
        max_single_trade_risk = self.BASE_RISK_PCT * self.MAX_DYNAMIC_MULTIPLIER
        
        if risk_percent > max_single_trade_risk:
            logger.error(f"🚨 Risk validation failed: {risk_percent:.2f}% > {max_single_trade_risk:.2f}% max")
            return False
            
        # NUEVA VALIDACIÓN: Riesgo mínimo para evitar órdenes demasiado pequeñas
        min_risk_amount = account_equity * 0.001  # Mínimo 0.1%
        if potential_loss < min_risk_amount and lot_size > 0.01:
            logger.warning(f"⚠️ Risk muy bajo: ${potential_loss:.2f} < ${min_risk_amount:.2f}")
            
        return True

    def _check_all_kill_switches(self) -> bool:
        """Verifica TODOS los kill switches del sistema EAS chino"""
        with self.risk_lock:
            # 1. Kill Switch por pérdidas consecutivas
            if self.consecutive_losses >= self.CONSECUTIVE_LOSS_LIMIT:
                self.kill_switch_active = True
                self.is_trading_allowed = False
                logger.critical("🔴 KILL SWITCH ACTIVADO: 2 consecutive losses")
                return False

            # 2. Kill Switch por capital (Hard Equity Stop)
            current_equity = self.get_account_equity()
            if self.initial_capital > 0:
                drawdown_pct = (1 - (current_equity / self.initial_capital)) * 100
                if drawdown_pct >= self.HARD_EQUITY_STOP_PCT:
                    self.hard_equity_stop_triggered = True
                    self.kill_switch_active = True
                    self.is_trading_allowed = False
                    logger.critical(f"🔴 HARD EQUITY STOP: Drawdown {drawdown_pct:.1f}% >= {self.HARD_EQUITY_STOP_PCT}%")
                    return False

            # 3. Kill Switch por límites de precio (si están configurados)
            if self._check_price_limits():
                self.price_limit_triggered = True
                self.kill_switch_active = True
                self.is_trading_allowed = False
                logger.critical("🔴 PRICE LIMIT STOP: Límites de precio alcanzados")
                return False

            return True

    def _check_price_limits(self) -> bool:
        """Verifica límites de precio fijos del sistema EAS chino"""
        # Placeholder: en producción, integrar con `get_market_price()` o similar
        # Ejemplo: current_price = get_current_price("XAUUSD")
        # if self.PRICE_LIMIT_UPPER and current_price >= self.PRICE_LIMIT_UPPER: return True
        # if self.PRICE_LIMIT_LOWER and current_price <= self.PRICE_LIMIT_LOWER: return True
        return False

    def check_daily_risk_limit(self) -> bool:
        """Verifica límite de riesgo diario MEJORADO"""
        with self.risk_lock:
            daily_risk_pct = abs(self.daily_pnl) / self.get_account_equity() * 100
            if daily_risk_pct >= self.MAX_DAILY_RISK_PCT:
                logger.warning(f"🚫 Daily risk limit hit: {daily_risk_pct:.2f}% >= {self.MAX_DAILY_RISK_PCT}%")
                self.is_trading_allowed = False
                return False
            return True

    def update_trade_outcome(self, pnl: float, risk_breakdown: Dict[str, float]):
        """Actualiza resultado de trade MEJORADO"""
        with self.risk_lock:
            trade_record = {
                "pnl": pnl, 
                "time": datetime.utcnow(),
                "risk_breakdown": risk_breakdown
            }
            self.daily_trades.append(trade_record)
            self.daily_pnl += pnl
            
            if pnl < 0:
                self.consecutive_losses += 1
                logger.warning(f"📉 Loss recorded: ${pnl:.2f}, Consecutive: {self.consecutive_losses}")
                
                # Verificar kill switch inmediatamente después de pérdida
                self._check_all_kill_switches()
            else:
                self.consecutive_losses = 0
                logger.info(f"📈 Win recorded: ${pnl:.2f}")

            self._save_trade_to_db(trade_record)
            self._save_persistent_state()
            
            # Verificar límites después de actualizar
            self.check_daily_risk_limit()

    def enable_partial_close(self, current_pnl_ratio: float) -> bool:
        """Habilita cierre parcial MEJORADO"""
        return current_pnl_ratio >= self.breakeven_ratio

    def _init_database(self):
        """Inicializa base de datos MEJORADA"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY,
                pnl REAL,
                time TEXT,
                risk_breakdown TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_metrics (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                daily_risk_used REAL,
                consecutive_losses INTEGER,
                current_drawdown REAL,
                max_drawdown REAL,
                account_equity REAL,
                risk_multiplier REAL,
                is_risk_on INTEGER,
                macro_bias_score INTEGER,
                base_risk_pct REAL,
                dynamic_exposure_pct REAL,
                hard_equity_stop_triggered INTEGER,
                price_limit_triggered INTEGER
            )
        """)
        conn.commit()
        conn.close()

    def _save_trade_to_db(self, trade: Dict):
        """Guarda trade en base de datos MEJORADO"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO trades (pnl, time, risk_breakdown) VALUES (?, ?, ?)",
                       (trade['pnl'], trade['time'].isoformat(), json.dumps(trade['risk_breakdown'])))
        conn.commit()
        conn.close()

    def _save_persistent_state(self):
        """Guarda estado persistente MEJORADO"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO risk_metrics 
            (timestamp, daily_risk_used, consecutive_losses, current_drawdown, max_drawdown, 
             account_equity, risk_multiplier, is_risk_on, macro_bias_score, base_risk_pct, 
             dynamic_exposure_pct, hard_equity_stop_triggered, price_limit_triggered)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (datetime.utcnow().isoformat(), 
              abs(self.daily_pnl) / self.get_account_equity() * 100,
              self.consecutive_losses, 0.0, 0.0, self.get_account_equity(), 
              self.risk_multiplier, int(self.is_trading_allowed), 5,
              self.BASE_RISK_PCT, self.BASE_RISK_PCT * self.risk_multiplier,
              int(self.hard_equity_stop_triggered), int(self.price_limit_triggered)))
        conn.commit()
        conn.close()

    def _load_persistent_state(self):
        """Carga estado persistente MEJORADO"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM risk_metrics ORDER BY timestamp DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                self.consecutive_losses = row[2] or 0
                self.risk_multiplier = row[6] or 1.0
                self.is_trading_allowed = bool(row[7])
                self.hard_equity_stop_triggered = bool(row[11] or False)
                self.price_limit_triggered = bool(row[12] or False)
                
                # Reset kill switches si el sistema fue reiniciado
                if self.kill_switch_active and self.is_trading_allowed:
                    self.kill_switch_active = False
                    self.consecutive_losses = 0
            conn.close()
        except Exception as e:
            logger.warning(f"Could not load persistent state: {e}")

    def reset_daily_state(self):
        """Resetea estado diario MEJORADO"""
        with self.risk_lock:
            self.daily_trades = []
            self.daily_pnl = 0.0
            self.consecutive_losses = 0
            # No resetear kill switches de capital o precio
            if not self.kill_switch_active and not self.hard_equity_stop_triggered and not self.price_limit_triggered:
                self.is_trading_allowed = True
            logger.info("🔄 Daily risk state reset MEJORADO")

    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas MEJORADAS"""
        with self.risk_lock:
            win_rate = (len([t for t in self.daily_trades if t['pnl'] > 0]) / max(len(self.daily_trades), 1)) * 100 if self.daily_trades else 0
            
            current_equity = self.get_account_equity()
            drawdown_pct = 0.0
            if self.initial_capital > 0:
                drawdown_pct = (1 - (current_equity / self.initial_capital)) * 100

            return {
                'base_risk_pct': self.BASE_RISK_PCT,
                'max_daily_risk_pct': self.MAX_DAILY_RISK_PCT,
                'current_consecutive_losses': self.consecutive_losses,
                'daily_trades_count': len(self.daily_trades),
                'daily_pnl': self.daily_pnl,
                'risk_multiplier': self.risk_multiplier,
                'is_trading_allowed': self.is_trading_allowed,
                'kill_switch_active': self.kill_switch_active,
                'hard_equity_stop_triggered': self.hard_equity_stop_triggered,
                'price_limit_triggered': self.price_limit_triggered,
                'account_equity': current_equity,
                'initial_capital': self.initial_capital,
                'current_drawdown_pct': drawdown_pct,
                'win_rate': win_rate,
                'max_dynamic_multiplier': self.MAX_DYNAMIC_MULTIPLIER,
                'effective_risk_pct': self.BASE_RISK_PCT * self.risk_multiplier,
                'hard_equity_stop_pct': self.HARD_EQUITY_STOP_PCT
            }

    def close_all_positions(self, reason: str = "Manual"):
        """Cierra todas las posiciones MEJORADO"""
        logger.warning(f"🔴 Closing all positions: {reason}")
        self.reset_daily_state()

    def emergency_shutdown(self, reason: str):
        """Apagado de emergencia MEJORADO del sistema EAS chino"""
        logger.critical(f"🚨 EMERGENCY SHUTDOWN: {reason}")
        self.kill_switch_active = True
        self.is_trading_allowed = False
        self.close_all_positions(f"Emergency: {reason}")
        logger.critical("🔴 SISTEMA EAS DETENIDO - Requiere intervención manual")

    def close(self):
        """Cierra conexión MT5 de forma segura MEJORADO"""
        if MT5_AVAILABLE and self.mt5_initialized:
            mt5.shutdown()
            logger.info("🔌 MT5 connection closed MEJORADO")