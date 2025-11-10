#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests para los Módulos Core - EAS Híbrido 2025
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.risk_manager import RiskManager
from core.signal_generator import SignalGenerator
from core.execution_engine import ExecutionEngine
from core.session_manager import SessionManager
from infrastructure.structured_logger import get_eas_logger

class TestRiskManager(unittest.TestCase):
    """Tests para el gestor de riesgo"""
    
    def setUp(self):
        self.risk_manager = RiskManager()
        self.account_balance = 10000.0
    
    def test_lot_size_calculation(self):
        """Test cálculo preciso del tamaño de lote"""
        # Test caso normal
        lot_size = self.risk_manager.calculate_lot_size(
            account_balance=self.account_balance,
            risk_percent=0.3,
            entry_price=1950.0,
            stop_loss=1945.0,
            symbol='XAUUSD'
        )
        
        self.assertIsInstance(lot_size, float)
        self.assertGreater(lot_size, 0.0)
        
        # Test que respeta límites del broker
        min_lot = 0.01
        max_lot = 10.0
        normalized_lot = self.risk_manager.normalize_lot_size(
            lot_size, min_lot, max_lot, 0.01
        )
        
        self.assertGreaterEqual(normalized_lot, min_lot)
        self.assertLessEqual(normalized_lot, max_lot)
    
    def test_risk_multiplier_application(self):
        """Test aplicación de multiplicadores de riesgo"""
        base_risk = 0.3
        multipliers = [1.0, 1.2, 1.5]
        
        for multiplier in multipliers:
            adjusted_risk = self.risk_manager.apply_risk_multiplier(
                base_risk, multiplier
            )
            expected_risk = base_risk * multiplier
            self.assertEqual(adjusted_risk, expected_risk)
    
    def test_kill_switch_activation(self):
        """Test activación de kill switches"""
        # Test límite de pérdidas consecutivas
        for i in range(3):
            self.risk_manager.record_trade_result(loss=True)
        
        should_activate = self.risk_manager.check_kill_switches()
        self.assertTrue(should_activate)
        
        # Reset y test límite diario
        self.risk_manager.reset_daily_metrics()
        self.risk_manager.daily_loss = 1.2  # Excede 1.0%
        
        should_activate = self.risk_manager.check_kill_switches()
        self.assertTrue(should_activate)
    
    def test_circuit_breaker_management(self):
        """Test gestión de circuit breakers"""
        # Simular múltiples errores
        for _ in range(5):
            self.risk_manager.record_execution_error()
        
        is_breaker_active = self.risk_manager.is_circuit_breaker_active()
        self.assertTrue(is_breaker_active)
        
        # Verificar cooldown
        self.assertTrue(self.risk_manager.circuit_breaker_cooldown_remaining() > 0)

class TestSignalGenerator(unittest.TestCase):
    """Tests para el generador de señales"""
    
    def setUp(self):
        self.signal_generator = SignalGenerator()
    
    def test_bos_retest_detection(self):
        """Test detección de patrón BOS_RETEST"""
        market_data = {
            'price_action': {
                'liquidity_sweep': True,
                'orderblock_retest': True,
                'break_of_structure': True
            },
            'volume': {
                'confirmation': True,
                'spike_detected': True
            },
            'timeframe': 'M15'
        }
        
        signal = self.signal_generator.detect_bos_retest(market_data)
        self.assertIsNotNone(signal)
        self.assertEqual(signal['pattern'], 'BOS_RETEST')
        self.assertGreaterEqual(signal['confidence'], 0.7)
    
    def test_multi_timeframe_confirmation(self):
        """Test confirmación multi-timeframe"""
        timeframe_data = {
            'M15': {'signal': 'BULLISH', 'strength': 0.8},
            'H1': {'signal': 'BULLISH', 'strength': 0.7},
            'D1': {'signal': 'BULLISH', 'strength': 0.6}
        }
        
        is_confirmed = self.signal_generator.check_multi_timeframe_alignment(
            timeframe_data
        )
        self.assertTrue(is_confirmed)
        
        # Test con falta de alineación
        timeframe_data['H1']['signal'] = 'BEARISH'
        is_confirmed = self.signal_generator.check_multi_timeframe_alignment(
            timeframe_data
        )
        self.assertFalse(is_confirmed)
    
    def test_volume_analysis(self):
        """Test análisis de volumen"""
        volume_data = {
            'current': 1500,
            'average': 1000,
            'trend': 'increasing'
        }
        
        volume_analysis = self.signal_generator.analyze_volume(volume_data)
        self.assertTrue(volume_analysis['is_confirming'])
        self.assertGreater(volume_analysis['volume_ratio'], 1.0)
    
    def test_signal_filtering(self):
        """Test filtrado de señales"""
        signals = [
            {'pattern': 'BOS_RETEST', 'confidence': 0.9, 'timeframe': 'M15'},
            {'pattern': 'BOS_RETEST', 'confidence': 0.6, 'timeframe': 'M15'},
            {'pattern': 'NOISE', 'confidence': 0.3, 'timeframe': 'M1'}
        ]
        
        filtered_signals = self.signal_generator.filter_signals(
            signals, min_confidence=0.7
        )
        
        self.assertEqual(len(filtered_signals), 1)
        self.assertEqual(filtered_signals[0]['confidence'], 0.9)

