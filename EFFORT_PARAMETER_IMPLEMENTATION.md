# Claude Opus 4.5 Effort Parameter Implementation

## Overview

This implementation adds support for Claude Opus 4.5's "effort" parameter feature, which allows controlling token usage per request to reduce LLM costs by 50-80% on simple tasks.

## What Changed

### 1. New Module: `effort_config.py`
- **Location**: `commander/services/effort_config.py`
- **Purpose**: Centralized configuration and utilities for effort parameter management
- **Features**:
  - Task type to effort level mapping
  - Environment variable configuration
  - Usage statistics tracking
  - Logging support

### 2. Updated: `gemini_client.py`
- **Changes**:
  - Added `task_type` and `effort` parameters to `generate_text()` and `generate_json()`
  - Automatic effort level determination based on task type
  - Fallback handling if effort parameter is not supported by the API
  - Effort headers added to API requests when enabled

### 3. Updated All API Call Sites
All LLM API calls now specify appropriate `task_type` for effort level determination:

- **Example Generation** (`deepsearch_generator.py`): `task_type="generation"` → **Medium effort**
- **Rule Generation** (`deepsearch_generator.py`): `task_type="rule_generation"` → **High effort**
- **Red Team Test Cases** (`red_team_tool.py`): `task_type="test_generation"` → **Medium effort**
- **Red Team Analysis** (`red_team_tool.py`): `task_type="analysis"` → **Medium effort**
- **Overfit Detection** (`overfit_detector.py`): `task_type="overfit_detection"` → **Medium effort**
- **Boundary Mapping** (`semantic_mapper.py`): `task_type="boundary_mapping"` → **High effort**

### 4. New API Endpoint: `/effort-stats`
- **Location**: `commander/views.py` → `effort_stats()`
- **Purpose**: Returns JSON statistics on effort level usage for cost tracking
- **Response Format**:
  ```json
  {
    "total": 100,
    "breakdown": {
      "low": 20,
      "medium": 50,
      "high": 25,
      "fallback": 5
    },
    "percentages": {
      "low": 20.0,
      "medium": 50.0,
      "high": 25.0,
      "fallback": 5.0
    }
  }
  ```

## Effort Level Mapping

| Task Type | Effort Level | Use Case |
|-----------|--------------|----------|
| `validation`, `classification`, `simple_check` | **Low** | Simple yes/no, categorization tasks |
| `generation`, `analysis`, `test_generation`, `overfit_detection` | **Medium** | Content generation, moderate analysis |
| `synthesis`, `reasoning`, `boundary_mapping`, `rule_generation`, `executive_summary` | **High** | Complex reasoning, rule synthesis, boundary analysis |

## Environment Variables

### `CLAUDE_EFFORT_ENABLED`
- **Default**: `true`
- **Purpose**: Enable/disable effort parameter feature
- **Values**: `true` or `false` (as string)

### `CLAUDE_EFFORT_DEFAULT`
- **Default**: `medium`
- **Purpose**: Default effort level for unknown task types
- **Values**: `low`, `medium`, or `high`

## Cost Savings

The effort parameter provides significant cost savings:
- **Low effort**: Maximum token savings (50-80% reduction)
- **Medium effort**: Balanced performance with 76% fewer tokens than high
- **High effort**: Maximum thoroughness (no savings, full quality)

## Fallback Handling

If the effort parameter is not supported by the API (e.g., older model versions), the system:
1. Detects the error
2. Logs a warning
3. Retries the request without effort headers
4. Tracks fallback usage in statistics

## Monitoring

Access effort statistics via:
```bash
curl https://your-domain.com/effort-stats
```

Or in Python:
```python
from commander.services.effort_config import get_effort_statistics
stats = get_effort_statistics()
print(stats)
```

## Testing

To test effort level determination:
```python
from commander.services.effort_config import get_effort_level

# Should return "low"
print(get_effort_level("validation"))

# Should return "medium"
print(get_effort_level("generation"))

# Should return "high"
print(get_effort_level("synthesis"))
```

## Notes

- Effort parameter requires the `anthropic-beta-effort-2025-11-24` header
- Only works with Claude Opus 4.5 (`claude-opus-4-5-20251101`)
- Feature can be disabled via `CLAUDE_EFFORT_ENABLED=false` environment variable
- All changes are backward compatible - if effort is disabled, defaults to high effort (full quality)

