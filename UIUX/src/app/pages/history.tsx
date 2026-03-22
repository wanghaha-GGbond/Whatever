import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { RotateCw } from 'lucide-react';
import { api } from '../lib/api';
import { PrimaryButton } from '../components/primary-button';
import { track } from '../lib/analytics';
import { ENABLE_MOCK_FALLBACK } from '../lib/env';
import { sessionStore } from '../lib/session';

interface HItem {
  pick_id: string;
  name: string;
  timestamp: string;
  conditions: string;
  satisfaction: number;
  went?: boolean;
  title?: string;
  content?: string;
  tags?: string[];
  actual_cost?: number | null;
  transport_used?: string | null;
}

const MOCK_HISTORY: HItem[] = [
  {
    pick_id: 'mock_1',
    name: '上生新所',
    timestamp: '2026-03-08T16:20:00+08:00',
    conditions: '骑车15分钟内，文化空间，有新鲜感',
    satisfaction: 4,
    title: '周六散心还不错',
    content: '环境比预期更舒服，拍照也好看，后面还会再来。',
    tags: ['值得再去', '拍照好看'],
    actual_cost: 0,
    transport_used: '骑车',
  },
  {
    pick_id: 'mock_2',
    name: '社区咖啡店',
    timestamp: '2026-03-05T10:30:00+08:00',
    conditions: '步行10分钟内，安静，预算¥30',
    satisfaction: 3,
    title: '一般',
    content: '人有点多，工作日中午去会更好。',
    tags: ['排队久'],
    actual_cost: 32,
    transport_used: '步行',
  },
  {
    pick_id: 'mock_3',
    name: '苏州河畔骑行道',
    timestamp: '2026-03-01T15:00:00+08:00',
    conditions: '骑车，户外，无预算限制',
    satisfaction: 5,
    title: '超预期',
    content: '风景很好，骑一圈状态就回来了。',
    tags: ['值得再去', '适合独处'],
    actual_cost: 0,
    transport_used: '骑车',
  },
];

function getSatisfactionTag(satisfaction?: number) {
  if (!satisfaction) {
    return (
      <span className="text-xs px-3 py-1 rounded-full bg-black/5 text-[#6e6e73]">
        一般
      </span>
    );
  }
  if (satisfaction >= 4) {
    return (
      <span className="text-xs px-3 py-1 rounded-full bg-[#16a34a] text-white font-medium">
        好
      </span>
    );
  }
  if (satisfaction <= 2) {
    return (
      <span className="text-xs px-3 py-1 rounded-full bg-black/8 text-[#6e6e73] font-medium">
        不好
      </span>
    );
  }
  return (
    <span className="text-xs px-3 py-1 rounded-full bg-black/5 text-[#6e6e73]">
      一般
    </span>
  );
}

function formatDate(timestamp: string) {
  try {
    return new Date(timestamp).toLocaleDateString('zh-CN', {
      month: 'numeric',
      day: 'numeric',
      weekday: 'short',
    });
  } catch {
    return timestamp;
  }
}

export function History() {
  const navigate = useNavigate();
  const [items, setItems] = useState<HItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      setError('');
      try {
        const userId = sessionStore.getUserId() || sessionStore.getDeviceId();
        const res = await api.getHistory(userId);
        setItems(res.data.list);
        track('history_viewed', { count: res.data.list.length });
      } catch {
        if (ENABLE_MOCK_FALLBACK) {
          setItems(MOCK_HISTORY);
        } else {
          setItems([]);
          setError('历史记录加载失败，请稍后重试。');
        }
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <div className="min-h-screen bg-[#f0fdf4]">
      <div className="max-w-2xl mx-auto px-5 py-8 space-y-6">
        <div>
          <h1 className="text-xl font-bold text-[#1d1d1f]">历史记录</h1>
          <p className="text-[#6e6e73] mt-1 text-sm">你的出门记录</p>
        </div>

        {/* 骨架屏 */}
        {loading && (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-white/70 backdrop-blur-2xl rounded-3xl h-28 animate-pulse border border-white/50"
              />
            ))}
          </div>
        )}

        {/* 记录列表 */}
        {!loading && items.length > 0 && (
          <div className="space-y-4">
            {items.map((item) => (
              <div
                key={item.pick_id}
                className="bg-white/70 backdrop-blur-2xl rounded-3xl p-5 border border-white/50 shadow-[0_8px_32px_rgba(0,0,0,0.08)] hover:shadow-[0_12px_40px_rgba(0,0,0,0.12)] transition-all"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-base text-[#1d1d1f] mb-0.5 truncate">{item.name}</h3>
                    <div className="text-xs text-[#6e6e73]">
                      {formatDate(item.timestamp)}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-3 shrink-0">
                    {getSatisfactionTag(item.satisfaction)}
                  </div>
                </div>

                <div className="bg-black/4 rounded-2xl p-3 mb-3">
                  <div className="text-xs text-[#6e6e73] mb-1">当时条件：</div>
                  <div className="text-sm text-[#1d1d1f]">{item.conditions || '—'}</div>
                </div>

                {item.title || item.content ? (
                  <div className="bg-white/70 rounded-2xl border border-black/6 p-3 mb-3 space-y-1.5">
                    {item.title ? (
                      <div className="text-sm font-medium text-[#1d1d1f]">{item.title}</div>
                    ) : null}
                    {item.content ? (
                      <div className="text-sm text-[#4b5563] leading-relaxed">{item.content}</div>
                    ) : null}
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {(item.tags || []).map((tag) => (
                        <span
                          key={`${item.pick_id}_${tag}`}
                          className="text-[11px] px-2 py-1 rounded-full bg-[#16a34a]/10 text-[#15803d]"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}

                {(item.actual_cost != null || item.transport_used) ? (
                  <div className="text-xs text-[#6e6e73] mb-3">
                    {item.transport_used ? `出行：${item.transport_used}` : ''}
                    {item.actual_cost != null ? ` · 实际花费：¥${item.actual_cost}` : ''}
                  </div>
                ) : null}

                <button
                  onClick={() => navigate('/')}
                  className="flex items-center gap-1 text-xs text-[#6e6e73] hover:text-[#1d1d1f] transition-colors"
                >
                  <RotateCw className="w-3.5 h-3.5" />
                  再抽一次
                </button>
              </div>
            ))}
          </div>
        )}

        {!loading && error && (
          <div className="rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {error}
          </div>
        )}

        {/* 空状态 */}
        {!loading && items.length === 0 && !error && (
          <div className="flex flex-col items-center justify-center py-24 space-y-3">
            <div className="text-3xl font-bold text-black/15">还没有记录</div>
            <p className="text-sm text-[#6e6e73]">每次出门决策都会留在这里</p>
            <div className="pt-2 w-40">
              <PrimaryButton onClick={() => navigate('/')}>
                去决策一次
              </PrimaryButton>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
