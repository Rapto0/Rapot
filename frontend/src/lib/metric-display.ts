/** Missing measurements have no numerical value or profit/loss implication. */
export function metricTone(value: number | null | undefined, threshold = 0): 'profit' | 'loss' | 'neutral' {
    return value == null || !Number.isFinite(value) ? 'neutral' : value >= threshold ? 'profit' : 'loss';
}

export function metricTextClass(value: number | null | undefined): string {
    return { profit: 'text-profit', loss: 'text-loss', neutral: 'text-muted-foreground' }[metricTone(value)];
}

export function formatMetric(value: number | null | undefined, decimals = 2, signed = false): string {
    if (value == null || !Number.isFinite(value)) return '—';
    return `${signed && value >= 0 ? '+' : ''}${value.toLocaleString('tr-TR', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    })}`;
}

export function formatMetricPercent(value: number | null | undefined, decimals = 2, signed = false): string {
    const formatted = formatMetric(value, decimals, signed);
    return formatted === '—' ? formatted : `${formatted}%`;
}

export function formatTradePrice(value: number | null | undefined, marketType: string, decimals = 2): string {
    const formatted = formatMetric(value, decimals);
    return formatted === '—' ? formatted : `${marketType === 'Kripto' ? '$' : '₺'}${formatted}`;
}
