/** Remove obsolete connection fields without touching other browser preferences. */
const LEGACY_SETTINGS_KEYS = ['rapot.settings.v1', 'rapot-settings'] as const;
const LEGACY_NUMBER_FIELDS = ['rsiOversold', 'rsiOverbought', 'hunterMinScore', 'scanInterval'] as const;

type SettingsStorage = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>;

export interface LegacySettingsCleanupResult {
  status: 'complete' | 'blocked';
  failedKeys: string[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function retainedLegacyValues(value: unknown): Record<string, number | boolean> {
  const retained: Record<string, number | boolean> = {};
  if (!isRecord(value)) return retained;
  for (const field of LEGACY_NUMBER_FIELDS) {
    if (typeof value[field] === 'number' && Number.isFinite(value[field])) retained[field] = value[field];
  }
  if (typeof value.notifications === 'boolean') retained.notifications = value.notifications;
  return retained;
}

/**
 * These values are only an inert legacy record. Nothing hydrates them into bot
 * configuration or active UI settings. Repeated startup calls are idempotent.
 */
export function cleanupLegacyBrowserSettings(storage?: SettingsStorage): LegacySettingsCleanupResult {
  let target: SettingsStorage;
  try {
    target = storage ?? window.localStorage;
  } catch {
    return { status: 'blocked', failedKeys: [...LEGACY_SETTINGS_KEYS] };
  }

  const failedKeys: string[] = [];
  for (const key of LEGACY_SETTINGS_KEYS) {
    try {
      const raw = target.getItem(key);
      if (raw === null) continue;
      let parsed: unknown;
      try {
        parsed = JSON.parse(raw);
      } catch {
        parsed = null;
      }
      const values = retainedLegacyValues(key === 'rapot-settings' && isRecord(parsed) ? parsed.state : parsed);
      if (Object.keys(values).length === 0) {
        target.removeItem(key);
        continue;
      }
      const sanitized = JSON.stringify(key === 'rapot-settings' ? {
        state: values,
        version: isRecord(parsed) && Number.isSafeInteger(parsed.version) && Number(parsed.version) >= 0 ? parsed.version : 0,
      } : values);
      if (sanitized !== raw) target.setItem(key, sanitized);
    } catch {
      // Never include stored values or browser exception messages in diagnostics.
      failedKeys.push(key);
    }
  }
  return { status: failedKeys.length ? 'blocked' : 'complete', failedKeys };
}
