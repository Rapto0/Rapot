import type { ResearchCandle, ResearchField, ResearchOperation, ResearchTable } from '@/lib/api/borsapy-api';

const LABELS: Record<string, string> = {
    symbol: 'Sembol', name: 'Ad', date: 'Tarih', time: 'Mum zamanı', timestamp: 'Veri zamanı',
    open: 'Açılış', high: 'Yüksek', low: 'Düşük', close: 'Kapanış', volume: 'Hacim',
    price: 'Fiyat', last: 'Son fiyat', last_price: 'Son fiyat', change: 'Değişim',
    change_percent: 'Değişim (%)', bid: 'Alış', ask: 'Satış', market_cap: 'Piyasa değeri',
    quantity: 'Miktar', weight: 'Ağırlık', weight_pct: 'Ağırlık (%)', value: 'Değer',
    cost: 'Maliyet', profit: 'Kâr / zarar', return: 'Getiri', total_return: 'Toplam getiri',
    total_trades: 'İşlem sayısı', win_rate: 'Kazanma oranı', net_profit: 'Net kâr / zarar',
    net_profit_pct: 'Net getiri (%)', sharpe_ratio: 'Sharpe oranı', max_drawdown: 'En büyük düşüş',
    sector: 'Sektör', currency: 'Para birimi', recommendation: 'Değerlendirme',
    received_at: 'Sunucuya ulaşma', updated_at: 'Güncelleme', source: 'Kaynak',
    result: 'Sonuçlar', index: 'Tarih / kayıt', history: 'Geçmiş', holdings: 'Varlıklar',
    trades: 'İşlemler', equity_curve: 'Portföy değeri', buy_hold_curve: 'Al ve tut',
    drawdown_curve: 'Düşüş', metrics: 'Ölçümler', risk_metrics: 'Risk ölçümleri',
    current: 'Güncel değerler', url: 'Kaynak bağlantısı', link: 'Kaynak bağlantısı',
};
export function researchLabel(key: string): string {
    return LABELS[key.toLowerCase()] ?? key.split('.').map(part => LABELS[part.toLowerCase()] ?? part.replaceAll('_', ' ')).join(' · ');
}
export function researchDate(value: unknown): string {
    if (value === null || value === undefined || value === '') return 'Henüz yok';
    const date = new Date(typeof value === 'number' ? (value < 1e12 ? value * 1000 : value) : String(value));
    return Number.isFinite(date.getTime()) ? date.toLocaleString('tr-TR', { timeZone: 'Europe/Istanbul' }) : 'Bilinmiyor';
}
export function formatResearchValue(value: unknown, depth = 0): string {
    if (value === null || value === undefined || value === '') return '—';
    if (typeof value === 'number') return Number.isFinite(value) ? value.toLocaleString('tr-TR', { maximumFractionDigits: 6 }) : '—';
    if (typeof value === 'boolean') return value ? 'Evet' : 'Hayır';
    if (typeof value === 'object') {
        if (depth > 2) return 'Ayrıntılı kayıt';
        if (Array.isArray(value)) return value.map(item => formatResearchValue(item, depth + 1)).join(' · ');
        return Object.entries(value).map(([key, item]) => `${researchLabel(key)}: ${formatResearchValue(item, depth + 1)}`).join(' · ');
    }
    return String(value);
}
export function initialResearchParams(operation: ResearchOperation): Record<string, string> {
    return Object.fromEntries(operation.fields.map(field => [field.name, field.default === undefined || field.default === null ? '' : typeof field.default === 'object' ? JSON.stringify(field.default) : String(field.default)]));
}
export function researchParams(fields: ResearchField[], draft: Record<string, string>): Record<string, unknown> {
    const result: Record<string, unknown> = {};
    for (const field of fields) {
        const raw = (draft[field.name] ?? '').trim();
        if (!raw) {
            if (field.required) throw new Error(`${field.label} alanını doldurun.`);
            continue;
        }
        if (field.type === 'number') {
            const value = Number(raw);
            if (!Number.isFinite(value) || (field.min !== undefined && value < field.min) || (field.max !== undefined && value > field.max)) throw new Error(`${field.label} için geçerli bir sayı girin.`);
            result[field.name] = value;
        } else {
            if (field.type === 'select' && field.options && !field.options.some(option => option.value === raw)) throw new Error(`${field.label} için listeden seçim yapın.`);
            result[field.name] = raw;
        }
    }
    return result;
}
export function researchCsv(table: ResearchTable): string {
    const escape = (value: unknown) => {
        const raw = value === null || value === undefined ? '' : typeof value === 'object' ? formatResearchValue(value) : String(value);
        // CSV is also opened in spreadsheets: provider text must never become a formula.
        const safe = /^[\s]*[=+@-]/.test(raw) && typeof value !== 'number' ? `'${raw}` : raw;
        return `"${safe.replaceAll('"', '""')}"`;
    };
    return '\uFEFF' + [table.columns.map(escape).join(','), ...table.rows.map(row => table.columns.map(column => escape(row[column])).join(','))].join('\r\n');
}
export function validResearchCandles(candles: ResearchCandle[]): ResearchCandle[] {
    const byTime = new Map<number, ResearchCandle>();
    for (const candle of candles) {
        if (![candle.time, candle.open, candle.high, candle.low, candle.close].every(Number.isFinite) || !Number.isInteger(candle.time) || candle.time <= 0 || candle.time > 32_503_680_000 || candle.low <= 0 || candle.high < Math.max(candle.open, candle.close, candle.low) || candle.low > Math.min(candle.open, candle.close)) continue;
        if (candle.volume !== undefined && candle.volume !== null && (!Number.isFinite(candle.volume) || candle.volume < 0)) continue;
        byTime.set(candle.time, candle);
    }
    return [...byTime.values()].sort((a, b) => a.time - b.time);
}
export function researchLink(value: unknown): string | null {
    if (typeof value !== 'string' || !/^https?:\/\//i.test(value)) return null;
    try {
        const url = new URL(value);
        return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
    } catch { return null; }
}
export function researchSeries(table: ResearchTable): { timeColumn: string; valueColumns: string[]; points: Record<string, number>[] } | null {
    const timeColumn = table.columns.find(column => /^(date|datetime|timestamp|time|index)$/i.test(column));
    if (!timeColumn) return null;
    const valueColumns = table.columns.filter(column => column !== timeColumn && table.rows.some(row => typeof row[column] === 'number' && Number.isFinite(row[column])));
    if (!valueColumns.length) return null;
    const byTime = new Map<number, Record<string, number>>();
    for (const row of table.rows) {
        const raw = row[timeColumn];
        let time = NaN;
        if (typeof raw === 'string' && /^\d{4}-\d{2}-\d{2}/.test(raw)) time = Date.parse(raw) / 1000;
        else if (typeof raw === 'number' && timeColumn.toLowerCase() !== 'index') time = raw > 1e12 ? raw / 1000 : raw;
        if (!Number.isFinite(time) || time <= 0 || time > 32_503_680_000) continue;
        const point: Record<string, number> = { time };
        for (const column of valueColumns) if (typeof row[column] === 'number' && Number.isFinite(row[column])) point[column] = row[column];
        byTime.set(time, point);
    }
    const points = [...byTime.values()].sort((left, right) => left.time - right.time);
    return points.length > 1 ? { timeColumn, valueColumns, points } : null;
}
const PERIOD_DAYS: Record<string, number> = { '1d': 1, '5d': 5, '1mo': 31, '3mo': 93, '6mo': 186, '1y': 366, '2y': 732 };
const INTERVAL_MAX: Record<string, number> = { '1m': 5, '5m': 31, '15m': 93, '30m': 186, '1h': 186, '4h': 186 };
export function availableResearchPeriods(fields: ResearchField[], interval: string): { value: string; label: string }[] {
    const options = fields.find(field => field.name === 'period')?.options ?? [];
    const maximum = INTERVAL_MAX[interval];
    return options.filter(option => !maximum || (PERIOD_DAYS[option.value] ?? Infinity) <= maximum);
}
export function changeResearchParam(fields: ResearchField[], draft: Record<string, string>, name: string, value: string): Record<string, string> {
    const next = { ...draft, [name]: value };
    if (name === 'interval' && fields.some(field => field.name === 'period')) {
        const allowed = availableResearchPeriods(fields, value);
        if (allowed.length && !allowed.some(option => option.value === next.period)) next.period = allowed.at(-1)!.value;
    }
    return next;
}
export function researchOptionLabel(field: ResearchField, value: string, label: string): string {
    if (label !== value) return label;
    if (field.name === 'period') return ({ '1d': '1 gün', '3d': '3 gün', '5d': '5 gün', '7d': '7 gün', '1w': '1 hafta', '1mo': '1 ay', '3mo': '3 ay', '6mo': '6 ay', '1y': '1 yıl', '2y': '2 yıl' })[value] ?? label;
    if (field.name === 'interval') return ({ '1m': '1 dakika', '5m': '5 dakika', '15m': '15 dakika', '30m': '30 dakika', '1h': '1 saat', '4h': '4 saat', '1d': '1 gün', '1wk': '1 hafta' })[value] ?? label;
    const translated: Record<string, string> = {
        all: 'Tümü', bist: 'BIST', crypto: 'Kripto', forex: 'Döviz', index: 'Endeks', viop: 'VİOP',
        annual: 'Yıllık', quarterly: 'Çeyreklik', monthly: 'Aylık', weekly: 'Haftalık', daily: 'Günlük',
        balance_sheet: 'Bilanço', income_stmt: 'Gelir tablosu', cashflow: 'Nakit akış',
        low_pe: 'Düşük F/K', high_dividend: 'Yüksek temettü', high_roe: 'Yüksek özsermaye getirisi',
        high_net_margin: 'Yüksek net kâr marjı', small_cap: 'Küçük piyasa değeri', mid_cap: 'Orta piyasa değeri',
        large_cap: 'Büyük piyasa değeri', high_upside: 'Yüksek hedef potansiyeli', high_volume: 'Yüksek hacim',
        buy_recommendation: 'AL tavsiyesi', rsi_below_30: 'RSI 30 altında', rsi_above_70: 'RSI 70 üstünde',
        close_above_sma50: 'Fiyat SMA50 üzerinde', sma20_crosses_sma50: 'SMA20, SMA50’yi yukarı keser',
        macd_above_signal: 'MACD sinyal üzerinde', YAT: 'Yatırım fonu', EMK: 'Emeklilik fonu',
        tufe: 'TÜFE', ufe: 'ÜFE', policy: 'Politika faizi', overnight: 'Gecelik faiz', late_liquidity: 'Geç likidite',
        futures: 'Tüm vadeli kontratlar', stock_futures: 'Hisse vadeli', index_futures: 'Endeks vadeli',
        currency_futures: 'Döviz vadeli', commodity_futures: 'Emtia vadeli', options: 'Tüm opsiyonlar',
        stock_options: 'Hisse opsiyonları', index_options: 'Endeks opsiyonları',
        low: 'Düşük', mid: 'Orta', high: 'Yüksek', TR: 'Türkiye', US: 'ABD', EU: 'Avro Bölgesi',
        DE: 'Almanya', GB: 'Birleşik Krallık', JP: 'Japonya', CN: 'Çin', bollinger: 'Bollinger bantları',
        stochastic: 'Stokastik', supertrend: 'Supertrend', tilson_t3: 'Tilson T3',
    };
    return translated[value] ?? (field.name === 'indicator' ? value.toUpperCase() : label);
}
export interface StudyInputRow { name: string; type: 'number' | 'text' | 'boolean'; value: string }
export function studyInputValues(rows: StudyInputRow[]): Record<string, string | number | boolean> {
    if (rows.length > 16) throw new Error('En fazla 16 gösterge parametresi ekleyebilirsiniz.');
    const result: Record<string, string | number | boolean> = {};
    for (const row of rows) {
        const name = row.name.trim();
        if (!/^[A-Za-z_][A-Za-z0-9_]{0,39}$/.test(name) || ['__proto__', 'constructor', 'prototype'].includes(name) || Object.hasOwn(result, name)) throw new Error('Parametre adları benzersiz olmalı; yalnız harf, rakam ve alt çizgi kullanın.');
        if (row.type === 'number') {
            const number = Number(row.value);
            if (!row.value.trim() || !Number.isFinite(number) || Math.abs(number) > 1e7) throw new Error('Gösterge parametresi −10.000.000 ile 10.000.000 arasında sonlu bir sayı olmalı.');
            result[name] = number;
        } else {
            if (row.type === 'text' && row.value.length > 80) throw new Error('Metin parametresi en fazla 80 karakter olabilir.');
            result[name] = row.type === 'boolean' ? row.value === 'true' : row.value;
        }
    }
    return result;
}
export function researchError(cause: unknown): string {
    const status = typeof cause === 'object' && cause !== null && 'status' in cause ? cause.status : null;
    if (status === 401) return 'Oturumunuz sona erdi. Yeniden giriş yapın.';
    if (status === 403) return 'Bu işlem için yönetici yetkisi gerekiyor.';
    if (status === 409) return 'Sağlayıcı oturumu doğrulanamadı. Bağlantılar bölümünden oturumu kontrol edin.';
    if (status === 422 || status === 400) return 'İstek kabul edilmedi. Alanları ve işlem açıklamasını kontrol edin.';
    if (status === 429) return 'İstek sınırına ulaşıldı. Bir süre bekleyip yeniden deneyin.';
    return 'İşlem tamamlanamadı. Bağlantı durumunu kontrol edip yeniden deneyin.';
}
