export interface TickerPrice {
    price: number
    change: number | null
    priceChange: number | null
}

export type BinanceTickerStatus = "connecting" | "connected" | "reconnecting" | "offline" | "paused"

interface TickerRecord {
    price: TickerPrice
    receivedAt: number
    sourceTime: number | null
    latestSourceTime: number | null
    generation: number
}

export interface TickerSnapshot {
    prices: Record<string, TickerPrice>
    receivedAtBySymbol: Record<string, number>
    sourceTimeBySymbol: Record<string, number>
    liveBySymbol: Record<string, boolean>
    status: BinanceTickerStatus
}

interface Interest {
    symbols: ReadonlySet<string>
    notify: (symbol?: string) => void
}

const MAX_STREAMS = 1024
const RETAIN_MS = 120_000
const CONTROL_INTERVAL_MS = 400

function isRecord(value: unknown): value is Record<string, unknown> {
    return value !== null && typeof value === "object" && !Array.isArray(value)
}

function numericField(value: unknown): number | null {
    if (typeof value === "string") {
        if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(value.trim())) return null
        value = Number(value)
    }
    return typeof value === "number" && Number.isFinite(value) ? value : null
}

export function emptyTickerSnapshot(status: BinanceTickerStatus): TickerSnapshot {
    return { prices: {}, receivedAtBySymbol: {}, sourceTimeBySymbol: {}, liveBySymbol: {}, status }
}

export class BinanceTickerFeed {
    private readonly interests = new Set<Interest>()
    private readonly quotes = new Map<string, TickerRecord>()
    private desired = new Set<string>()
    private subscribed = new Set<string>()
    private socket: WebSocket | null = null
    private status: BinanceTickerStatus = "connecting"
    private generation = 0
    private retryDelay = 1000
    private lastManual = -Infinity
    private lastControl = -Infinity
    private controlFailures = 0
    private nextId = 0
    private pending: { id: number; symbols: string[]; add: boolean } | null = null
    private readonly timers: Partial<Record<"idle" | "retry" | "open" | "control" | "ack", number>> = {}

    read(symbols: ReadonlySet<string>, now = Date.now()): TickerSnapshot {
        const snapshot = emptyTickerSnapshot(this.status)
        for (const symbol of symbols) {
            const quote = this.quotes.get(symbol)
            if (!quote || now - quote.receivedAt > RETAIN_MS) continue
            snapshot.prices[symbol] = quote.price
            snapshot.receivedAtBySymbol[symbol] = quote.receivedAt
            if (quote.sourceTime !== null) snapshot.sourceTimeBySymbol[symbol] = quote.sourceTime
            snapshot.liveBySymbol[symbol] = this.status === "connected" && this.hasStream(symbol)
                && quote.generation === this.generation
        }
        return snapshot
    }

    watch(interest: Interest) {
        if (!this.interests.size) {
            window.addEventListener("offline", this.offline)
            window.addEventListener("online", this.online)
        }
        this.clear("idle")
        this.interests.add(interest)
        this.sync()
        return () => {
            if (!this.interests.delete(interest)) return
            this.sync()
            if (!this.interests.size) {
                window.removeEventListener("offline", this.offline)
                window.removeEventListener("online", this.online)
            }
        }
    }

    reset() {
        this.interests.clear()
        this.desired.clear()
        this.quotes.clear()
        this.clear("idle")
        this.clear("retry")
        this.retire()
        this.status = "connecting"
        this.retryDelay = 1000
        this.controlFailures = 0
        this.lastManual = -Infinity
        window.removeEventListener("offline", this.offline)
        window.removeEventListener("online", this.online)
    }

    reconnect() {
        const now = Date.now()
        if (!this.desired.size || window.navigator.onLine === false || now - this.lastManual < 1000) return
        this.lastManual = now
        this.clear("retry")
        this.retire()
        this.retryDelay = 1000
        this.connect(true)
    }

    private clear(name: keyof BinanceTickerFeed["timers"]) {
        const timer = this.timers[name]
        if (timer !== undefined) window.clearTimeout(timer)
        delete this.timers[name]
    }

    private after(name: keyof BinanceTickerFeed["timers"], ms: number, action: () => void) {
        this.clear(name)
        const timer = window.setTimeout(() => {
            if (this.timers[name] !== timer) return
            delete this.timers[name]
            action()
        }, ms)
        this.timers[name] = timer
    }

    private notify(symbol?: string) {
        for (const interest of this.interests) {
            if (symbol === undefined || interest.symbols.has(symbol)) interest.notify(symbol)
        }
    }

    private hasStream(symbol: string) {
        return this.subscribed.has(symbol) || (this.pending?.add === true && this.pending.symbols.includes(symbol))
    }

    private setStatus(status: BinanceTickerStatus) {
        if (status === this.status) return
        this.status = status
        this.notify()
    }

    private sync() {
        const symbols = new Set<string>()
        for (const interest of this.interests) {
            for (const symbol of interest.symbols) symbols.add(symbol)
        }
        this.desired = new Set([...symbols].slice(0, MAX_STREAMS))
        if (!this.desired.size) {
            this.clear("retry")
            this.clear("control")
            if (this.socket) this.after("idle", 1500, () => {
                this.retire()
                this.status = "connecting"
            })
            return
        }
        if (window.navigator.onLine === false) this.offline()
        else if (!this.socket && this.timers.retry === undefined) this.connect()
        else this.reconcile()
    }

