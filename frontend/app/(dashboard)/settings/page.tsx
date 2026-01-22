import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";

export default function SettingsPage() {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card className="bg-panel/95">
        <CardHeader>
          <CardTitle>Bildirim Ayarları</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div className="space-y-2">
            <label className="text-xs text-white/60">Telegram ID</label>
            <Input placeholder="@otonomtrader" />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-white/60">API Key</label>
            <Input type="password" placeholder="••••••••" />
          </div>
          <div className="flex items-center justify-between rounded-lg border border-white/10 bg-black/20 p-3">
            <div>
              <p className="text-sm text-white">Kritik Sinyal Bildirimi</p>
              <p className="text-xs text-white/50">HUNTER skoru &gt; 85</p>
            </div>
            <Switch defaultChecked />
          </div>
        </CardContent>
      </Card>
      <Card className="bg-panel/95">
        <CardHeader>
          <CardTitle>Strateji Parametreleri</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5 text-sm">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs text-white/60">RSI Eşiği</label>
              <span className="text-xs text-white/50">30</span>
            </div>
            <Slider defaultValue={[30]} max={70} min={10} step={1} />
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs text-white/60">MACD Hassasiyeti</label>
              <span className="text-xs text-white/50">1.4</span>
            </div>
            <Slider defaultValue={[14]} max={30} min={5} step={1} />
          </div>
          <div className="flex items-center justify-between rounded-lg border border-white/10 bg-black/20 p-3">
            <div>
              <p className="text-sm text-white">Otomatik Risk Azaltma</p>
              <p className="text-xs text-white/50">Volatilite yüksekse aktif</p>
            </div>
            <Switch />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
