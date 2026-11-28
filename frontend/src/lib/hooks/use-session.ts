'use client';

import { useSyncExternalStore } from 'react';
import { getSession, getSessionChecked, subscribeSession } from '../auth/session';

export function useSession() {
    return useSyncExternalStore(subscribeSession, getSession, () => null);
}

export function useSessionChecked() {
    return useSyncExternalStore(subscribeSession, getSessionChecked, () => false);
}
