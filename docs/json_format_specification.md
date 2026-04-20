# Highway Segmentation - JSON Results Format Specification
**Version**: 1.1.0  
**Date**: April 13, 2026  
**Status**: Phase 1 Implementation - Simplified Essential Features

## 🎯 **Overview**

This document specifies the JSON format for Highway Segmentation analysis results. The format is designed for immediate implementation with essential features, while preserving extensibility for future enhancements.

### **Design Goals - Phase 1**
- **Essential Data Capture**: Core optimization results and basic metadata
- **Cross-Route Aggregation**: Summary statistics for multi-route analysis  
- **Data Traceability**: Column mapping and route processing context
- **Extensible Architecture**: Framework ready for future feature additions
- **Simple Implementation**: Focus on immediate value with clean upgrade path

### **Future Enhancements** *(Commented in schema)*
- Complete reproducibility with detailed environment tracking
- Structured warning and diagnostic system
- Advanced performance metrics and convergence tracking 
- Unique analysis ID generation and cross-analysis tracking

## 📋 **Implementation Scope - Phase 1**

### **Essential Features** *(Implemented Now)*

**Analysis Context:**
- Analysis timestamp and method identification
- Basic software version (application name and version)
- Analysis status (completed, failed, partial, interrupted)

**Cross-Route Aggregation:**
- `total_processing_time`: Complete analysis runtime in seconds
- `total_routes_processed`: Number of routes successfully analyzed  
- `total_length_processed`: Sum of all route lengths analyzed (miles/km)

**Data Traceability:**
- Column mapping (`x_column`, `y_column`, optional `route_column`)
- Input file metadata (name, size, row count)
- Total routes available vs processed

**Route Processing Context:**
- `route_filtering_applied`: Whether route selection was used
- `total_routes_in_source`: Routes available in input data
- Route processing configuration and selected route list

### **Input Parameters** (*Complete Reproducibility*)

**Method Configuration:**
- Analysis method key and human-readable display name
- Method description from configuration system

**Core Method Parameters:**
- All algorithm parameters defined by the selected optimization method
- Validation ranges, data types, and UI visibility controlled by method configuration
- Hidden parameters included for reproducibility but not exposed in UI

**Extensible Method-Specific Parameters:**
- Complete parameter set for the chosen optimization method 
- Algorithm parameters: population_size, num_generations, mutation_rate, crossover_rate, etc.
- Segmentation parameters: min_length, max_length, gap_threshold
- Method-specific parameters: target_avg_length, penalty_weight (for constrained methods)
- All parameters defined by the selected optimization method configuration

**Route Processing Configuration:**
- Route mode (single_route vs multi_route)
- Column mappings (x_column, y_column, route_column)
- Selected routes array for processing

**System Configuration:**
- Cache settings, random seeds for reproducibility
- Algorithm constants and UI settings
- All configuration dataclass values

### **Route-Specific Data** (*Per Route Processing*)

**Route Identification:**
- Route ID, display name, processing order
- Optional route-specific notes

**Input Data Analysis:**
```json
{
  "data_summary": {
    "total_data_points": 1247,
    "data_range": {"x_min": 0.0, "x_max": 25.3, "y_min": 0.5, "y_max": 8.2},
    "data_quality": {"valid_points": 1247, "invalid_points": 0, "duplicate_points": 3}
  },
  "gap_analysis": {
    "gap_segments": [
      {"start": 5.2, "end": 7.1, "length": 1.9},
      {"start": 12.4, "end": 13.6, "length": 1.2}
    ],
    "total_gaps": 2, "total_gap_length": 3.1, "largest_gap": 1.9,
    "gap_threshold_used": 0.5,
    "breakpoint_consolidation": {
      "original_breakpoints": [0.0, 5.0, 5.2, 5.3, 7.1, 7.2, 12.4, 13.6, 15.6, 16.8, 25.3],
      "removed_breakpoints": [5.0, 5.3, 7.2],
      "consolidation_reason": "gap_threshold_processing"
    }
  },
  "mandatory_segments": {
    "mandatory_breakpoints": [0.0, 5.2, 7.1, 15.6, 16.8, 25.3],
    "analyzable_segments": [{"start": 0.0, "end": 5.2, "length": 5.2, "type": "data"}],
    "total_analyzable_length": 22.2
  }
}
```

