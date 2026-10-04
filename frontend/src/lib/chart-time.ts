import type { TickMarkType, Time } from 'lightweight-charts';

export type ChartTimeZone = 'Europe/Istanbul' | 'UTC';

export const chartTimeZone = (market: string): ChartTimeZone =>
    market === 'BIST' ? 'Europe/Istanbul' : 'UTC';

function displayDate(time: unknown): { date: Date; calendarDay: boolean } | null {
    let calendarDay = false;
    let milliseconds: number;
    if (typeof time === 'number') {
        milliseconds = time * 1000;
    } else if (typeof time === 'string') {
        const value = time.trim();
        calendarDay = /^\d{4}-\d{2}-\d{2}$/.test(value);
        if (calendarDay) milliseconds = Date.parse(`${value}T00:00:00Z`);
        else if (/^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?$/.test(value)) {
            // Legacy timezone-free crypto values are UTC, independent of the browser host.
            milliseconds = Date.parse(`${value.replace(' ', 'T')}Z`);
        } else if (/T.*(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)) milliseconds = Date.parse(value);
        else return null;
    } else if (time && typeof time === 'object' && 'year' in time && 'month' in time && 'day' in time) {
        const { year, month, day } = time;
        if (![year, month, day].every(value => typeof value === 'number' && Number.isInteger(value))) return null;
        milliseconds = Date.UTC(year as number, (month as number) - 1, day as number);
        calendarDay = true;
    } else return null;
    const date = new Date(milliseconds);
    return Number.isFinite(date.getTime()) ? { date, calendarDay } : null;
}

/** Display only: never add an offset to candle, marker, worker or drawing timestamps. */
export function createChartTimeFormatters(timeZone: ChartTimeZone) {
    const create = (options: Intl.DateTimeFormatOptions, calendarDay = false) =>
        new Intl.DateTimeFormat('tr-TR', { ...options, timeZone: calendarDay ? 'UTC' : timeZone, hourCycle: 'h23' });
    const date = { year: '2-digit', month: 'short', day: '2-digit' } as const;
    const fullTime = create({ ...date, hour: '2-digit', minute: '2-digit' });
    const dayOnly = create(date, true);
    const tickOptions: Intl.DateTimeFormatOptions[] = [
        { year: 'numeric' },
        { month: 'short' },
        { day: '2-digit' },
        { hour: '2-digit', minute: '2-digit' },
        { hour: '2-digit', minute: '2-digit', second: '2-digit' },
    ];
    // Lightweight Charts v5 TickMarkType: Year=0, Month=1, DayOfMonth=2, Time=3, TimeWithSeconds=4.
    const ticks = tickOptions.map(options => create(options));
    const calendarTicks = tickOptions.map(options => create(options, true));
    return {
        timeZone,
        label: timeZone === 'Europe/Istanbul' ? 'Türkiye saati (UTC+3)' : 'UTC',
        timeFormatter(time: unknown): string {
            const value = displayDate(time);
            return value ? (value.calendarDay ? dayOnly : fullTime).format(value.date) : '';
        },
        tickMarkFormatter(time: Time, type: TickMarkType): string {
            const value = displayDate(time);
            if (!value) return '';
            if (value.calendarDay && type >= 3) return dayOnly.format(value.date);
            return (value.calendarDay ? calendarTicks : ticks)[type]?.format(value.date) ?? '';
        },
    };
}
