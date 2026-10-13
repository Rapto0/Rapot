/**
 * Backward-compatible API surface.
 * Domain-specific implementations live under `trades-api`, `market-api`, `ops-api`, and `analysis-api`.
 */

export * from './types';
export * from './trades-api';
export * from './market-api';
export * from './ops-api';
export * from './analysis-api';
export {
    transformAnalysis,
    transformStats,
    transformTrade,
} from './normalizers';
