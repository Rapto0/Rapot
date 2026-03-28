"""
Centralized state/stat keys used across scheduler, scanners, health, and ops layers.
"""

# Scanner counters
SYNC_SCAN_COUNT_KEY = "sync_scan_count"
SYNC_SIGNAL_COUNT_KEY = "sync_signal_count"
ASYNC_SCAN_COUNT_KEY = "async_scan_count"
ASYNC_SIGNAL_COUNT_KEY = "async_signal_count"

# Distributed lock keys
SCHEDULED_SCAN_LOCK_NAME = "scheduled_scan"

# Runtime state keys persisted in bot_stats
RUNTIME_IS_RUNNING_KEY = "runtime_is_running"
RUNTIME_IS_SCANNING_KEY = "runtime_is_scanning"
RUNTIME_LAST_SCAN_TIME_KEY = "runtime_last_scan_time"
RUNTIME_ERROR_COUNT_KEY = "runtime_error_count"
RUNTIME_LAST_ERROR_KEY = "runtime_last_error"

# Health state keys
SPECIAL_TAG_HEALTH_STATE_KEY = "special_tag_health_state"
SPECIAL_TAG_HEALTH_SUMMARY_KEY = "special_tag_health_summary"
