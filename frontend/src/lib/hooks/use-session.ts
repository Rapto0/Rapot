'use client';

import { useSyncExternalStore } from 'react';
import { getSession, subscribeSession } from '../auth/session';

export function useSession() {
    return useSyncExternalStore(subscribeSession, getSession, () => null);
}
