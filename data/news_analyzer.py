#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced News Filter - IA Authority with Consistent Blocking Rules
Solves: 15min vs 60min inconsistency by making IA filter the final authority
CORREGIDO Y FUNCIONAL
"""

import asyncio
import aiohttp
import json
import logging
import re
import time 
from datetime import datetime, timedelta, time as dttime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import threading

# ===== IMPLEMENTACIÓN MÍNIMA DE LOGGER ESTRUCTURADO =====
try:
    from infrastructure.structured_logger import get_eas_logger
    logger = get_eas_logger("EAS.NewsAnalyzer")
except ImportError:
    # Fallback a logger estándar
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("EAS.NewsAnalyzer")

# ===== IMPLEMENTACIONES OPCIONALES =====
try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False
    logger.warning("⚠️ pytz no disponible - usando UTC simple")

try:
    from prometheus_client import Counter, Gauge, Histogram
    PROMETHEUS_AVAILABLE = True
    
    NEWS_EVENTS_COUNTER = Counter('news_events_total', 'Total news events processed', ['impact', 'source'])
    BLOCKING_DECISIONS = Counter('news_blocking_decisions', 'Trading blocking decisions', ['decision', 'impact_level'])
    CACHE_HITS = Counter('news_cache_hits', 'News cache hits')
    CACHE_MISSES = Counter('news_cache_misses', 'News cache misses')
    IA_ANALYSIS_TIME = Histogram('ia_analysis_seconds', 'IA analysis time per event')
    SOURCE_FETCH_TIME = Histogram('source_fetch_seconds', 'Time to fetch from each source', ['source'])
    EVENT_PROCESSING_TIME = Histogram('event_processing_seconds', 'Event processing time')
    
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("⚠️ Prometheus client no disponible - métricas desactivadas")

class NewsImpact(Enum):
    LOW = 1
    MEDIUM = 2 
    HIGH = 3
    CRITICAL = 4

@dataclass
class NewsEvent:
    id: str
    title: str
    currency: str
    impact: NewsImpact
    time: datetime
    forecast: Optional[str]
    previous: Optional[str]
    actual: Optional[str]
    source: str
    category: str
    ai_impact_score: Optional[float] = None
    ai_sentiment: Optional[str] = None
    block_minutes: int = 0
    is_gold_critical: bool = False
    last_updated: datetime = None 
    
    def __post_init__(self):
        if self.last_updated is None:
            if PYTZ_AVAILABLE:
                self.last_updated = datetime.utcnow().replace(tzinfo=pytz.UTC)
            else:
                self.last_updated = datetime.utcnow()

class AdvancedNewsFilter:
    def __init__(self, config: Dict[str, Any], tot_engine=None):
        self.config = config
        self.news_config = config.get('economiccalendar', {})
        
        # CONFIGURACIÓN UNIFICADA MEJORADA
        self.ia_blocking_rules = {
            NewsImpact.CRITICAL: 60,  # 60 minutos para eventos críticos
            NewsImpact.HIGH: 45,      # 45 minutos para alto impacto  
            NewsImpact.MEDIUM: 30,    # 30 minutos para impacto medio
            NewsImpact.LOW: 15        # 15 minutos para bajo impacto
        }
        
        # Fallback mejorado con márgenes de seguridad
        self.fallback_blocking_rules = {
            NewsImpact.CRITICAL: 75,   # Más conservador en fallback
            NewsImpact.HIGH: 60,
            NewsImpact.MEDIUM: 30, 
            NewsImpact.LOW: 15
        }
        
        self.lookahead_hours = self.news_config.get('lookahead_hours', 24)
        self.tot_engine = tot_engine
        
        # Fuentes de datos mejoradas con timeouts específicos
        self.news_sources = [
            {
                "name": "ForexFactory", 
                "url": "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
                "type": "json", 
                "priority": 1,
                "timeout": 8,
                "retries": 2
            },
            {
                "name": "AlphaVantage", 
                "url": "https://www.alphavantage.co/query",
                "type": "api", 
                "priority": 2,
                "timeout": 10,
                "retries": 1
            },
            {
                "name": "FXStreet", 
                "url": "https://api.fxstreet.com/v1/economic-calendar/events",
                "type": "api", 
                "priority": 3,
                "timeout": 8,
                "retries": 2
            }
        ]
        
        # Configuración mejorada de WebSocket
        self.ws_task = None
        self.session = None
        self.session_timeout = aiohttp.ClientTimeout(total=15)
        self.cached_events: List[NewsEvent] = []
        self.cache_file = Path("cache/news/news_cache.json")
        self.cache_file.parent.mkdir(parents=True, exist_ok=True) 
        self.cache_ttl = 300  # Reducido a 5 minutos para mayor frescura
        
        # Eventos críticos expandidos
        self.critical_gold_events = {
            "FED", "FOMC", "FEDERAL RESERVE", "INTEREST RATE", "RATE DECISION",
            "NFP", "NONFARM PAYROLLS", "EMPLOYMENT SITUATION", "JOBS REPORT",
            "CPI", "CONSUMER PRICE INDEX", "INFLATION", "CORE CPI",
            "PCE", "PERSONAL CONSUMPTION EXPENDITURES", "CORE PCE",
            "RETAIL SALES", "UNEMPLOYMENT RATE", "AVERAGE EARNINGS",
            "GDP", "GROSS DOMESTIC PRODUCT", "ECB", "EUROPEAN CENTRAL BANK",
            "BOE", "BANK OF ENGLAND", "BOJ", "BANK OF JAPAN",
            "PMI", "PURCHASING MANAGERS INDEX", "ISM", "MANUFACTURING PMI"
        }
        
        # Palabras clave mejoradas para relevancia de oro
        self.gold_keywords = [
            "gold", "xau", "inflation", "fed", "nfp", "usd", "dollar",
            "precious metals", "federal reserve", "interest rate", 
            "monetary policy", "cpi", "pce", "fomc", "dxy", "vix",
            "yield", "treasury", "rate decision", "quantitative tightening",
            "balance sheet", "hawkish", "dovish", "real yields", "bullion"
        ]
        
        self.last_cache_update = None
        self.ia_analysis_enabled = tot_engine is not None
        self.initialized = False
        self._lock = threading.RLock()
        
        logger.info("✅ AdvancedNewsFilter initialized - IA Authority for blocking rules")
        logger.info(f"🔒 Blocking rules: CRITICAL=60min, HIGH=45min, MEDIUM=30min, LOW=15min")
        logger.info(f"🤖 IA Analysis: {'ENABLED' if self.ia_analysis_enabled else 'DISABLED'}")

    async def initialize(self):
        """Inicializa conexiones y carga cache - Versión mejorada"""
        if self.initialized:
            return
        try:
            connector = aiohttp.TCPConnector(limit=15, force_close=True, enable_cleanup_closed=True)
            self.session = aiohttp.ClientSession(connector=connector, timeout=self.session_timeout)
            await self._load_cache()
            
            # Solo iniciar WebSocket si tenemos engine IA para procesamiento en tiempo real
            if self.ia_analysis_enabled:
                self.ws_task = asyncio.create_task(self._ws_listener())
                
            self.initialized = True
            logger.info("✅ News filter fully initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize news filter: {e}")
            raise

    async def _ws_listener(self):
        """WebSocket listener mejorado con reconexión exponencial"""
        uri = "wss://nfs.faireconomy.media/ff_calendar"
        reconnect_delay = 5
        max_reconnect_delay = 300 
        while True:
            try:
                import websockets
                async with websockets.connect(uri, ping_interval=30, ping_timeout=10) as ws:
                    logger.info("🔗 Connected to ForexFactory WebSocket")
                    reconnect_delay = 5 
                    
                    while True:
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=60)
                            event_data = json.loads(msg)
                            await self._process_realtime_event(event_data)
                        except asyncio.TimeoutError:
                            # Ping para mantener conexión activa
                            await ws.ping()
                            continue
                            
            except Exception as e:
                logger.error(f"WebSocket error: {e}, reconnecting in {reconnect_delay}s")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

    async def _process_realtime_event(self, event_data: Dict[str, Any]):
        """Procesa evento en tiempo real con análisis IA - Versión mejorada"""
        start_time = time.time()
        
        try:
            event = self._parse_forexfactory_event(event_data)
            if event and self._is_potentially_relevant(event):
                # Análisis IA en tiempo real para determinar bloqueo exacto
                await self._analyze_event_with_ia(event)
                self._update_event_cache(event)
                await self._save_cache()
                if PROMETHEUS_AVAILABLE:
                    analysis_time = time.time() - start_time
                    IA_ANALYSIS_TIME.observe(analysis_time)
                logger.info(f"🔄 Realtime event analyzed: {event.title} -> {event.block_minutes}min block")
        except Exception as e:
            logger.error(f"❌ Error processing realtime event: {e}")

    async def get_news_events(self, hours_ahead: int = None) -> List[NewsEvent]:
        """Obtiene eventos de noticias con análisis IA - Versión mejorada"""
        if hours_ahead is None:
            hours_ahead = self.lookahead_hours
        if PYTZ_AVAILABLE:
            now = datetime.utcnow().replace(tzinfo=pytz.UTC)
        else:
            now = datetime.utcnow()
        
        # Usar cache si es válido
        if self._is_cache_valid():
            if PROMETHEUS_AVAILABLE:
                CACHE_HITS.inc()
            return self._get_upcoming_events(now, hours_ahead)
        
        if PROMETHEUS_AVAILABLE:
            CACHE_MISSES.inc()
        # Obtener eventos de todas las fuentes
        all_events = await self._fetch_all_news_sources()
        unique_events = self._deduplicate_events(all_events)
        
        # Análisis IA para determinar tiempos de bloqueo
        if self.ia_analysis_enabled:
            await self._analyze_events_with_ia(unique_events)
        else:
            self._apply_fallback_blocking_rules(unique_events)
            
        # Actualizar cache
        with self._lock:
            self.cached_events = unique_events
            self.last_cache_update = datetime.utcnow()
        await self._save_cache()
        
        if PROMETHEUS_AVAILABLE:
            NEWS_EVENTS_COUNTER.labels(impact='total', source='multiple').inc()
        logger.info(f"📰 Loaded {len(unique_events)} news events with IA analysis")
        
        return self._get_upcoming_events(now, hours_ahead)

    def should_block_trading(self, current_time: Optional[datetime] = None) -> Tuple[bool, str]:
        """DECISIÓN FINAL DE BLOQUEO MEJORADA - IA ES AUTORIDAD
        Resuelve inconsistencia 15min vs 60min con márgenes de seguridad"""
        if current_time is None:
            if PYTZ_AVAILABLE:
                current_time = datetime.utcnow().replace(tzinfo=pytz.UTC)
            else:
                current_time = datetime.utcnow()
                
        with self._lock:
            if not self.cached_events:
                if PROMETHEUS_AVAILABLE:
                    BLOCKING_DECISIONS.labels(decision='no_events', impact_level='none').inc()
                return False, "No news events to analyze"
            
            # Ordenar eventos por proximidad
            sorted_events = sorted(self.cached_events, key=lambda x: abs((x.time - current_time).total_seconds()))
            
            for event in sorted_events:
                time_diff = (event.time - current_time).total_seconds() / 60
                
                # Solo considerar eventos futuros o muy recientes (hasta 5 minutos en el pasado)
                if time_diff < -5:
                    continue
                
                # IA DETERMINA EL TIEMPO DE BLOQUEO - AUTORIDAD FINAL
                block_minutes = event.block_minutes
                
                # Aplicar margen de seguridad adicional para eventos críticos
                effective_block_minutes = block_minutes
                if event.impact == NewsImpact.CRITICAL:
                    effective_block_minutes += 5  # 5 minutos extra de seguridad
                    
                if abs(time_diff) <= effective_block_minutes:
                    if PROMETHEUS_AVAILABLE:
                        BLOCKING_DECISIONS.labels(
                            decision='blocked', 
                            impact_level=event.impact.name.lower()
                        ).inc()
                    time_relation = "before" if time_diff > 0 else "after"
                    return True, (
                        f"🚫 BLOCKED: {event.title} "
                        f"(Impact: {event.impact.name}, "
                        f"IA Score: {event.ai_impact_score or 'N/A'}, "
                        f"Block: {effective_block_minutes}min, "
                        f"{abs(time_diff):.1f}min {time_relation} event)"
                    )
        
        if PROMETHEUS_AVAILABLE:
            BLOCKING_DECISIONS.labels(decision='allowed', impact_level='none').inc()
        return False, "No blocking news events"

    async def _fetch_all_news_sources(self) -> List[NewsEvent]:
        """Obtiene eventos de todas las fuentes configuradas - Versión paralelizada"""
        all_events = []
        fetch_tasks = []
        
        for source in self.news_sources:
            task = self._fetch_single_source(source)
            fetch_tasks.append(task)
        
        # Ejecutar todas las fuentes en paralelo
        results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            source_name = self.news_sources[i]["name"]
            if isinstance(result, Exception):
                logger.error(f"❌ Error fetching from {source_name}: {result}")
            elif result:
                all_events.extend(result)
                logger.debug(f"✅ Fetched {len(result)} events from {source_name}")
                
        return all_events

    async def _fetch_single_source(self, source: Dict[str, Any]) -> List[NewsEvent]:
        """Obtiene eventos de una sola fuente con reintentos"""
        start_time = time.time()
        for attempt in range(source.get("retries", 1) + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=source.get("timeout", 10))
                if source["type"] == "json":
                    async with self.session.get(source["url"], timeout=timeout) as response:
                        if response.status == 200:
                            data = await response.json()
                            events = []
                            # ForexFactory JSON es un array, no un diccionario con 'events' key
                            for event_data in data if isinstance(data, list) else data.get("events", []): 
                                event = self._parse_forexfactory_event(event_data)
                                if event:
                                    events.append(event)    
                            if PROMETHEUS_AVAILABLE:
                                fetch_time = time.time() - start_time
                                SOURCE_FETCH_TIME.labels(source=source["name"]).observe(fetch_time)
                            return events
                        else:
                            logger.warning(f"⚠️ HTTP {response.status} from {source['name']}, attempt {attempt + 1}")
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Timeout fetching from {source['name']}, attempt {attempt + 1}")
            except Exception as e:
                logger.warning(f"⚠️ Error fetching from {source['name']}, attempt {attempt + 1}: {e}")
                
            if attempt < source.get("retries", 1):
                await asyncio.sleep(2 ** attempt)  # Backoff exponencial
        
        logger.error(f"❌ Failed to fetch from {source['name']} after all retries")
        return []

    def _parse_forexfactory_event(self, event_data: Dict[str, Any]) -> Optional[NewsEvent]:
        """Parsea evento de ForexFactory a NewsEvent - Versión mejorada"""
        try:
            start_time = time.time()
            
            # Parsear timestamp
            time_str = event_data.get("date", "")
            if not time_str:
                return None
            
            # Formato: "2025-01-18T15:30:00+00:00" o "2025-01-18T15:30:00Z"
            try:
                if PYTZ_AVAILABLE:
                    event_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                else:
                    # Manejar sin pytz
                    clean_time = time_str.replace('Z', '+00:00')
                    if '+' in clean_time:
                        clean_time = clean_time.split('+')[0]
                    event_time = datetime.fromisoformat(clean_time)
            except ValueError:
                # Intentar otros formatos
                for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"]:
                    try:
                        event_time = datetime.strptime(time_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return None
            
            # Mapear impacto
            impact_str = event_data.get("impact", "").lower()
            impact_map = {
                "high": NewsImpact.HIGH,
                "medium": NewsImpact.MEDIUM, 
                "low": NewsImpact.LOW
            }
            impact = impact_map.get(impact_str, NewsImpact.LOW)
            
            # Determinar si es crítico para oro
            title = event_data.get("title", "").upper()
            is_critical = any(critical in title for critical in self.critical_gold_events)
            
            event = NewsEvent(
                id=f"ff_{event_data.get('id', hash(title))}",
                title=event_data.get("title", "").strip(),
                currency=event_data.get("country", "USD").upper(),
                impact=NewsImpact.CRITICAL if is_critical else impact,
                time=event_time,
                forecast=event_data.get("forecast"),
                previous=event_data.get("previous"),
                actual=event_data.get("actual"),
                source="ForexFactory",
                category=event_data.get("category", "general"),
                is_gold_critical=is_critical
            )
            if PROMETHEUS_AVAILABLE:
                NEWS_EVENTS_COUNTER.labels(
                    impact=event.impact.name, 
                    source="ForexFactory"
                ).inc()
            return event
            
        except Exception as e:
            logger.error(f"❌ Error parsing event {event_data.get('title', 'unknown')}: {e}")
            return None

    async def _analyze_events_with_ia(self, events: List[NewsEvent]):
        """Análisis IA para determinar tiempos de bloqueo precisos - Versión mejorada"""
        logger.info(f"🤖 Analyzing {len(events)} events with IA")
        # Limitar análisis a eventos relevantes para mejorar rendimiento
        relevant_events = [event for event in events if self._is_potentially_relevant(event)]
        non_relevant_events = [event for event in events if not self._is_potentially_relevant(event)]
        
        # Aplicar fallback a eventos no relevantes
        for event in non_relevant_events:
            self._apply_fallback_to_event(event)
            
        # Procesar eventos relevantes en lotes para no sobrecargar el sistema
        batch_size = 5
        for i in range(0, len(relevant_events), batch_size):
            batch = relevant_events[i:i + batch_size]
            analysis_tasks = [self._analyze_event_with_ia(event) for event in batch]
            await asyncio.gather(*analysis_tasks, return_exceptions=True)
            await asyncio.sleep(0.1)  # Pequeña pausa entre lotes
            
        logger.info(f"✅ IA analysis completed: {len(relevant_events)} relevant events processed")

    async def _analyze_event_with_ia(self, event: NewsEvent):
        """Análisis IA individual para evento - Versión mejorada"""
        try:
            if self.tot_engine:
                # Análisis real con ToT engine
                start_time = time.time()
                ia_result = await self.tot_engine.analyze_news_impact(event)
                
                # Aplicar resultados de IA
                event.ai_impact_score = ia_result.get('impact_score')
                event.ai_sentiment = ia_result.get('sentiment')
                event.block_minutes = self._calculate_block_minutes_from_ia(ia_result, event)
                if PYTZ_AVAILABLE:
                    event.last_updated = datetime.utcnow().replace(tzinfo=pytz.UTC)
                else:
                    event.last_updated = datetime.utcnow()
                
                if PROMETHEUS_AVAILABLE:
                    analysis_time = time.time() - start_time
                    IA_ANALYSIS_TIME.observe(analysis_time)
                
                logger.debug(f"🔍 IA Analysis: {event.title} -> Score: {event.ai_impact_score}, Block: {event.block_minutes}min")
            else:
                # Simulación mejorada de análisis IA
                self._simulate_ia_analysis(event)
                
        except Exception as e:
            logger.error(f"❌ IA analysis failed for {event.title}: {e}")
            self._apply_fallback_to_event(event)

    def _calculate_block_minutes_from_ia(self, ia_result: Dict[str, Any], event: NewsEvent) -> int:
        """Calcula minutos de bloqueo basado en análisis IA - Versión mejorada"""
        impact_score = ia_result.get('impact_score', 0.5)
        sentiment = ia_result.get('sentiment', 'neutral')
        volatility_estimate = ia_result.get('volatility', 0.5)
        
        # LÓGICA DE IA MEJORADA COMO AUTORIDAD FINAL
        base_block = 0
        if impact_score >= 0.9 or event.impact == NewsImpact.CRITICAL:
            base_block = self.ia_blocking_rules[NewsImpact.CRITICAL]
        elif impact_score >= 0.7:
            base_block = self.ia_blocking_rules[NewsImpact.HIGH]
        elif impact_score >= 0.5:
            base_block = self.ia_blocking_rules[NewsImpact.MEDIUM]
        elif impact_score >= 0.3:
            base_block = self.ia_blocking_rules[NewsImpact.LOW]
            
        # Ajustar por volatilidad estimada
        volatility_multiplier = 1.0 + (volatility_estimate * 0.3)  # Hasta 30% más
        adjusted_block = int(base_block * volatility_multiplier)
        
        # Límites máximos y mínimos
        max_block = 90  # Máximo absoluto
        min_block = 0
        return max(min_block, min(adjusted_block, max_block))

    def _simulate_ia_analysis(self, event: NewsEvent):
        """Simulación mejorada de análisis IA"""
        # Base del impacto original con variación aleatoria
        import random
        base_scores = {
            NewsImpact.CRITICAL: 0.85 + random.uniform(0.0, 0.15),
            NewsImpact.HIGH: 0.65 + random.uniform(0.0, 0.20),
            NewsImpact.MEDIUM: 0.45 + random.uniform(0.0, 0.20),
            NewsImpact.LOW: 0.25 + random.uniform(0.0, 0.20)
        }
        
        event.ai_impact_score = base_scores.get(event.impact, 0.3)
        
        # Ajustar por relevancia de oro
        if event.is_gold_critical:
            event.ai_impact_score = min(1.0, event.ai_impact_score + 0.15)
            
        # Análisis de sentimiento mejorado
        title_lower = event.title.lower()
        bullish_words = ["increase", "rise", "growth", "positive", "strong", "up", "better", "bullish", "hawkish"]
        bearish_words = ["decrease", "fall", "decline", "negative", "weak", "down", "worse", "bearish", "dovish"]
        
        bullish_count = sum(1 for word in bullish_words if word in title_lower)
        bearish_count = sum(1 for word in bearish_words if word in title_lower)
        
        if bullish_count > bearish_count + 1:
            event.ai_sentiment = "bullish"
        elif bearish_count > bullish_count + 1:
            event.ai_sentiment = "bearish"
        else:
            event.ai_sentiment = "neutral"
            
        # Calcular bloqueo basado en score IA simulado
        event.block_minutes = self._calculate_block_minutes_from_ia({
            'impact_score': event.ai_impact_score,
            'sentiment': event.ai_sentiment,
            'volatility': min(event.ai_impact_score + 0.2, 0.9)  # Estimación de volatilidad
        }, event)
        if PYTZ_AVAILABLE:
            event.last_updated = datetime.utcnow().replace(tzinfo=pytz.UTC)
        else:
            event.last_updated = datetime.utcnow()

    def _apply_fallback_blocking_rules(self, events: List[NewsEvent]):
        """Aplica reglas de fallback cuando IA no está disponible"""
        for event in events:
            self._apply_fallback_to_event(event)

    def _apply_fallback_to_event(self, event: NewsEvent):
        """Aplica reglas de fallback a evento individual - Versión mejorada"""
        # Usar reglas de fallback más conservadoras
        event.block_minutes = self.fallback_blocking_rules.get(event.impact, 0)
        # Para eventos críticos, asegurar bloqueo mínimo
        if event.impact == NewsImpact.CRITICAL and event.block_minutes < 60:
            event.block_minutes = 60
        if PYTZ_AVAILABLE:
            event.last_updated = datetime.utcnow().replace(tzinfo=pytz.UTC)
        else:
            event.last_updated = datetime.utcnow()
        logger.warning(f"⚠️ Using fallback blocking: {event.title} -> {event.block_minutes}min")

    def _is_potentially_relevant(self, event: NewsEvent) -> bool:
        """Determina si un evento es potencialmente relevante para análisis IA - Versión mejorada"""
        # Eventos críticos siempre son relevantes
        if event.impact == NewsImpact.CRITICAL:
            return True
        
        # Eventos de alta/medio impacto en monedas principales
        major_currencies = {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"}
        if event.impact in [NewsImpact.HIGH, NewsImpact.MEDIUM] and event.currency in major_currencies:
            return True
            
        # Eventos con palabras clave de oro
        title_lower = event.title.lower()
        if any(keyword in title_lower for keyword in self.gold_keywords):
            return True
            
        # Eventos que afectan mercados globales
        global_market_keywords = [
            "crisis", "recession", "stimulus", "qe", "quantitative easing",
            "trade war", "tariff", "sanction", "election", "brexit"
        ]
        if any(keyword in title_lower for keyword in global_market_keywords):
            return True
            
        return False

    def _get_upcoming_events(self, current_time: datetime, hours_ahead: int) -> List[NewsEvent]:
        """Filtra eventos futuros - Versión mejorada"""
        cutoff_time = current_time + timedelta(hours=hours_ahead)
        recent_cutoff = current_time - timedelta(minutes=30)  # Incluir eventos recientes
        return [
            event for event in self.cached_events
            if recent_cutoff <= event.time <= cutoff_time
        ]

    def _deduplicate_events(self, events: List[NewsEvent]) -> List[NewsEvent]:
        """Elimina eventos duplicados - Versión mejorada"""
        seen = set()
        unique_events = []
        for event in sorted(events, key=lambda x: x.time, reverse=True):  # Los más recientes primero
            # Crear clave más robusta para deduplicación
            title_normalized = re.sub(r'[^a-zA-Z0-9]', '', event.title.lower())
            time_key = event.time.strftime("%Y%m%d%H%M")  # Precisión de minutos
            key = (title_normalized[:50], time_key, event.currency)
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
        return sorted(unique_events, key=lambda x: x.time)

    def _update_event_cache(self, new_event: NewsEvent):
        """Actualiza cache con nuevo evento - Versión mejorada"""
        with self._lock:
            # Buscar evento existente
            for i, existing_event in enumerate(self.cached_events):
                if (existing_event.id == new_event.id or 
                    (abs((existing_event.time - new_event.time).total_seconds()) < 3600 and
                     existing_event.title.lower() == new_event.title.lower())):
                    
                    # Actualizar solo si el nuevo evento es más reciente o tiene más información
                    if (new_event.last_updated > existing_event.last_updated or
                        new_event.actual is not None and existing_event.actual is None):
                        self.cached_events[i] = new_event
                    return
                
            # Si no existe, agregar nuevo evento
            self.cached_events.append(new_event)

    def _is_cache_valid(self) -> bool:
        """Verifica si el cache es válido - Versión mejorada"""
        if not self.last_cache_update or not self.cached_events:
            return False
            
        cache_age = (datetime.utcnow() - self.last_cache_update).total_seconds()
        
        # Cache más fresco para mercado activo
        market_hours = self._is_market_active()
        max_age = self.cache_ttl / 2 if market_hours else self.cache_ttl
        
        return cache_age < max_age

    def _is_market_active(self) -> bool:
        """Determina si el mercado está en horas activas"""
        now = datetime.utcnow()
        weekday = now.weekday()
        hour = now.hour
        # Lunes a Viernes, horario de mercados principales
        if weekday < 5:  # Lunes a Viernes
            # Horario de superposición Londres/NY (13:00-17:00 UTC)
            if 13 <= hour < 17:
                return True
            # Horario Asia (22:00-06:00 UTC del día siguiente)
            if hour >= 22 or hour < 6:
                return True
        return False

    async def _load_cache(self):
        """Carga cache desde archivo - Versión mejorada"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                self.cached_events = []
                cache_version = data.get('version', 1)
                
                for event_data in data.get('events', []):
                    try:
                        # Convertir string de tiempo a datetime
                        event_data['time'] = datetime.fromisoformat(event_data['time'])
                        # Manejar last_updated
                        if 'last_updated' in event_data and event_data['last_updated'] is not None:
                            event_data['last_updated'] = datetime.fromisoformat(event_data['last_updated'])
                        # Convertir string de impacto a Enum
                        event_data['impact'] = NewsImpact[event_data['impact']]
                        # Validar integridad del evento
                        if event_data.get('title') and event_data.get('currency'):
                            self.cached_events.append(NewsEvent(**event_data))
                    except (KeyError, ValueError) as e:
                        logger.warning(f"⚠️ Skipping invalid cache event: {e}")
                        continue
                        
                if 'last_update' in data and data['last_update']:
                    self.last_cache_update = datetime.fromisoformat(data['last_update'])
                else:
                    self.last_cache_update = datetime.utcnow()
                logger.info(f"📁 Loaded {len(self.cached_events)} events from cache (v{cache_version})")
                
        except Exception as e:
            logger.error(f"❌ Cache load error: {e}")
            self.cached_events = []

    async def _save_cache(self):
        """Guarda cache a archivo - Versión mejorada con guardado atómico"""
        try:
            data = {
                'version': 2,
                'events': [
                    {
                        **asdict(event),
                        'time': event.time.isoformat(),
                        'impact': event.impact.name,
                        # Asegurar que los campos Optional son None o el valor
                        'forecast': event.forecast if event.forecast is not None else None,
                        'previous': event.previous if event.previous is not None else None,
                        'actual': event.actual if event.actual is not None else None,
                        'last_updated': event.last_updated.isoformat() if event.last_updated else None
                    }
                    for event in self.cached_events
                ],
                'last_update': self.last_cache_update.isoformat() if self.last_cache_update else datetime.utcnow().isoformat()
            }
            
            # Guardar de forma atómica
            temp_file = self.cache_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            # Reemplazar archivo existente
            temp_file.replace(self.cache_file)
                
        except Exception as e:
            logger.error(f"❌ Cache save error: {e}")

    def get_blocking_statistics(self) -> Dict[str, Any]:
        """Estadísticas de bloqueo mejoradas para monitoreo"""
        if PYTZ_AVAILABLE:
            now = datetime.utcnow().replace(tzinfo=pytz.UTC)
        else:
            now = datetime.utcnow()
        blocking_events = []
        upcoming_events = []
        
        for event in self.cached_events:
            time_diff = (event.time - now).total_seconds() / 60
            
            # Aplicar margen de seguridad para estadísticas (similar a should_block_trading)
            effective_block_minutes = event.block_minutes
            if event.impact == NewsImpact.CRITICAL:
                effective_block_minutes += 5 # 5 minutos extra de seguridad
            
            # Bloqueo: si la diferencia absoluta está dentro del tiempo de bloqueo
            if abs(time_diff) <= effective_block_minutes:
                blocking_events.append({
                    'title': event.title,
                    'time_to_event': time_diff, # Negativo = evento pasó, Positivo = evento futuro
                    'block_minutes': effective_block_minutes, # Reportar bloqueo efectivo
                    'ia_score': event.ai_impact_score,
                    'impact': event.impact.name,
                    'currency': event.currency
                })
            
            # Eventos próximos (próximas 4 horas o 240 minutos)
            if 0 <= time_diff <= 240:
                upcoming_events.append({
                    'title': event.title,
                    'time_to_event': time_diff,
                    'impact': event.impact.name,
                    'currency': event.currency
                })
                
        return {
            'total_events': len(self.cached_events),
            'blocking_events': blocking_events,
            'upcoming_events': sorted(upcoming_events, key=lambda x: x['time_to_event'])[:10],  # Top 10 próximos
            'ia_analysis_enabled': self.ia_analysis_enabled,
            'cache_age_minutes': (
                (datetime.utcnow() - self.last_cache_update).total_seconds() / 60 
                if self.last_cache_update else None
            ),
            'initialized': self.initialized,
            'cache_valid': self._is_cache_valid()
        }

    async def cleanup_old_events(self):
        """Limpia eventos antiguos del cache (eventos pasados hace más de 24 horas)"""
        if PYTZ_AVAILABLE:
            cutoff_time = datetime.utcnow().replace(tzinfo=pytz.UTC) - timedelta(hours=24)
        else:
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
        initial_count = len(self.cached_events)
        
        self.cached_events = [
            event for event in self.cached_events 
            if event.time >= cutoff_time
        ]
        
        removed_count = initial_count - len(self.cached_events)
        if removed_count > 0:
            logger.info(f"🧹 Cleaned up {removed_count} old events")
            await self._save_cache()

    async def close(self):
        """Cierra conexiones - Versión mejorada"""
        self.initialized = False
        
        # 1. Cancelar tarea WebSocket
        if self.ws_task:
            self.ws_task.cancel()
            try:
                await self.ws_task
            except asyncio.CancelledError:
                pass
            
        # 2. Cerrar sesión aiohttp
        if self.session:
            await self.session.close()
            
        # 3. Limpiar eventos antiguos antes de cerrar (mantener cache limpio)
        await self.cleanup_old_events()
            
        logger.info("🛑 News filter shutdown complete")

    def get_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas para HealthMonitor"""
        stats = self.get_blocking_statistics()
        return {
            "total_events": stats['total_events'],
            "blocking_events_count": len(stats['blocking_events']),
            "ia_analysis_enabled": stats['ia_analysis_enabled'],
            "cache_valid": stats['cache_valid'],
            "cache_age_minutes": stats['cache_age_minutes'],
            "initialized": stats['initialized']
        }