**Processing Results** (*Unified Pareto Structure*):

**IMPORTANT**: All output `breakpoints` arrays **must include all mandatory breakpoints** from the gap analysis, plus any additional breakpoints added by the optimization algorithm. Mandatory breakpoints cannot be removed by the optimization process.

*Single-Objective (1 pareto point):*
```json
{
  "pareto_points": [{
    "point_id": 0,
    "objective_values": [2.47],
    "segmentation": {
      "breakpoints": [0.0, 3.2, 5.2, 7.1, 8.1, 15.4, 15.6, 16.8, 25.3],
      "segment_lengths": [3.2, 2.0, 1.9, 1.0, 7.3, 0.2, 1.2, 8.5],
      "segment_count": 8
    }
  }]
}
```

*Multi-Objective (multiple pareto points):*
```json
{
  "pareto_points": [
    {
      "point_id": 0, 
      "objective_values": [1.85, 3.2], 
      "segmentation": {
        "breakpoints": [0.0, 2.5, 5.2, 7.1, 12.3, 15.6, 16.8, 25.3],
        "segment_lengths": [2.5, 2.7, 1.9, 5.2, 3.3, 1.2, 8.7],
        "segment_count": 7
      }
    },
    {
      "point_id": 1, 
      "objective_values": [2.1, 2.8], 
      "segmentation": {
        "breakpoints": [0.0, 5.2, 7.1, 11.8, 15.6, 16.8, 22.4, 25.3],
        "segment_lengths": [5.2, 1.9, 4.7, 3.8, 1.2, 5.6, 2.9],
        "segment_count": 7
      }
    }
  ]
}
```

*Constrained (1 point with method-specific results):*
```json
{
  "pareto_points": [{
    "point_id": 0,
    "objective_values": [2.31],
    "segmentation": {
      "breakpoints": [0.0, 2.1, 5.2, 7.1, 9.3, 15.6, 16.8, 18.9, 25.3],
      "segment_lengths": [2.1, 3.1, 1.9, 2.2, 6.3, 1.2, 2.1, 6.4],
      "segment_count": 8
    }
  }]
}
```

All processing results follow the unified pareto_points structure regardless of optimization method used.

---

## 🏗️ **JSON Schema Structure**

