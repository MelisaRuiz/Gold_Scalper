#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Session Manager - EAS Híbrido 2025 Compliant
Optimized for London-NY Overlap (13:00-17:00 GMT) with strict EAS rules.
Integrated with AdvancedNewsFilter for unified blocking decisions.
"""

import logging
import pytz
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional, List
from enum import Enum
import aiohttp
import asyncio
from dataclasses import dataclass

logger = logging.getLogger("HECTAGold.SessionManager")

class SessionPhase(Enum):
    """Fases de sesión optimizadas para EAS Híbrido 2025"""
    CLOSED = "closed"
    PREMARKET = "premarket"           # 12:00-13:00 GMT
    LONDON_NY_OVERLAP = "overlap"     # 13:00-17:00 GMT (ÓPTIMO)
    NY_CORE = "ny_core"               # 09:30-11:30 ET (13:30-15:30 GMT)
    POST_SESSION = "post_session"
    HOLIDAY = "holiday"
    NEWS_BLOCKED = "news_blocked"

@dataclass
class SessionMetrics:
    """Métricas de sesión en tiempo real"""
    current_phase: SessionPhase
    time_remaining: timedelta
    liquidity_score: float
    volatility_profile: str
    optimal_trading: bool
    reason: str

class SessionManager:
    """
    Gestor de sesiones EAS Híbrido 2025 - Optimizado para XAUUSD Scalping
    Implementa reglas estrictas: London-NY Overlap exclusivo
    """
    
    def __init__(self, config: Dict[str, Any], news_filter=None):
        """
        Inicializa Session Manager compliant con EAS Híbrido 2025
        
        Args:
            config: Configuración del sistema
            news_filter: Instancia de AdvancedNewsFilter para decisiones unificadas
        """
        self.config = config
        self.news_filter = news_filter
        
        # TIMEZONES CRÍTICAS PARA TRADING INTERNACIONAL
        self.gmt = pytz.timezone('GMT')
        self.ny_tz = pytz.timezone('America/New_York')
        self.london_tz = pytz.timezone('Europe/London')
        
        # HORARIOS ESTRICTOS EAS HÍBRIDO 2025
        self.session_config = {
            # OVERLAP LONDRES-NY (ÓPTIMO SEGÚN EAS)
            'london_ny_overlap': {
                'start_gmt': 13,  # 13:00 GMT
                'end_gmt': 17,    # 17:00 GMT  
                'description': 'London-NY Overlap - Máxima liquidez XAUUSD'
            },
            # SESIÓN NÚCLEO NY (COMPLEMENTARIA)
            'ny_core_session': {
                'start_et': 9.5,   # 09:30 ET
                'end_et': 11.5,    # 11:30 ET
                'description': 'NY Core Session - Apertura mercados US'
            },
            # PREMARKET (PREPARACIÓN)
            'premarket': {
                'start_gmt': 12,   # 12:00 GMT  
                'end_gmt': 13,     # 13:00 GMT
                'description': 'Premarket - Preparación overlap'
            }
        }
        
        # GESTIÓN DE FERIADOS - ACTUALIZADO PARA API EXTERNA
        self.holidays: List[str] = []
        self.holiday_cache_duration = 3600  # 1 hora para trading activo
        self.last_holiday_update = None
        
        # CLIENTE HTTP MEJORADO
        self.session: Optional[aiohttp.ClientSession] = None
        
        # CACHE DE ALTO RENDIMIENTO
        self._session_cache = {}
        self._cache_ttl = 5  # 5 segundos para scalping
        
        # MÉTRICAS EN TIEMPO REAL
        self.session_metrics = SessionMetrics(
            current_phase=SessionPhase.CLOSED,
            time_remaining=timedelta(0),
            liquidity_score=0.0,
            volatility_profile='unknown',
            optimal_trading=False,
            reason='Initializing'
        )
        
        logger.info("🕐 SessionManager EAS Híbrido 2025 inicializado")
        logger.info("🎯 Horarios: London-NY Overlap 13:00-17:00 GMT")

    async def initialize(self):
        """Inicialización asíncrona optimizada"""
        connector = aiohttp.TCPConnector(limit=3, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(total=10, connect=5)  # Timeouts optimizados
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        
        # Cargar feriados de forma asíncrona
        await self._load_holidays_async()
        
        logger.info("✅ SessionManager inicializado")

    async def _load_holidays_async(self):
        """Carga asíncrona de feriados desde API externa"""
        try:
            success = await self._fetch_holidays_from_api()
            if not success:
                self._load_default_holidays()
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron cargar feriados: {e}")
            self._load_default_holidays()

    async def _fetch_holidays_from_api(self) -> bool:
        """
        Obtiene feriados desde API económica externa confiable
        Reemplaza la lista hard-coded original
        """
        try:
            current_year = datetime.now().year
            
            # API 1: Date.nager.at (pública y confiable)
            url = f"https://date.nager.at/api/v3/PublicHolidays/{current_year}/US"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    holidays_data = await response.json()
                    self.holidays = [holiday['date'] for holiday in holidays_data]
                    self.last_holiday_update = datetime.now()
                    
                    logger.info(f"📅 Cargados {len(self.holidays)} feriados US desde API pública")
                    return True
            
            # Fallback API 2: Calendarific (requiere API key en producción)
            # await self._fetch_holidays_calendarific(current_year)
            
        except Exception as e:
            logger.error(f"❌ Error cargando feriados desde API: {e}")
            return False
        
        return False

    async def _fetch_holidays_calendarific(self, year: int):
        """Método alternativo usando Calendarific API (requiere API key)"""
        try:
            # Este método requiere API key configurada
            api_key = self.config.get('calendarific_api_key')
            if not api_key:
                return
                
            url = f"https://calendarific.com/api/v2/holidays"
            params = {
                'api_key': api_key,
                'country': 'US',
                'year': year
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['response']['holidays']:
                        self.holidays = [h['date']['iso'] for h in data['response']['holidays']]
                        logger.info(f"📅 Cargados {len(self.holidays)} feriados desde Calendarific")
                        
        except Exception as e:
            logger.error(f"❌ Error con Calendarific API: {e}")

    def _load_default_holidays(self):
        """Carga feriados por defecto para respaldo (mejorada)"""
        current_year = datetime.now().year
        
        # Feriados principales US para trading
        default_holidays = [
            f"{current_year}-01-01",  # New Year's Day
            f"{current_year}-01-15",  # MLK Day (third Monday)
            f"{current_year}-02-19",  # Presidents Day (third Monday)
            f"{current_year}-05-27",  # Memorial Day (last Monday)
            f"{current_year}-07-04",  # Independence Day
            f"{current_year}-09-02",  # Labor Day (first Monday)
            f"{current_year}-11-28",  # Thanksgiving (fourth Thursday)
            f"{current_year}-12-25",  # Christmas
        ]
        
        self.holidays = default_holidays
        logger.info("📅 Usando feriados por defecto de respaldo")

    def is_holiday(self, date: datetime) -> bool:
        """Verifica si es feriado en zona NY con cache"""
        # Verificar si necesita actualización
        if (self.last_holiday_update is None or 
            (datetime.now() - self.last_holiday_update).total_seconds() > self.holiday_cache_duration):
            asyncio.create_task(self._load_holidays_async())
        
        ny_date = date.astimezone(self.ny_tz)
        date_str = ny_date.strftime('%Y-%m-%d')
        return date_str in self.holidays

    async def is_trading_allowed(self, current_time: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        DECISIÓN PRINCIPAL: Verifica si el trading está permitido
        Integrado con News Filter para decisiones unificadas
        
        Returns:
            (is_allowed, reason)
        """
        if current_time is None:
            current_time = datetime.now(pytz.utc)
            
        # 1. VERIFICAR CACHE (optimización performance)
        cache_key = f"trading_allowed_{current_time.minute}"
        if cache_key in self._session_cache:
            cached_time, cached_result = self._session_cache[cache_key]
            if (datetime.now(pytz.utc) - cached_time).total_seconds() < self._cache_ttl:
                return cached_result
        
        # 2. VERIFICAR FERIADOS
        if self.is_holiday(current_time):
            result = (False, "US market holiday")
            self._session_cache[cache_key] = (datetime.now(pytz.utc), result)
            return result
        
        # 3. VERIFICAR BLOQUEO POR NOTICIAS (usando AdvancedNewsFilter)
        if self.news_filter:
            try:
                news_blocked, news_reason = self.news_filter.should_block_trading(current_time)
                if news_blocked:
                    result = (False, f"News block: {news_reason}")
                    self._session_cache[cache_key] = (datetime.now(pytz.utc), result)
                    return result
            except Exception as e:
                logger.warning(f"⚠️ Error consultando news filter: {e}")
        
        # 4. VERIFICAR SESIÓN ACTIVA
        session_active, session_phase = self._is_session_active(current_time)
        
        if not session_active:
            result = (False, f"Outside session: {session_phase}")
            self._session_cache[cache_key] = (datetime.now(pytz.utc), result)
            return result
        
        # 5. SESIÓN ACTIVA - VERIFICAR CALIDAD
        if session_phase == SessionPhase.LONDON_NY_OVERLAP:
            result = (True, "Optimal London-NY overlap session")
        elif session_phase == SessionPhase.NY_CORE:
            result = (True, "NY core session - good conditions")
        elif session_phase == SessionPhase.PREMARKET:
            result = (True, "Premarket session - caution advised")
        else:
            result = (True, f"Active session: {session_phase}")
        
        self._session_cache[cache_key] = (datetime.now(pytz.utc), result)
        return result

    def _is_session_active(self, current_time: datetime) -> Tuple[bool, SessionPhase]:
        """
        Determina si estamos en sesión activa según EAS Híbrido 2025
        
        Prioridad:
        1. London-NY Overlap (13:00-17:00 GMT) - ÓPTIMO
        2. NY Core Session (09:30-11:30 ET) - SECUNDARIO
        3. Premarket (12:00-13:00 GMT) - PREPARACIÓN
        """
        gmt_time = current_time.astimezone(self.gmt)
        gmt_hour = gmt_time.hour + gmt_time.minute / 60.0
        
        et_time = current_time.astimezone(self.ny_tz)
        et_hour = et_time.hour + et_time.minute / 60.0
        
        # 1. LONDON-NY OVERLAP (ÓPTIMO EAS)
        overlap_start = self.session_config['london_ny_overlap']['start_gmt']
        overlap_end = self.session_config['london_ny_overlap']['end_gmt']
        
        if overlap_start <= gmt_hour < overlap_end:
            return True, SessionPhase.LONDON_NY_OVERLAP
        
        # 2. NY CORE SESSION (APERTURA NY)
        ny_start = self.session_config['ny_core_session']['start_et']
        ny_end = self.session_config['ny_core_session']['end_et']
        
        if ny_start <= et_hour < ny_end:
            return True, SessionPhase.NY_CORE
        
        # 3. PREMARKET (PREPARACIÓN)
        premarket_start = self.session_config['premarket']['start_gmt']
        premarket_end = self.session_config['premarket']['end_gmt']
        
        if premarket_start <= gmt_hour < premarket_end:
            return True, SessionPhase.PREMARKET
        
        return False, SessionPhase.CLOSED

    def get_session_metrics(self, current_time: Optional[datetime] = None) -> SessionMetrics:
        """
        Obtiene métricas completas de sesión para toma de decisiones
        """
        if current_time is None:
            current_time = datetime.now(pytz.utc)
            
        # Determinar fase actual
        is_active, current_phase = self._is_session_active(current_time)
        
        # Calcular tiempo restante
        time_remaining = self._calculate_time_remaining(current_time, current_phase)
        
        # Calcular score de liquidez (simulado - en producción usar datos reales)
        liquidity_score = self._calculate_liquidity_score(current_phase)
        
        # Determinar perfil de volatilidad
        volatility_profile = self._get_volatility_profile(current_phase)
        
        # ¿Es trading óptimo?
        optimal_trading = current_phase == SessionPhase.LONDON_NY_OVERLAP
        
        # Razón actual
        reason = self._get_session_reason(current_phase, is_active)
        
        # Actualizar métricas
        self.session_metrics = SessionMetrics(
            current_phase=current_phase,
            time_remaining=time_remaining,
            liquidity_score=liquidity_score,
            volatility_profile=volatility_profile,
            optimal_trading=optimal_trading,
            reason=reason
        )
        
        return self.session_metrics

    def _calculate_time_remaining(self, current_time: datetime, phase: SessionPhase) -> timedelta:
        """Calcula tiempo restante en sesión actual"""
        gmt_time = current_time.astimezone(self.gmt)
        gmt_hour = gmt_time.hour + gmt_time.minute / 60.0
        
        if phase == SessionPhase.LONDON_NY_OVERLAP:
            end_hour = self.session_config['london_ny_overlap']['end_gmt']
            end_time = gmt_time.replace(hour=int(end_hour), minute=0, second=0, microsecond=0)
            if gmt_hour >= end_hour:
                end_time += timedelta(days=1)
                
        elif phase == SessionPhase.NY_CORE:
            et_time = current_time.astimezone(self.ny_tz)
            et_hour = et_time.hour + et_time.minute / 60.0
            end_hour = self.session_config['ny_core_session']['end_et']
            end_time = et_time.replace(hour=int(end_hour), minute=30, second=0, microsecond=0)
            if et_hour >= end_hour:
                end_time += timedelta(days=1)
            end_time = end_time.astimezone(self.gmt)
            
        elif phase == SessionPhase.PREMARKET:
            end_hour = self.session_config['premarket']['end_gmt']
            end_time = gmt_time.replace(hour=int(end_hour), minute=0, second=0, microsecond=0)
            if gmt_hour >= end_hour:
                end_time += timedelta(days=1)
                
        else:
            return timedelta(0)
            
        return end_time - gmt_time

    def _calculate_liquidity_score(self, phase: SessionPhase) -> float:
        """Calcula score de liquidez basado en fase de sesión"""
        scores = {
            SessionPhase.LONDON_NY_OVERLAP: 0.9,
            SessionPhase.NY_CORE: 0.7,
            SessionPhase.PREMARKET: 0.5,
            SessionPhase.POST_SESSION: 0.3,
            SessionPhase.CLOSED: 0.1
        }
        return scores.get(phase, 0.1)

    def _get_volatility_profile(self, phase: SessionPhase) -> str:
        """Determina perfil de volatilidad esperado"""
        profiles = {
            SessionPhase.LONDON_NY_OVERLAP: "high_optimal",
            SessionPhase.NY_CORE: "high_volatile", 
            SessionPhase.PREMARKET: "medium_rising",
            SessionPhase.POST_SESSION: "low_declining",
            SessionPhase.CLOSED: "low_stable"
        }
        return profiles.get(phase, "unknown")

    def _get_session_reason(self, phase: SessionPhase, is_active: bool) -> str:
        """Genera razón descriptiva del estado de sesión"""
        if not is_active:
            return "Market closed - outside trading hours"
            
        reasons = {
            SessionPhase.LONDON_NY_OVERLAP: "Optimal trading - London-NY overlap active",
            SessionPhase.NY_CORE: "Good conditions - NY core session", 
            SessionPhase.PREMARKET: "Caution advised - premarket session",
            SessionPhase.POST_SESSION: "Reduced liquidity - post session"
        }
        return reasons.get(phase, "Active trading session")

    def get_optimal_entry_window(self) -> Dict[str, Any]:
        """
        Calcula ventana óptima de entrada basada en sesión actual
        """
        current_time = datetime.now(pytz.utc)
        metrics = self.get_session_metrics(current_time)
        
        # Ventana óptima depende de la fase actual
        if metrics.current_phase == SessionPhase.LONDON_NY_OVERLAP:
            window_size = timedelta(minutes=15)  # Ventana corta para scalping
            confidence = "VERY_HIGH"
        elif metrics.current_phase == SessionPhase.NY_CORE:
            window_size = timedelta(minutes=10)
            confidence = "HIGH"
        elif metrics.current_phase == SessionPhase.PREMARKET:
            window_size = timedelta(minutes=5)
            confidence = "MEDIUM"
        else:
            window_size = timedelta(0)
            confidence = "LOW"
            
        return {
            'is_optimal': metrics.optimal_trading,
            'window_start': current_time,
            'window_end': current_time + window_size,
            'confidence': confidence,
            'recommended_action': 'ENTER' if metrics.optimal_trading else 'WAIT',
            'liquidity_score': metrics.liquidity_score,
            'volatility_profile': metrics.volatility_profile,
            'time_remaining': metrics.time_remaining
        }

    async def wait_for_session(self, target_phase: SessionPhase = SessionPhase.LONDON_NY_OVERLAP) -> bool:
        """
        Espera de forma asíncrona hasta que la sesión target esté activa
        Útil para sistemas que necesitan esperar condiciones óptimas
        """
        logger.info(f"⏳ Esperando sesión: {target_phase.value}")
        
        max_wait_minutes = 120  # Máximo 2 horas de espera
        check_interval = 30     # Verificar cada 30 segundos
        
        start_time = datetime.now(pytz.utc)
        
        while (datetime.now(pytz.utc) - start_time).total_seconds() < max_wait_minutes * 60:
            current_metrics = self.get_session_metrics()
            
            if current_metrics.current_phase == target_phase:
                logger.info(f"✅ Sesión target alcanzada: {target_phase.value}")
                return True
                
            # Verificar si hay sesión activa (aunque no sea la target)
            is_allowed, reason = await self.is_trading_allowed()
            if is_allowed and current_metrics.current_phase != SessionPhase.CLOSED:
                logger.info(f"🎯 Sesión alternativa disponible: {current_metrics.current_phase.value}")
                return True
                
            await asyncio.sleep(check_interval)
            
        logger.warning("⏰ Timeout esperando sesión target")
        return False

    def get_detailed_status(self) -> Dict[str, Any]:
        """Estado detallado del session manager para monitoreo"""
        current_time = datetime.now(pytz.utc)
        metrics = self.get_session_metrics(current_time)
        is_allowed, reason = asyncio.run(self.is_trading_allowed(current_time))
        optimal_window = self.get_optimal_entry_window()
        
        return {
            'timestamp': current_time.isoformat(),
            'gmt_time': current_time.astimezone(self.gmt).strftime('%H:%M'),
            'ny_time': current_time.astimezone(self.ny_tz).strftime('%H:%M'),
            'london_time': current_time.astimezone(self.london_tz).strftime('%H:%M'),
            'trading_allowed': is_allowed,
            'trading_reason': reason,
            'session_phase': metrics.current_phase.value,
            'liquidity_score': metrics.liquidity_score,
            'volatility_profile': metrics.volatility_profile,
            'time_remaining': str(metrics.time_remaining),
            'optimal_window': optimal_window,
            'holidays_loaded': len(self.holidays),
            'cache_size': len(self._session_cache),
            'news_filter_connected': self.news_filter is not None,
            'last_holiday_update': self.last_holiday_update.isoformat() if self.last_holiday_update else None
        }

    def cleanup_cache(self):
        """Limpia cache expirado"""
        current_time = datetime.now(pytz.utc)
        expired_keys = []
        
        for key, (cached_time, _) in self._session_cache.items():
            if (current_time - cached_time).total_seconds() > self._cache_ttl * 2:  # Doble TTL
                expired_keys.append(key)
                
        for key in expired_keys:
            del self._session_cache[key]
            
        if expired_keys:
            logger.debug(f"🧹 Cache limpiado: {len(expired_keys)} entradas expiradas")

    async def refresh_data(self):
        """Actualiza datos del session manager (feriados, etc.)"""
        try:
            await self._load_holidays_async()
            self.cleanup_cache()
            logger.debug("🔄 SessionManager datos actualizados")
        except Exception as e:
            logger.error(f"❌ Error actualizando SessionManager: {e}")

    async def close(self):
        """Cierre seguro del session manager"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("🔌 SessionManager cerrado")

    def __del__(self):
        """Destructor para limpieza automática"""
        if self.session:
            asyncio.create_task(self.close())