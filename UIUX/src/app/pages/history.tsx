import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { RotateCw } from 'lucide-react';
import { api } from '../lib/api';
import { PrimaryButton } from '../components/primary-button';
import { track } from '../lib/analytics';

interface HItem {
  pick_id: string;
  name: string;
  timestamp: string;
  conditions: string;
  satisfaction: number;
}

const MOCK_HISTORY: HItem[] = [
  {
    pick_id: 'mock_1',
    name: '上生新所',
    timestamp: '2026-03-08T16:20:00+08:00',
    conditions: '骑车15分钟内，文化空间，有新鲜感',
    satisfaction: 4,
  },
  {
    pick_id: 'mock_2',
    name: '社区咖啡店',
    timestamp: '2026-03-05T10:30:00+08:00',
    conditions: '步行10分钟内，安静，预算¥30',
    satisfaction: 3,
  },
  {
    pick_id: 'mock_3',
    name: '苏州河畔骑行道',
    timestamp: '2026-03-01T15:00:00+08:00',
    conditions: '骑车，户外，无预算限制',
    satisfaction: 5,
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

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.getHistory();
        setItems(res.data.list);
        track('history_viewed', { count: res.data.list.length });
      } catch {
        setItems(MOCK_HISTORY);
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

        {/* 空状态 */}
        {!loading && items.length === 0 && (
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
