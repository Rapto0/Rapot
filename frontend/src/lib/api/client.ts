/**
 * Backward-compatible API surface.
 * Domain-specific implementations live under `signals-api`, `market-api`, `ops-api`, and `analysis-api`.
 */

export * from './types';
export * from './signals-api';
export * from './market-api';
export * from './ops-api';
export * from './analysis-api';
export {
    transformAnalysis,
    transformOpsOverviewReadModel,
    transformSignal,
    transformStats,
    transformTrade,
} from './normalizers';
