import { fetchAdvancedEvents, type AdvancedAlarmEvent } from "@/lib/api/advanced-alarms-api"

export const ALARM_EVENT_POLL_MS = 5_000

const EVENT_LIMIT = 100
const DELIVERY_REFRESH_MS = 30_000
const SNAPSHOT_REFRESH_MS = 60_000

export interface AdvancedAlarmEventFeed {
    events: AdvancedAlarmEvent[]
    nextAfterId: number
    snapshotAt: number
}

export async function readAdvancedAlarmEventFeed(
    previous: AdvancedAlarmEventFeed | undefined,
    signal: AbortSignal,
    now = Date.now(),
): Promise<AdvancedAlarmEventFeed> {
    const hasUndeliveredEvent = previous?.events.some(event => event.delivery_status === "pending" || event.delivery_status === "sending")
    const snapshotInterval = hasUndeliveredEvent ? DELIVERY_REFRESH_MS : SNAPSHOT_REFRESH_MS

    if (previous && now - previous.snapshotAt < snapshotInterval) {
        const update = await fetchAdvancedEvents(previous.nextAfterId, signal)
        if (!update.has_more) {
            if (update.events.length === 0) return previous

            const byId = new Map(previous.events.map(event => [event.id, event]))
            for (const event of update.events) byId.set(event.id, event)
            return {
                events: [...byId.values()].sort((left, right) => right.id - left.id).slice(0, EVENT_LIMIT),
                nextAfterId: update.next_after_id,
                snapshotAt: previous.snapshotAt,
            }
        }
        // Only the newest 100 are displayed. Recover in one snapshot after a burst.
    }

    const snapshot = await fetchAdvancedEvents(undefined, signal)
    return { events: snapshot.events, nextAfterId: snapshot.next_after_id, snapshotAt: now }
}
