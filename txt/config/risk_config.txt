{
  "version": "EAS_Hybrid_2025_v1.0",
  "last_updated": "2025-01-01T00:00:00Z",
  "description": "Configuración de Gestión de Riesgo - Sistema EAS Híbrido 2025",
  
  "core_risk_parameters": {
    "fixed_risk_per_trade_percent": 0.3,
    "max_portfolio_risk_percent": 5.0,
    "risk_calculation_method": "FIXED_FRACTIONAL",
    "compounding_enabled": false,
    
    "position_sizing": {
      "calculation_method": "RISK_BASED",
      "max_position_size_percent": 2.0,
      "min_position_size_usd": 100,
      "size_increment": 0.01
    }
  },
  
  "dynamic_risk_management": {
    "risk_multiplier_enabled": true,
    "base_multiplier": 1.0,
    "min_multiplier": 1.0,
    "max_multiplier": 1.5,
    "multiplier_increment": 0.1,
    
    "multiplier_factors": {
      "volatility_factor": {
        "enabled": true,
        "weight": 0.3,
        "low_volatility_boost": 0.2,
        "high_volatility_penalty": -0.3
      },
      
      "macro_factor": {
        "enabled": true,
        "weight": 0.25,
        "favorable_conditions_boost": 0.15,
        "unfavorable_penalty": -0.25
      },
      
      "technical_factor": {
        "enabled": true,
        "weight": 0.25,
        "strong_signal_boost": 0.15,
        "weak_signal_penalty": -0.2
      },
      
      "liquidity_factor": {
        "enabled": true,
        "weight": 0.1,
        "high_liquidity_boost": 0.1,
        "low_liquidity_penalty": -0.15
      },
      
      "timing_factor": {
        "enabled": true,
        "weight": 0.1,
        "optimal_session_boost": 0.1,
        "off_session_penalty": -0.1
      }
    }
  },
  
  "stop_loss_management": {
    "stop_loss_method": "TECHNICAL_LEVELS",
    "max_stop_loss_pips": 15.0,
    "min_stop_loss_pips": 2.0,
    
    "technical_levels": {
      "beyond_liquidity_sweep": true,
      "beyond_order_block": true,
      "additional_buffer_pips": 0.5,
      "respect_structure": true
    },
    
    "volatility_adjusted_sl": {
      "enabled": true,
      "atr_multiplier": 1.5,
      "atr_timeframe": "H1",
      "max_atr_stop_multiplier": 2.0
    }
  },
  
  "take_profit_management": {
    "take_profit_method": "FIXED_RISK_REWARD",
    "min_risk_reward_ratio": 1.5,
    "target_risk_reward_ratio": 2.0,
    "max_risk_reward_ratio": 3.0,
    
    "partial_profits": {
      "enabled": true,
      "levels": [
        {
          "profit_target_rr": 1.0,
          "close_percentage": 50,
          "move_sl_to_breakeven": true
        },
        {
          "profit_target_rr": 2.0, 
          "close_percentage": 50,
          "trailing_stop_enabled": true
        }
      ]
    }
  },
  
  "kill_switches": {
    "daily_loss_limits": {
      "enabled": true,
      "soft_limit_percent": 0.8,
      "hard_limit_percent": 1.0,
      "action_on_soft_limit": "REDUCE_RISK",
      "action_on_hard_limit": "STOP_TRADING"
    },
    
    "consecutive_losses": {
      "enabled": true,
      "max_consecutive_losses": 2,
      "action_on_trigger": "STOP_TRADING_AND_ALERT",
      "cooldown_period_hours": 4
    },
    
    "weekly_loss_limits": {
      "enabled": true,
      "soft_limit_percent": 2.0,
      "hard_limit_percent": 3.0,
      "action_on_soft_limit": "REDUCE_RISK_50",
      "action_on_hard_limit": "STOP_TRADING_WEEK"
    },
    
    "monthly_loss_limits": {
      "enabled": true,
      "soft_limit_percent": 4.0,
      "hard_limit_percent": 6.0,
      "action_on_soft_limit": "REDUCE_RISK_75",
      "action_on_hard_limit": "STOP_TRADING_MONTH"
    },
    
    "performance_degradation": {
      "enabled": true,
      "win_rate_threshold": 0.6,
      "profit_factor_threshold": 1.2,
      "drawdown_threshold": 5.0,
      "action_on_trigger": "REVIEW_AND_ADJUST"
    }
  },
  
  "circuit_breakers": {
    "market_volatility": {
      "enabled": true,
      "atr_spike_threshold": 3.0,
      "action_on_trigger": "PAUSE_TRADING",
      "resume_after_normalization": true
    },
    
    "execution_errors": {
      "enabled": true,
      "max_consecutive_errors": 3,
      "error_rate_threshold": 0.05,
      "action_on_trigger": "PAUSE_EXECUTION",
      "cooldown_period_minutes": 5
    },
    
    "data_quality": {
      "enabled": true,
      "min_data_quality_score": 0.7,
      "max_latency_ms": 100,
      "action_on_trigger": "PAUSE_UNTIL_IMPROVED"
    },
    
    "connection_stability": {
      "enabled": true,
      "max_reconnects_per_hour": 5,
      "action_on_trigger": "SWITCH_TO_BACKUP"
    }
  },
  
  "risk_exposure_limits": {
    "maximum_exposure": {
      "max_open_trades": 3,
      "max_correlation_exposure": 0.5,
      "max_sector_exposure": 0.3
    },
    
    "overnight_risk": {
      "close_before_session_end": true,
      "max_overnight_positions": 0,
      "overnight_risk_multiplier": 0.0
    },
    
    "weekend_risk": {
      "close_before_weekend": true,
      "weekend_position_multiplier": 0.0
    }
  },
  
  "risk_monitoring": {
    "real_time_monitoring": {
      "enabled": true,
      "update_frequency_sec": 10,
      "alert_on_risk_breach": true
    },
    
    "risk_reporting": {
      "daily_report": true,
      "weekly_report": true,
      "monthly_report": true,
      "report_automation": true
    },
    
    "risk_dashboard": {
      "enabled": true,
      "refresh_interval_sec": 30,
      "key_metrics_display": [
        "current_exposure",
        "daily_pnl",
        "consecutive_wins_losses",
        "risk_multiplier",
        "kill_switch_status"
      ]
    }
  },
  
  "recovery_protocols": {
    "after_loss_sequence": {
      "risk_reduction_after_loss": 0.5,
      "gradual_recovery_enabled": true,
      "recovery_steps": [0.5, 0.75, 1.0]
    },
    
    "system_failure": {
      "auto_restart_attempts": 3,
      "fallback_to_conservative": true,
      "manual_intervention_required": false
    },
    
    "data_outage": {
      "use_cached_data": true,
      "max_cache_age_minutes": 5,
      "pause_trading_on_prolonged_outage": true
    }
  }
}