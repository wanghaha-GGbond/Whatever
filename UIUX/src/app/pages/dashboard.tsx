import { useEffect, useState } from 'react';

interface Metrics {
  period_days: number;
  sessions: number;
  picks: number;
  completion_rate: number | null;
  nav_rate: number | null;
  redraw_rate: number | null;
  persona_rate: number | null;
  feedback_rate: number | null;
  total_history: number;
}

function pct(v: number | null) {
  if (v === null) return '—';
  return `${(v * 100).toFixed(1)}%`;
}

export function Dashboard() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/v1/dashboard/metrics?days=7')
      .then(r => r.json())
      .then(d => setMetrics(d.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const rows = metrics ? [
    { label: '决策完成率', value: pct(metrics.completion_rate), sub: `${metrics.picks} picks / ${metrics.sessions} sessions` },
    { label: '去导航率',   value: pct(metrics.nav_rate),        sub: '点击「去导航」/ 抓阄次数' },
    { label: '重抽率',     value: pct(metrics.redraw_rate),      sub: '点击「重新抽」/ 抓阄次数' },
    { label: '人格试玩率', value: pct(metrics.persona_rate),     sub: '试玩过人格的 session 数' },
    { label: '反馈提交率', value: pct(metrics.feedback_rate),    sub: '提交反馈 / 抓阄次数' },
  ] : [];

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-2xl mx-auto px-5 py-8 space-y-6">
        <div>
          <h1 className="text-xl font-bold">数据看板</h1>
          <p className="text-muted-foreground text-sm mt-1">
            最近 7 天 · 累计历史 {metrics?.total_history ?? '—'} 条
          </p>
        </div>

        {loading && (
          <div className="space-y-3">
            {[1,2,3,4,5].map(i => (
              <div key={i} className="bg-muted/50 rounded-2xl h-20 animate-pulse" />
            ))}
          </div>
        )}

        {!loading && (
          <div className="space-y-3">
            {rows.map(row => (
              <div key={row.label} className="bg-white rounded-2xl p-5 border border-border flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">{row.label}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{row.sub}</div>
                </div>
                <div className="text-2xl font-bold text-primary">{row.value}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