class TestExecutionEngine(unittest.IsolatedAsyncioTestCase):
    """Tests para el motor de ejecución"""
    
    async def asyncSetUp(self):
        self.execution_engine = ExecutionEngine()
        await self.execution_engine.initialize()
    
    async def test_order_validation(self):
        """Test validación de órdenes"""
        valid_order = {
            'symbol': 'XAUUSD',
            'operation': 'BUY',
            'volume': 0.1,
            'price': 1950.25,
            'sl': 1945.25,
            'tp': 1960.25
        }
        
        is_valid = await self.execution_engine.validate_order(valid_order)
        self.assertTrue(is_valid)
        
        # Test orden inválida
        invalid_order = valid_order.copy()
        invalid_order['volume'] = 100.0  # Volumen excesivo
        
        is_valid = await self.execution_engine.validate_order(invalid_order)
        self.assertFalse(is_valid)
    
    async def test_limit_order_execution(self):
        """Test ejecución de órdenes limit"""
        order_request = {
            'symbol': 'XAUUSD',
            'operation': 'BUY_LIMIT',
            'volume': 0.1,
            'price': 1949.50,
            'sl': 1945.50,
            'tp': 1959.50,
            'expiration': 300  # 5 minutos
        }
        
        with patch('core.execution_engine.MT5Connector') as mock_mt5:
            mock_mt5.send_order.return_value = {
                'retcode': 10009,  # MT5 ORDER_SENT
                'order': 123456,
                'volume': 0.1,
                'price': 1949.50,
                'bid': 1950.0,
                'ask': 1950.1
            }
            
            result = await self.execution_engine.execute_limit_order(order_request)
            self.assertTrue(result['success'])
            self.assertEqual(result['order_id'], 123456)
    
    async def test_slippage_control(self):
        """Test control de slippage"""
        order_request = {
            'symbol': 'XAUUSD',
            'operation': 'BUY',
            'volume': 0.1,
            'price': 1950.25,
            'max_slippage': 0.5  # 0.5 pips
        }
        
        execution_prices = [1950.25, 1950.30, 1950.35, 1950.75]
        
        for exec_price in execution_prices:
            has_excessive_slippage = self.execution_engine.check_slippage(
                order_request['price'], exec_price, order_request['max_slippage']
            )
            
            if exec_price > 1950.75:  # Más de 0.5 pips
                self.assertTrue(has_excessive_slippage)
            else:
                self.assertFalse(has_excessive_slippage)
    
    async def test_circuit_breaker_integration(self):
        """Test integración con circuit breakers"""
        # Simular múltiples errores de ejecución
        for _ in range(5):
            self.execution_engine.record_execution_error()
        
        is_breaker_active = self.execution_engine.is_circuit_breaker_active()
        self.assertTrue(is_breaker_active)
        
        # Verificar que no se ejecutan órdenes con breaker activo
        order_request = {
            'symbol': 'XAUUSD',
            'operation': 'BUY',
            'volume': 0.1
        }
        
        result = await self.execution_engine.execute_market_order(order_request)
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'CIRCUIT_BREAKER_ACTIVE')
    
    async def test_retry_mechanism(self):
        """Test mecanismo de reintentos"""
        order_request = {
            'symbol': 'XAUUSD',
            'operation': 'BUY',
            'volume': 0.1
        }
        
        with patch('core.execution_engine.MT5Connector') as mock_mt5:
            # Simular fallo seguido de éxito
            mock_mt5.send_order.side_effect = [
                Exception("Network error"),
                {'retcode': 10009, 'order': 123456}
            ]
            
            result = await self.execution_engine.execute_with_retry(order_request)
            self.assertTrue(result['success'])
            self.assertEqual(mock_mt5.send_order.call_count, 2)