    private retire() {
        this.generation++
        this.clear("ack")
        this.clear("open")
        this.clear("control")
        this.pending = null
        this.subscribed.clear()
        const socket = this.socket
        this.socket = null
        if (!socket) return
        socket.onopen = socket.onmessage = socket.onerror = socket.onclose = null
        if (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN) {
            socket.close(1000, "Ticker connection retired")
        }
    }

    private retry() {
        if (!this.desired.size) return
        if (window.navigator.onLine === false) { this.setStatus("offline"); return }
        this.setStatus("reconnecting")
        const controlDelay = this.controlFailures ? Math.min(2000 * 2 ** (this.controlFailures - 1), 10_000) : 0
        this.after("retry", Math.max(this.retryDelay, controlDelay), () => this.connect(true))
        this.retryDelay = Math.min(this.retryDelay * 2, 10_000)
    }

    private disconnect(socket: WebSocket, controlFailure = false) {
        if (this.socket !== socket) return
        if (controlFailure) this.controlFailures++
        this.retire()
        this.retry()
    }

    private readonly offline = () => {
        this.clear("retry")
        this.retire()
        this.setStatus("offline")
    }

    private readonly online = () => {
        if (this.desired.size && !this.socket && this.timers.retry === undefined) this.connect(true)
    }

    private connect(retrying = false) {
        if (window.navigator.onLine === false) { this.setStatus("offline"); return }
        this.setStatus(retrying ? "reconnecting" : "connecting")
        const start = [...this.desired].slice(0, 50)
        const streams = start.map(symbol => `${symbol.toLowerCase()}@ticker`)
        const url = streams.length === 1 ? `/ws/${streams[0]}` : `/stream?streams=${streams.join("/")}`
        let socket: WebSocket
        try {
            socket = new WebSocket(`wss://stream.binance.com:9443${url}`)
        } catch {
            this.retry()
            return
        }
        this.socket = socket
        const disconnected = () => this.disconnect(socket)
        socket.onopen = () => {
            if (this.socket !== socket) return
            this.clear("open")
            this.retryDelay = 1000
            this.lastControl = -Infinity
            this.subscribed = new Set(start)
            this.setStatus("connected")
            this.reconcile()
        }
        socket.onmessage = event => {
            if (this.socket !== socket || typeof event.data !== "string") return
            this.receive(socket, event.data)
        }
        socket.onerror = disconnected
        socket.onclose = disconnected
        this.after("open", 20_000, disconnected)
    }

    private reconcile() {
        const socket = this.socket
        if (!this.desired.size || !socket || socket.readyState !== WebSocket.OPEN || this.pending) return
        const removed = [...this.subscribed].filter(symbol => !this.desired.has(symbol))
        const add = removed.length === 0
        const symbols = add ? [...this.desired].filter(symbol => !this.subscribed.has(symbol)) : removed
        if (!symbols.length) return
        const wait = this.lastControl + CONTROL_INTERVAL_MS - Date.now()
        if (wait > 0) { this.after("control", wait, () => this.reconcile()); return }
        const id = ++this.nextId
        this.pending = { id, symbols, add }
        this.lastControl = Date.now()
        const fail = () => this.disconnect(socket, true)
        this.after("ack", 8000, fail)
        try {
            socket.send(JSON.stringify({ id, method: add ? "SUBSCRIBE" : "UNSUBSCRIBE",
                params: symbols.map(symbol => `${symbol.toLowerCase()}@ticker`) }))
        } catch {
            this.clear("ack")
            fail()
        }
    }

    private receive(socket: WebSocket, raw: string) {
        let message: unknown
        try { message = JSON.parse(raw) } catch { return }
        if (!isRecord(message)) return
        const command = this.pending
        if (command && message.id === command.id) {
            this.clear("ack")
            this.pending = null
            if (message.result !== null) { this.disconnect(socket, true); return }
            this.controlFailures = 0
            for (const symbol of command.symbols) {
                if (command.add) this.subscribed.add(symbol)
                else {
                    this.subscribed.delete(symbol)
                    const quote = this.quotes.get(symbol)
                    if (quote) quote.generation = -1
                }
            }
            this.reconcile()
            return
        }
        const ticker = "data" in message ? message.data : message
        if (!isRecord(ticker)) return
        if (ticker.e === "serverShutdown") { this.disconnect(socket); return }
        if (typeof ticker.s !== "string") return
        const symbol = ticker.s.toUpperCase()
        if (!this.desired.has(symbol) || !this.hasStream(symbol)) return
        const price = numericField(ticker.c)
        if (price === null || price <= 0) return
        const sourceTime = typeof ticker.E === "number" && Number.isSafeInteger(ticker.E)
            && ticker.E > 0 && ticker.E < 8.64e15 ? ticker.E : null
        const previous = this.quotes.get(symbol)
        if (sourceTime !== null && previous?.latestSourceTime != null && sourceTime < previous.latestSourceTime) return
        this.quotes.delete(symbol)
        this.quotes.set(symbol, {
            price: { price, change: numericField(ticker.P), priceChange: numericField(ticker.p) },
            receivedAt: Date.now(), sourceTime,
            latestSourceTime: sourceTime ?? previous?.latestSourceTime ?? null, generation: this.generation,
        })
        if (this.quotes.size > MAX_STREAMS) this.quotes.delete(this.quotes.keys().next().value!)
        this.notify(symbol)
    }
}