### **Top-Level Architecture**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://mottmac.com/schemas/highway-segmentation/results/v1.0.0",
  "title": "Highway Segmentation Analysis Results",
  "version": "1.1.0",
  "type": "object",
  "required": ["analysis_metadata", "input_parameters", "route_results"],
  
  "properties": {
    "analysis_metadata": { /* Analysis context and summaries */ },
    "method_specific_analysis_stats": { /* Optional method-specific statistics */ },
    "input_parameters": { /* Complete reproducibility data */ },
    "route_results": [ /* Array of per-route results */ ]
  }
}
```

### **1. Analysis Metadata Schema**

```json
"analysis_metadata": {
  "type": "object",
  "required": ["analysis_id", "timestamp", "software_version", "analysis_method", "analysis_status"],
  "properties": {
    "analysis_id": {
      "type": "string",
      "pattern": "^highway_seg_[0-9]{8}_[0-9]{6}$",
      "description": "highway_seg_YYYYMMDD_HHMMSS"
    },
    "timestamp": {"type": "string", "format": "date-time"},
    "software_version": {
      "type": "object",
      "properties": {
        "application": {"type": "string", "default": "Highway Segmentation"},
        "version": {"type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"},
        "build_date": {"type": "string", "format": "date"},
        "python_version": {"type": "string"}
      }
    },
    "analysis_method": {
      "type": "string", 
      "enum": ["single_objective", "multi_objective", "constrained"]
    },
    "analysis_status": {
      "type": "string",
      "enum": ["completed", "failed", "partial", "interrupted"]
    },
    "input_file_info": {
      "type": "object",
      "required": ["file_name", "total_data_rows"],
      "properties": {
        "data_file_path": {"type": "string"},
        "data_file_name": {"type": "string"},
        "data_file_size_bytes": {"type": "integer", "minimum": 0},
        "data_file_modified": {"type": "string", "format": "date-time"},
        "total_data_rows": {"type": "integer", "minimum": 1},
        "total_routes_available": {"type": "integer", "minimum": 1},
        "column_info": {
          "type": "object",
          "required": ["total_columns", "x_column", "y_column"],
          "properties": {
            "total_columns": {"type": "integer", "minimum": 3},
            "x_column": {"type": "string"},
            "y_column": {"type": "string"},
            "route_column": {"type": ["string", "null"]}
          }
        }
      }
    },
    "analysis_summary": {
      "type": "object",
      "required": ["total_processing_time", "total_routes_processed"],
      "properties": {
        "total_processing_time": {"type": "number", "minimum": 0},
        "total_routes_processed": {"type": "integer", "minimum": 1},
        "total_length_processed": {"type": "number", "minimum": 0},
        "total_segments_generated": {"type": "integer", "minimum": 0},
        "total_breakpoints_generated": {"type": "integer", "minimum": 0},
        "total_pareto_points": {"type": "integer", "minimum": 1},
        "average_processing_time_per_route": {"type": "number", "minimum": 0},
        "total_data_points_processed": {"type": "integer", "minimum": 0},
        "total_gaps_identified": {"type": "integer", "minimum": 0},
        "average_segments_per_route": {"type": "number", "minimum": 0}
      }
    },
    "analysis_warnings": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type", "message", "severity"],
        "properties": {
          "type": {"type": "string", "enum": ["data_quality", "algorithm", "parameter", "system"]},
          "message": {"type": "string"},
          "severity": {"type": "string", "enum": ["info", "warning", "error"]},
          "route_id": {"type": ["string", "null"]},
          "timestamp": {"type": "string", "format": "date-time"}
        }
      }
    }
  }
}
```

### **2. Method-Specific Analysis Statistics Schema**

```json
"method_specific_analysis_stats": {
  "type": "object",
  "title": "Method-Specific Analysis Statistics",
  "description": "Optional post-analysis method-specific data about the full analysis. Each optimization method can populate this with their own performance metrics and statistics.",
  "additionalProperties": true,
  "patternProperties": {
    ".*": {
      "anyOf": [
        {"type": "string"},
        {"type": "number"},
        {"type": "boolean"},
        {"type": "array"},
        {"type": "object"}
      ]
    }
  }
}
```

### **3. Input Parameters Schema**

```json
"input_parameters": {
  "type": "object",
  "required": ["optimization_method_config", "method_parameters", "route_processing"],
  "properties": {
    "optimization_method_config": {
      "type": "object",
      "required": ["method_key", "display_name"],
      "properties": {
        "method_key": {"type": "string"},
        "display_name": {"type": "string"},
        "description": {"type": "string"}
      }
    },
    "method_parameters": {
      "type": "object",
      "description": "Complete parameter set for the optimization method, including all algorithm parameters and method-specific settings",
      "patternProperties": {
        ".*": {
          "anyOf": [
            {"type": "string"}, {"type": "number"}, {"type": "boolean"}, 
            {"type": "array"}, {"type": "object"}
          ]
        }
      }
    },
    "route_processing": {
      "type": "object", 
      "required": ["route_mode", "selected_routes"],
      "properties": {
        "route_mode": {"type": "string", "enum": ["single_route", "multi_route"]},
        "route_column": {"type": ["string", "null"]},
        "x_column": {"type": "string"},
        "y_column": {"type": "string"},
        "selected_routes": {
          "type": "array",
          "items": {"type": "string"},
          "minItems": 1
        },
        "route_filtering_applied": {"type": "boolean"},
        "total_routes_in_source": {"type": "integer", "minimum": 1},
        "total_routes_processed": {"type": "integer", "minimum": 1}
      }
    },
    "system_config": {
      "type": "object",
      "properties": {
        "cache_clear_interval": {"type": "integer", "minimum": 1},
        "random_seed": {"type": ["integer", "null"]},
        "algorithm_constants": {"type": "object"},
        "ui_settings": {"type": "object"}
      }
    }
  }
}
```

### **4. Route Results Schema**

```json
"route_results": {
  "type": "array",
  "minItems": 1,
  "items": {
    "type": "object",
    "required": ["route_info", "input_data_analysis", "processing_results"],
    "properties": {
      "route_info": {
        "type": "object", 
        "required": ["route_id"],
        "properties": {
          "route_id": {"type": "string"}
        }
      },
      "input_data_analysis": {
        "type": "object",
        "required": ["data_summary", "gap_analysis", "mandatory_segments"],
        "properties": {
          "data_summary": {
            "type": "object",
            "required": ["total_data_points", "data_range"],
            "properties": {
              "total_data_points": {"type": "integer", "minimum": 3},
              "data_range": {
                "type": "object",
                "required": ["x_min", "x_max", "y_min", "y_max"],
                "properties": {
                  "x_min": {"type": "number"}, "x_max": {"type": "number"},
                  "y_min": {"type": "number"}, "y_max": {"type": "number"}
                }
              },
              "data_quality": {
                "type": "object",
                "properties": {
                  "valid_points": {"type": "integer", "minimum": 0},
                  "invalid_points": {"type": "integer", "minimum": 0},
                  "duplicate_points": {"type": "integer", "minimum": 0}
                }
              }
            }
          },
          "gap_analysis": {
            "type": "object",
            "required": ["gap_segments", "total_gaps"],
            "properties": {
              "gap_segments": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["start", "end", "length"],
                  "properties": {
                    "start": {"type": "number"},
                    "end": {"type": "number"},
                    "length": {"type": "number", "minimum": 0}
                  }
                }
              },
              "total_gaps": {"type": "integer", "minimum": 0},
              "total_gap_length": {"type": "number", "minimum": 0},
              "largest_gap": {"type": "number", "minimum": 0},
              "gap_threshold_used": {"type": "number", "minimum": 0},
              "breakpoint_consolidation": {
                "type": "object",
                "properties": {
                  "original_breakpoints": {
                    "type": "array",
                    "items": {"type": "number"}
                  },
                  "removed_breakpoints": {
                    "type": "array", 
                    "items": {"type": "number"}
                  },
                  "consolidation_reason": {"type": "string"}
                }
              }
            }
          },
          "mandatory_segments": {
            "type": "object",
            "required": ["mandatory_breakpoints", "analyzable_segments"],
            "properties": {
              "mandatory_breakpoints": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 2
              },
              "analyzable_segments": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["start", "end", "length", "type"],
                  "properties": {
                    "start": {"type": "number"},
                    "end": {"type": "number"},
                    "length": {"type": "number", "minimum": 0},
                    "type": {"type": "string", "enum": ["data", "boundary"]}
                  }
                }
              },
              "total_analyzable_length": {"type": "number", "minimum": 0}
            }
          }
        }
      },
      "processing_results": {
        "type": "object",
        "required": ["pareto_points"],
        "properties": {
          "pareto_points": {
            "type": "array",
            "minItems": 1,
            "items": {
              "type": "object",
              "required": ["point_id", "objective_values"],
              "properties": {
                "point_id": {"type": "integer", "minimum": 0},
                "objective_values": {
                  "type": "array",
                  "items": {"type": "number"},
                  "minItems": 1
                },
                "segmentation": {
                  "type": "object",
                  "required": ["breakpoints", "segment_lengths"],
                  "properties": {
                    "breakpoints": {
                      "type": "array",
                      "items": {"type": "number"},
                      "minItems": 2,
                      "description": "All breakpoints including mandatory breakpoints plus optimization-generated breakpoints"
                    },
                    "segment_lengths": {
                      "type": "array", 
                      "items": {"type": "number", "minimum": 0}
                    },
                    "segment_count": {"type": "integer", "minimum": 1},
                    "total_length": {"type": "number", "minimum": 0},
                    "average_segment_length": {"type": "number", "minimum": 0},
                    "segment_details": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "segment_index": {"type": "integer", "minimum": 0},
                          "start": {"type": "number"}, "end": {"type": "number"},
                          "length": {"type": "number", "minimum": 0},
                          "is_mandatory": {"type": "boolean"},
                          "data_point_count": {"type": "integer", "minimum": 0},
                          "y_value_min": {"type": ["number", "null"]},
                          "y_value_max": {"type": ["number", "null"]}, 
                          "y_value_avg": {"type": ["number", "null"]},
                          "y_value_std": {"type": ["number", "null"]}
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
    }
  }
}
```

---

## 🔧 **Key Design Decisions**

### **Unified Pareto Architecture**
- **All methods use pareto_points array** (single-objective = 1 point, multi-objective = multiple points)
- **Segmentation data embedded directly** in each pareto point (no separate arrays or cross-references)
- **Extensible constraint information** for specialized optimization methods

### **Complete Reproducibility Framework**
- **All input parameters preserved** with exact data types and validation ranges
- **System configuration captured** including random seeds and algorithm constants  
- **File metadata enables verification** of input data integrity
- **Processing context allows exact replication** of analysis conditions

### **Analysis-Wide Insights**
- **Summary statistics at top level** (total time, routes, length processed)
- **Individual route statistics preserved** separately for detailed analysis
- **Performance metrics captured** for optimization and debugging purposes
- **No comparative analysis** between routes in standard output (as requested)

### **Extensibility Mechanisms**
- **Unified method_parameters structure** supports any current or future optimization method
- **Hidden parameter support** allows internal algorithm settings without UI clutter
- **Configuration-driven validation** ensures parameter integrity based on method schema
- **PatternProperties allow arbitrary fields** for specialized analysis methods
- **Flexible statistics structure** accommodates different algorithm performance metrics
- **Structured warning/error reporting** supports diverse diagnostic needs

### **Data Integrity Guarantees**
- **Strong typing with validation ranges** (e.g., population_size: 10-10000)
- **Required vs optional fields clearly defined** for critical vs supplementary data
- **Enum validation for controlled vocabularies** (status fields, analysis methods)
- **Referential integrity** (segmentation data directly contained within pareto points)

---

## 🎯 **Implementation Guidance**

### **Phase 2 Integration Points**
1. **Unified Results Structure**: Direct mapping from JSON schema to Python dataclasses
2. **StandardResultsWriter**: Use this schema as output format specification
3. **Validation Framework**: Implement JSON Schema validation for data integrity
4. **Visualization Loading**: Parse results using predictable schema structure
5. **Hidden Parameter Support**: Configuration system controls UI visibility while preserving full reproducibility

### **Configuration System Integration**

**Method Configuration with Hidden Parameters:**
```python
# Enhanced ParameterDefinition with UI visibility control
@dataclass
class ParameterDefinition:
    name: str
    display_name: str
    description: str
    data_type: type
    default_value: Any
    validation_range: tuple
    group: str
    show_in_ui: bool = True  # New field for UI visibility

# Method definition with hidden parameters
GENETIC_ALGORITHM_METHOD = OptimizationMethod(
    method_key="single_objective_ga",
    display_name="Single-Objective Genetic Algorithm",
    parameters=[
        # UI-visible parameters
        ParameterDefinition("population_size", "Population Size", 
                          "Number of individuals in population", int, 100, (10, 10000), "algorithm", True),
        ParameterDefinition("num_generations", "Generations", 
                          "Number of evolutionary generations", int, 200, (1, 100000), "algorithm", True),
        ParameterDefinition("min_length", "Min Length", 
                          "Minimum segment length", float, 0.2, (0.1, 1.0), "constraints", True),
        
        # Hidden parameters (not in UI, but in results for reproducibility)
        ParameterDefinition("selection_pressure", "Selection Pressure", 
                          "Internal selection pressure coefficient", float, 2.0, (1.0, 5.0), "algorithm", False),
        ParameterDefinition("diversity_threshold", "Diversity Threshold", 
                          "Population diversity monitoring threshold", float, 0.01, (0.001, 0.1), "algorithm", False),
        ParameterDefinition("cache_warming_iterations", "Cache Warming", 
                          "Pre-computation iterations for performance", int, 10, (0, 100), "system", False),
    ]
)
```

**Benefits of Hidden Parameters:**
- **Clean UI**: Only essential parameters shown to users
- **Complete Reproducibility**: All parameters saved in results JSON
- **Algorithm Flexibility**: Internal tuning parameters preserved
- **Developer Control**: Fine-grained control over what users see vs. what's tracked

### **Extensibility Patterns**

**Adding New Analysis Methods:**
```python
# Single-Objective method parameters
"method_parameters": {
  "population_size": 100,
  "num_generations": 200, 
  "mutation_rate": 0.1,
  "crossover_rate": 0.8,
  "elite_ratio": 0.1,
  "tournament_size": 3,
  "min_length": 0.2,
  "max_length": 10.0,
  "gap_threshold": 0.5
}

# Multi-Objective method parameters  
"method_parameters": {
  "population_size": 150,
  "num_generations": 300,
  "mutation_rate": 0.15,
  "crossover_rate": 0.85,
  "archive_size": 100,
  "min_length": 0.2,
  "max_length": 10.0,
  "gap_threshold": 0.5
}

# Constrained method parameters
"method_parameters": {
  "population_size": 120,
  "num_generations": 250,
  "mutation_rate": 0.12,
  "crossover_rate": 0.8,
  "target_avg_length": 2.5,
  "penalty_weight": 100.0,
  "length_tolerance": 0.1,
  "min_length": 0.2,
  "max_length": 10.0,
  "gap_threshold": 0.5
}
```

**Method-Specific Results Extension:**
```python
# Methods can add specialized results within method_parameters or custom fields
"method_parameters": {
  // Standard parameters
  "population_size": 100,
  
  // Method can store custom results/statistics if needed
  "final_population_diversity": 0.73,
  "convergence_metrics": {"generation": 150, "improvement_rate": 0.045}
}
```

### **Third-Party Integration**

**External Tool Consumption:**
- Standard JSON Schema format with validation rules
- Predictable field names and data structures  
- Complete analysis context for external processing
- Extensible warning/error reporting for diagnostics

**Data Export/Import:**
- JSON format enables easy serialization/deserialization
- Schema validation ensures data integrity during transfers
- Complete reproducibility context for analysis replication
- Backward compatibility through schema versioning

---

## ✅ **Validation & Testing**

### **Schema Validation Requirements**
- All JSON output must validate against this schema
- Required fields must be present and properly typed
- Value ranges must be respected (non-negative lengths, valid percentages)
- Referential integrity must be maintained (segmentation ↔ pareto point links)

### **Sample JSON Files** (*To Be Created*)
- Single-objective analysis with 1 route
- Multi-objective analysis with pareto front  
- Multi-route processing with 3+ routes
- Constrained optimization with constraint details

### **Migration Strategy**
- Current CSV results can be imported to JSON format
- JSON Schema versioning supports future format evolution
- Fallback CSV export maintained for user compatibility
- Clear upgrade path from existing result formats

---

## 📅 **Next Steps**

1. **Create sample JSON files** validating the schema design (Step 1.5.6)
2. **Implement JSON Schema validation** in Python code
3. **Design Python dataclasses** matching the JSON structure  
4. **Create StandardResultsWriter** using this format specification
5. **Update visualization loading** to parse JSON results structure

---

**Status**: **Design Complete** - Ready for Phase 2 implementation using this specification as the authoritative guide.

## **Recent Updates** *(v1.1.0 - April 13, 2026)*

**Schema Enhancements:**
- Added `method_specific_analysis_stats` section for extensible method-specific performance metrics
- Enhanced segment details with statistical measures: `data_point_count`, `y_value_min/max/avg/std`
- Added route processing context fields: `route_filtering_applied`, `total_routes_in_source`, `total_routes_processed`
- Updated schema documentation to reflect actual implementation in `src/highway_segmentation_results_schema.json`