import type { SignalData } from './types';

/** REST can contain enrichment saved after an initial websocket event. */
export function mergeSignals(rest: SignalData[], realtime: SignalData[]): SignalData[] {
  const byId = new Map(realtime.map((signal) => [signal.id, signal]));
  for (const signal of rest) byId.set(signal.id, signal);
  return Array.from(byId.values());
}
