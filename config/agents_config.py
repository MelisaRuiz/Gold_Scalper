{
  "version": "EAS_Hybrid_2025_v1.0",
  "last_updated": "2025-01-18T10:00:00Z",
  "description": "Configuración de Agentes IA - Sistema EAS Híbrido 2025",
  
  "agent_orchestrator": {
    "name": "Trading_Orchestrator_2025",
    "max_concurrent_requests": 5,
    "request_timeout_ms": 3000,
    "consensus_threshold": 0.8,
    "fallback_behavior": "CONSERVATIVE",
    
    "workflow_stages": [
      "DATA_VALIDATION",
      "MACRO_ANALYSIS", 
      "SIGNAL_VALIDATION",
      "LIQUIDITY_ANALYSIS",
      "RISK_ASSESSMENT",
      "FINAL_APPROVAL"
    ]
  },
  
  "enhanced_consistency_engine": {
    "name": "Enhanced_Consistency_Engine",
    "model_provider": "OPENAI",
    "model_name": "gpt-4o-mini",
    "temperature": 0.0,
    "max_tokens": 1000,
    "timeout_ms": 2000,
    
    "validation_criteria": {
      "bos_retest_required": true,
      "session_time_validation": true,
      "risk_parameters_strict": true,
      "macro_context_required": true
    },
    
    "output_format": {
      "required_fields": [
        "validation_score",
        "risk_multiplier", 
        "reasoning_steps",
        "final_decision",
        "confidence_level"
      ],
      "validation_score_range": [0.0, 1.0],
      "risk_multiplier_range": [1.0, 1.5]
    },
    
    "few_shot_examples": [
      {
        "signal_type": "BOS_RETEST_BULLISH",
        "market_context": "NY_OPEN_XAUUSD",
        "macro_conditions": {
          "VIX": 18.5,
          "DXY": 103.2,
          "REAL_YIELDS": 2.3
        },
        "expected_output": {
          "validation_score": 0.87,
          "risk_multiplier": 1.2,
          "reasoning_steps": ["macro_analysis", "technical_validation", "risk_assessment"],
          "final_decision": "APPROVE",
          "confidence_level": 0.85
        }
      },
      {
        "signal_type": "LIQUIDITY_SWEEP_BEARISH", 
        "market_context": "LONDON_OPEN_XAUUSD",
        "macro_conditions": {
          "VIX": 28.0,
          "DXY": 105.0,
          "REAL_YIELDS": 2.8
        },
        "expected_output": {
          "validation_score": 0.42,
          "risk_multiplier": 1.0,
          "reasoning_steps": ["high_volatility_context", "session_mismatch", "technical_weakness"],
          "final_decision": "REJECT",
          "confidence_level": 0.75
        }
      }
    ]
  },
  
  "macro_analysis_agent": {
    "name": "MacroRiskAnalyzer",
    "update_frequency_min": 5,
    "data_sources": [
      "DXY_INDEX",
      "VIX_INDEX", 
      "US_TREASURY_YIELDS",
      "FED_FUNDS_RATE",
      "ECONOMIC_CALENDAR"
    ],
    
    "macro_indicators": {
      "vix_thresholds": {
        "safe_upper": 25.0,
        "warning_upper": 30.0,
        "critical_upper": 35.0
      },
      
      "dxy_correlations": {
        "gold_negative_correlation": -0.7,
        "dxy_safe_range_low": 102.0,
        "dxy_safe_range_high": 105.0
      },
      
      "yield_impact": {
        "real_yields_safe_max": 2.5,
        "yield_gold_correlation": -0.6
      }
    },
    
    "sentiment_analysis": {
      "risk_on_indicators": ["VIX < 20", "DXY < 104", "YIELDS < 2.4"],
      "risk_off_indicators": ["VIX > 25", "DXY > 105", "YIELDS > 2.6"],
      "neutral_indicators": ["VIX 20-25", "DXY 104-105", "YIELDS 2.4-2.6"]
    }
  },
  
  "signal_validation_agent": {
    "name": "SignalValidator",
    "technical_indicators": [
      "PRICE_ACTION",
      "VOLUME_PROFILE",
      "MARKET_STRUCTURE",
      "SUPPORT_RESISTANCE"
    ],
    
    "pattern_recognition": {
      "bos_retest_confidence": 0.8,
      "liquidity_sweep_confidence": 0.75,
      "orderblock_confidence": 0.7,
      "multi_timeframe_alignment_required": true
    },
    
    "volume_analysis": {
      "volume_confirmation_required": true,
      "min_volume_multiplier": 1.2,
      "volume_divergence_detection": true
    }
  },
  
  "liquidity_analysis_agent": {
    "name": "LiquidityAnalyzer",
    "orderbook_analysis": {
      "enabled": true,
      "depth_levels": 5,
      "imbalance_threshold": 0.6,
      "update_frequency_ms": 500
    },
    
    "liquidity_zones": {
      "detection_sensitivity": 0.7,
      "zone_strength_threshold": 0.6,
      "recent_zones_lookback_bars": 50
    },
    
    "market_depth": {
      "min_depth_volume": 10000,
      "depth_imbalance_alert": 0.7
    }
  },
  
  "risk_assessment_agent": {
    "name": "RiskMultiplierCalculator",
    "risk_factors": [
      "MARKET_VOLATILITY",
      "MACRO_SENTIMENT", 
      "TECHNICAL_STRENGTH",
      "LIQUIDITY_CONDITIONS",
      "SESSION_TIMING"
    ],
    
    "risk_multiplier_calculation": {
      "base_multiplier": 1.0,
      "max_multiplier": 1.5,
      "volatility_weight": 0.3,
      "macro_weight": 0.25,
      "technical_weight": 0.25,
      "liquidity_weight": 0.1,
      "timing_weight": 0.1
    },
    
    "volatility_adjustment": {
      "low_volatility_multiplier": 1.2,
      "medium_volatility_multiplier": 1.0,
      "high_volatility_multiplier": 0.8
    }
  },
  
  "safety_guardrails": {
    "input_validation": {
      "max_prompt_length": 1000,
      "allowed_patterns": ["BOS_RETEST", "LIQUIDITY_SWEEP", "ORDERBLOCK"],
      "disallowed_patterns": ["ignore", "override", "system", "prompt"]
    },
    
    "output_validation": {
      "json_schema_validation": true,
      "value_range_checks": true,
      "consistency_checks": true
    },
    
    "jailbreak_detection": {
      "enabled": true,
      "suspicious_patterns": [
        "ignore all previous instructions",
        "system prompt",
        "override risk rules", 
        "change trading strategy",
        "disable kill switch"
      ],
      "auto_block_threshold": 0.8
    }
  },
  
  "performance_optimization": {
    "caching_enabled": true,
    "cache_ttl_seconds": 30,
    "concurrent_processing": true,
    "batch_processing_size": 5,
    "memory_usage_limit_mb": 512
  },
  
  "api_keys": {
    "anthropic": "ANTHROPIC_API_KEY_HERE",
    "alpha_vantage": "ALPHA_VANTAGE_API_KEY_HERE",
    "fred": "FRED_API_KEY_HERE",
    "openai": "OPENAI_API_KEY_HERE"
  }
}