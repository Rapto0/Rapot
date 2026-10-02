import type { AlarmWrite, ServerAlarmIndicator, ServerAlarmRule, ServerAlarmSymbol } from './api/alarms-api';
import type { StoredWatchlistModel } from './watchlist-alarms';

export const SERVER_INDICATORS = {
    rsi: { label: 'RSI (14)', min: 0, max: 100, step: 0.1, dip: 30, top: 70 },
    wr: { label: 'Williams %R (14)', min: -100, max: 0, step: 0.1, dip: -80, top: -20 },
    combo: { label: 'COMBO', min: 1, max: 4, step: 1, dip: 4, top: 3 },
    hunter: { label: 'HUNTER', min: 1, max: 15, step: 1, dip: 7, top: 10 },
} as const;

export interface AlarmDraft extends Omit<AlarmWrite, 'symbols' | 'threshold'> {
    bistSymbols: string;
    cryptoSymbols: string;
    threshold: string;
}

export function emptyAlarmDraft(): AlarmDraft {
    return {
        name: '', bistSymbols: '', cryptoSymbols: '', indicator: 'rsi', timeframe: '1d',
        side: 'dip', threshold: '30', mode: 'on_enter', enabled: true, notify_telegram: false,
    };
}

export function draftForRule(rule: ServerAlarmRule): AlarmDraft {
    const { name, indicator, timeframe, side, threshold, mode, enabled, notify_telegram } = rule;
    return {
        name, indicator, timeframe, side, threshold: String(threshold), mode, enabled, notify_telegram,
        bistSymbols: rule.symbols.filter(item => item.market_type === 'BIST').map(item => item.symbol).join(', '),
        cryptoSymbols: rule.symbols.filter(item => item.market_type === 'Kripto').map(item => item.symbol).join(', '),
    };
}

function symbolText(text: string, market_type: ServerAlarmSymbol['market_type']): ServerAlarmSymbol[] {
    const normalized = text.trim().toUpperCase().split(/[\s,;]+/).filter(Boolean)
        .map(symbol => market_type === 'BIST' ? symbol.replace(/\.IS$/, '') : symbol);
    return [...new Set(normalized)].map(symbol => ({ symbol, market_type }));
}

export function alarmWriteFromDraft(draft: AlarmDraft, symbolLimit = 20): AlarmWrite {
    const name = draft.name.trim();
    if (!name || name.length > 80) throw new Error('Alarm adı 1–80 karakter olmalı.');
    const symbols = [...symbolText(draft.bistSymbols, 'BIST'), ...symbolText(draft.cryptoSymbols, 'Kripto')];
    if (!symbols.length || symbols.length > symbolLimit) throw new Error(`En az 1, en fazla ${symbolLimit} sembol girin.`);
    if (symbols.some(item => !/^[A-Z0-9]{2,20}$/.test(item.symbol))) {
        throw new Error('Sembolleri THYAO veya BTCUSDT biçiminde, boşluk veya virgülle ayırarak girin.');
    }
    if (symbols.some(item => item.market_type === 'Kripto' && !item.symbol.endsWith('USDT'))) {
        throw new Error('Kripto alarmlarında Binance Spot USDT çiftlerini kullanın (ör. BTCUSDT).');
    }
    if (draft.timeframe !== '1d' && symbols.some(item => item.market_type === 'BIST')) {
        throw new Error('BIST alarmlarında yalnız 1 gün desteklenir. 1 saat ve 4 saat yalnız kripto için desteklenir.');
    }
    const threshold = Number(draft.threshold);
    const spec = SERVER_INDICATORS[draft.indicator];
    if (!draft.threshold.trim() || !Number.isFinite(threshold) || threshold < spec.min || threshold > spec.max
        || (spec.step === 1 && !Number.isInteger(threshold))) {
        throw new Error(`${spec.label} eşiği ${spec.min}–${spec.max} aralığında${spec.step === 1 ? ' tam sayı' : ''} olmalı.`);
    }
    return {
        name, symbols, indicator: draft.indicator, timeframe: draft.timeframe, side: draft.side,
        threshold, mode: draft.mode, enabled: draft.enabled, notify_telegram: draft.notify_telegram,
    };
}

export function alarmPrefill(search: string, watchlists: StoredWatchlistModel[] = []): AlarmDraft {
    const draft = emptyAlarmDraft();
    const params = new URLSearchParams(search);
    const watchlist = watchlists.find(list => list.id === params.get('watchlist'));
    if (watchlist) {
        draft.name = watchlist.name.slice(0, 80);
        draft.bistSymbols = watchlist.rows.filter(row => row.kind === 'symbol' && row.marketType === 'BIST').map(row => row.kind === 'symbol' ? row.rawSymbol : '').join(', ');
        draft.cryptoSymbols = watchlist.rows.filter(row => row.kind === 'symbol' && row.marketType === 'Kripto').map(row => row.kind === 'symbol' ? row.rawSymbol : '').join(', ');
    } else {
        const symbol = (params.get('symbol') ?? '').trim().toUpperCase();
        if (/^[A-Z0-9]{2,20}$/.test(symbol)) {
            if (params.get('market') === 'Kripto') draft.cryptoSymbols = symbol;
            else draft.bistSymbols = symbol;
            draft.name = `${symbol} alarmı`;
        }
    }
    return draft;
}

export function alarmCondition(indicator: ServerAlarmIndicator, side: 'dip' | 'top', threshold: number | string): string {
    const score = indicator === 'combo' || indicator === 'hunter';
    return `${SERVER_INDICATORS[indicator].label} ${side === 'dip' ? 'dip' : 'tepe'} ${score || side === 'top' ? '≥' : '≤'} ${threshold}${score ? ` / ${SERVER_INDICATORS[indicator].max}` : ''}`;
}