class TestSessionManager(unittest.TestCase):
    """Tests para el gestor de sesiones"""
    
    def setUp(self):
        self.session_manager = SessionManager()
    
    def test_ny_session_detection(self):
        """Test detección de sesión NY"""
        # Test dentro de horario NY
        ny_time = "2025-01-18 10:00:00"  # 10 AM ET
        is_ny_session = self.session_manager.is_ny_session(ny_time)
        self.assertTrue(is_ny_session)
        
        # Test fuera de horario NY
        non_ny_time = "2025-01-18 20:00:00"  # 8 PM ET
        is_ny_session = self.session_manager.is_ny_session(non_ny_time)
        self.assertFalse(is_ny_session)
    
    def test_london_ny_overlap(self):
        """Test detección de overlap Londres-NY"""
        overlap_time = "2025-01-18 13:00:00"  # 1 PM GMT (8 AM ET)
        is_overlap = self.session_manager.is_london_ny_overlap(overlap_time)
        self.assertTrue(is_overlap)
    
    def test_news_event_filter(self):
        """Test filtrado por eventos de noticias"""
        # Test con evento de alta importancia
        high_impact_event = {
            'event': 'FED_RATE_DECISION',
            'importance': 'HIGH',
            'timestamp': '2025-01-18T14:00:00Z',
            'buffer_minutes': 60
        }
        
        current_time = "2025-01-18 14:30:00"  # 30 minutos después
        should_block = self.session_manager.should_block_for_news(
            high_impact_event, current_time
        )
        self.assertTrue(should_block)
        
        # Test fuera del buffer
        current_time = "2025-01-18 15:30:00"  # 90 minutos después
        should_block = self.session_manager.should_block_for_news(
            high_impact_event, current_time
        )
        self.assertFalse(should_block)
    
    def test_volatility_filter(self):
        """Test filtrado por volatilidad"""
        # Test con volatilidad normal
        normal_volatility = {
            'atr': 2.5,
            'threshold': 3.0
        }
        should_block = self.session_manager.should_block_for_volatility(
            normal_volatility
        )
        self.assertFalse(should_block)
        
        # Test con volatilidad alta
        high_volatility = {
            'atr': 4.0,
            'threshold': 3.0
        }
        should_block = self.session_manager.should_block_for_volatility(
            high_volatility
        )
        self.assertTrue(should_block)
    
    def test_session_metrics(self):
        """Test tracking de métricas de sesión"""
        # Simular múltiples operaciones
        trades = [
            {'result': 'win', 'duration': 5},
            {'result': 'loss', 'duration': 3},
            {'result': 'win', 'duration': 7}
        ]
        
        for trade in trades:
            self.session_manager.record_trade(trade)
        
        metrics = self.session_manager.get_session_metrics()
        
        self.assertEqual(metrics['total_trades'], 3)
        self.assertEqual(metrics['win_rate'], 2/3)
        self.assertAlmostEqual(metrics['avg_trade_duration'], 5.0)

class TestIntegrationCoreModules(unittest.IsolatedAsyncioTestCase):
    """Tests de integración entre módulos core"""
    
    async def asyncSetUp(self):
        self.risk_manager = RiskManager()
        self.signal_generator = SignalGenerator()
        self.execution_engine = ExecutionEngine()
        self.session_manager = SessionManager()
        
        await self.execution_engine.initialize()
    
    async def test_complete_trading_workflow(self):
        """Test flujo completo de trading"""
        # 1. Generar señal
        market_data = {
            'price_action': {
                'liquidity_sweep': True,
                'orderblock_retest': True
            },
            'volume': {'confirmation': True},
            'timeframe': 'M15'
        }
        
        signal = self.signal_generator.detect_bos_retest(market_data)
        self.assertEqual(signal['pattern'], 'BOS_RETEST')
        
        # 2. Validar sesión
        is_valid_session = self.session_manager.is_ny_session("2025-01-18 10:00:00")
        self.assertTrue(is_valid_session)
        
        # 3. Calcular riesgo
        lot_size = self.risk_manager.calculate_lot_size(
            account_balance=10000,
            risk_percent=0.3,
            entry_price=1950.0,
            stop_loss=1945.0,
            symbol='XAUUSD'
        )
        self.assertGreater(lot_size, 0.0)
        
        # 4. Ejecutar orden (mock)
        order_request = {
            'symbol': 'XAUUSD',
            'operation': 'BUY_LIMIT',
            'volume': lot_size,
            'price': 1949.50,
            'sl': 1945.0,
            'tp': 1960.0
        }
        
        with patch('core.execution_engine.MT5Connector') as mock_mt5:
            mock_mt5.send_order.return_value = {
                'retcode': 10009,
                'order': 123456
            }
            
            result = await self.execution_engine.execute_limit_order(order_request)
            self.assertTrue(result['success'])
            
            # 5. Registrar resultado
            self.risk_manager.record_trade_result(loss=False)
            self.session_manager.record_trade({
                'result': 'win',
                'duration': 5,
                'profit': 100.0
            })
        
        # Verificar métricas finales
        risk_metrics = self.risk_manager.get_risk_metrics()
        session_metrics = self.session_manager.get_session_metrics()
        
        self.assertEqual(risk_metrics['consecutive_losses'], 0)
        self.assertEqual(session_metrics['win_rate'], 1.0)

if __name__ == '__main__':
    unittest.main(verbosity=2)