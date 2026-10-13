import type { CustomInputs } from "./api/custom-indicators-api"

export interface CustomIndicatorPreset {
    indicator: string
    inputs: CustomInputs
    timeframe: string
    symbol: string
    market_type: "BIST" | "Kripto"
}
interface StoredPreset { version: 1; identity: string; createdAt: number; preset: CustomIndicatorPreset }
const PREFIX = "rapot.custom-preset.v1:"
const TTL = 30 * 60_000
const MAX_BYTES = 5000
const IDS = new Set(["htf_rsi_score", "rsi_snapshot", "rsi_votes", "smi_votes", "rmi_votes"])
const validToken = (token: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(token)

function decode(raw: string | null, identity: string, now: number): StoredPreset | null {
    if (!raw || new TextEncoder().encode(raw).byteLength > MAX_BYTES) return null
    try {
        const value = JSON.parse(raw) as StoredPreset
        const preset = value.preset
        if (value.version !== 1 || value.identity !== identity || !Number.isFinite(value.createdAt) || value.createdAt > now || now - value.createdAt > TTL || !preset || !IDS.has(preset.indicator)) return null
        if (typeof preset.symbol !== "string" || !/^[A-Z0-9]{1,32}$/.test(preset.symbol) || !["BIST", "Kripto"].includes(preset.market_type) || typeof preset.timeframe !== "string" || !/^[A-Za-z0-9]{1,10}$/.test(preset.timeframe)) return null
        if (!preset.inputs || typeof preset.inputs !== "object" || Array.isArray(preset.inputs) || Object.keys(preset.inputs).length > 100) return null
        if (Object.entries(preset.inputs).some(([key, item]) => !/^[a-zA-Z][a-zA-Z0-9_]*$/.test(key) || ["__proto__", "constructor", "prototype"].includes(key) || !(typeof item === "boolean" || typeof item === "number" && Number.isFinite(item) || typeof item === "string" && item.length <= 40))) return null
        return value
    } catch { return null }
}

export function storeCustomIndicatorPreset(preset: CustomIndicatorPreset, identity: string): string {
    const now = Date.now()
    const raw = JSON.stringify({ version: 1, identity, createdAt: now, preset })
    if (!decode(raw, identity, now)) throw new Error("Gösterge ayarları alarm taslağına aktarılamadı; ayarları tekrar uygulayın.")
    try {
        const token = crypto.randomUUID()
        const storage = window.sessionStorage
        storage.setItem(`${PREFIX}${token}`, raw)
        const saved: Array<{ key: string; createdAt: number }> = []
        for (let index = 0; index < storage.length; index++) {
            const key = storage.key(index)
            if (!key?.startsWith(PREFIX)) continue
            try {
                const value = JSON.parse(storage.getItem(key) ?? "null") as StoredPreset | null
                if (value?.identity === identity && key !== `${PREFIX}${token}`) saved.push({ key, createdAt: Number.isFinite(value.createdAt) ? value.createdAt : 0 })
            } catch { /* Unrecognized storage belongs to no proven identity. */ }
        }
        saved.sort((a, b) => b.createdAt - a.createdAt)
        for (const old of saved.slice(4)) storage.removeItem(old.key)
        return token
    } catch { throw new Error("Tarayıcı alarm taslağını saklayamadı. Bu sekmenin depolama iznini kontrol edin.") }
}

export function consumeCustomIndicatorPreset(token: string, identity: string): CustomIndicatorPreset | null {
    if (!validToken(token)) return null
    try {
        const key = `${PREFIX}${token}`
        const raw = window.sessionStorage.getItem(key)
        const value = decode(raw, identity, Date.now())
        if (!value) return null
        window.sessionStorage.removeItem(key)
        return value.preset
    } catch { return null }
}
