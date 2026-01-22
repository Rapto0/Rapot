import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function HistoryPage() {
  return (
    <Card className="bg-panel/95">
      <CardHeader>
        <CardTitle>İşlem Geçmişi</CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-white/60">
        Gerçek işlem geçmişi entegrasyonu bekleniyor. SQLite verileriyle doldurulacak.
      </CardContent>
    </Card>
  );
}
