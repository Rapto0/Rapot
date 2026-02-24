import { useState, useEffect } from 'react';

export interface CandlestickData {
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
}

export function useChartData(symbol: string = 'BTC/USDT') {
    const [data, setData] = useState<CandlestickData[]>([]);

    // İlk yükleme için geçmiş veri oluştur
    useEffect(() => {
        const generateData = () => {
            const initialData: CandlestickData[] = [];
            let time = Math.floor(Date.now() / 1000) - (1000 * 60 * 60); // 1000 mum geriden başla
            let price = 42000;

            for (let i = 0; i < 1000; i++) {
                const volatility = 0.002; // %0.2 oynaklık
                const change = price * volatility * (Math.random() - 0.5);
                const open = price;
                const close = price + change;
                const high = Math.max(open, close) + Math.abs(change) * Math.random();
                const low = Math.min(open, close) - Math.abs(change) * Math.random();

                initialData.push({
                    time,
                    open,
                    high,
                    low,
                    close,
                });

                price = close;
                time += 60; // 1 dakikalık mumlar
            }
            return initialData;
        };

        setData(generateData());
    }, [symbol]);

    // Canlı veri simülasyonu (WebSocket yerine geçici)
    useEffect(() => {
        if (data.length === 0) return;

        const interval = setInterval(() => {
            setData(currentData => {
                const lastCandle = currentData[currentData.length - 1];
                const lastTime = lastCandle.time;
                const currentTime = Math.floor(Date.now() / 1000);

                // Yeni mum mu, yoksa mevcut mumu güncelleme mi?
                if (currentTime - lastTime >= 60) {
                    // Yeni mum
                    const open = lastCandle.close;
                    const change = open * 0.001 * (Math.random() - 0.5);
                    const close = open + change;
                    const high = Math.max(open, close) + Math.abs(change) * Math.random();
                    const low = Math.min(open, close) - Math.abs(change) * Math.random();

                    return [...currentData, {
                        time: currentTime,
                        open,
                        high,
                        low,
                        close
                    }];
                } else {
                    // Mevcut mumu güncelle (Canlı fiyat efekti)
                    const updatedLast = { ...lastCandle };
                    const change = updatedLast.close * 0.0005 * (Math.random() - 0.5);
                    updatedLast.close += change;
                    updatedLast.high = Math.max(updatedLast.high, updatedLast.close);
                    updatedLast.low = Math.min(updatedLast.low, updatedLast.close);

                    return [...currentData.slice(0, -1), updatedLast];
                }
            });
        }, 1000); // Her saniye güncelle

        return () => clearInterval(interval);
    }, [data.length]);

    return { data };
}
