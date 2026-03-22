import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { ChevronDown, Loader2, RotateCw } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { CandidateCard } from '../components/candidate-card';
import { PrimaryButton } from '../components/primary-button';
import { api, Candidate } from '../lib/api';
import { sessionStore } from '../lib/session';
import { mockPlaces } from '../lib/mock-data';
import { track } from '../lib/analytics';
import { ENABLE_MOCK_FALLBACK } from '../lib/env';

// 把 mock-data 的 Place[] 结构映射成 Candidate[] 结构
const MOCK_CANDIDATES: Candidate[] = mockPlaces.map((p, i) => ({
  candidate_id: p.id,
  name: p.name,
  type: p.type,
  eta_min: parseInt(p.distance.replace(/[^0-9]/g, '')) || 15,
  distance_m: [2300, 1900, 2600, 1700, 2100][i % 5],
  transport_mode: p.distance.includes('步行') ? '步行' : p.distance.includes('地铁') ? '地铁' : '骑车',
  budget_text: p.budget,
  ai_judgement: p.aiJudgement,
  risk_label: p.riskLabel,
}));

const MOCK_SUMMARY = 'AI 已为你筛选出附近合适去处，综合了距离、氛围和当前时段人流。';

interface DrawCardLite {
  candidate_id: string;
  name: string;
  type: string;
}

function toDrawPool(list: Candidate[]): DrawCardLite[] {
  return list.slice(0, 10).map((c) => ({
    candidate_id: c.candidate_id,
    name: c.name,
    type: c.type,
  }));
}

function shuffleCandidates(list: Candidate[]): Candidate[] {
  const next = [...list];
  for (let i = next.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [next[i], next[j]] = [next[j], next[i]];
  }
  return next;
}

function parseBudgetUpper(text: string): number {
  if (!text) return Number.POSITIVE_INFINITY;
  if (text.includes('不限')) return Number.POSITIVE_INFINITY;
  const nums = text.match(/\d+/g)?.map((n) => parseInt(n, 10)) ?? [];
  if (nums.length === 0) return Number.POSITIVE_INFINITY;
  return Math.max(...nums);
}

function SkeletonCard() {
  return (
    <div className="bg-white/70 backdrop-blur-2xl rounded-3xl h-28 animate-pulse border border-white/50" />
  );
}

function LaunchingOverlay() {
  return (
    <div className="fixed inset-0 z-50 bg-[#f0fdf4]">
      <div className="h-full w-full px-5 py-8">
        <div className="max-w-2xl mx-auto h-full flex flex-col justify-center gap-8">
          <motion.div
            initial={{ scale: 0.85, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.24, ease: 'easeOut' }}
            className="mx-auto"
          >
            <motion.div
              animate={{ scale: [1, 1.06, 1], boxShadow: ['0 8px 24px rgba(0,0,0,0.12)', '0 18px 36px rgba(16,185,129,0.28)', '0 8px 24px rgba(0,0,0,0.12)'] }}
              transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
              className="rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 text-white px-10 py-4 font-medium text-base inline-flex items-center gap-2"
            >
              <Loader2 className="w-5 h-5 animate-spin" />
              AI 选址中...
            </motion.div>
          </motion.div>

          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-20 rounded-3xl border border-white/80 bg-white/70 backdrop-blur-2xl relative overflow-hidden"
              >
                <motion.div
                  className="absolute inset-y-0 -left-1/3 w-1/3 bg-gradient-to-r from-transparent via-white/60 to-transparent"
                  animate={{ x: ['0%', '340%'] }}
                  transition={{ duration: 1.25, repeat: Infinity, ease: 'linear', delay: i * 0.15 }}
                />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function Candidates() {
  const navigate = useNavigate();
  const [items, setItems] = useState<Candidate[]>([]);
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [drawError, setDrawError] = useState('');
  const [budgetFilter, setBudgetFilter] = useState<'all' | 'le30' | 'le50'>('all');
  const [distanceSort, setDistanceSort] = useState<'default' | 'near' | 'far'>('default');
  const [typeFilter, setTypeFilter] = useState('all');

  useEffect(() => {
    const run = async () => {
      const sessionId = sessionStore.getSessionId();
      if (!sessionId) {
        navigate('/');
        return;
      }
      setLoadError('');
      // mock session fallback：跳过 API 直接用 mock 数据
      if (sessionId.startsWith('mock_session_fallback')) {
        if (!ENABLE_MOCK_FALLBACK) {
          setLoadError('当前环境已禁用本地兜底，请返回首页重新发起推荐。');
          setItems([]);
          setSummary('');
          setLoading(false);
          return;
        }
        const fallbackItems = shuffleCandidates(MOCK_CANDIDATES);
        setItems(fallbackItems);
        sessionStore.setCandidatePool(toDrawPool(fallbackItems));
        setSummary(MOCK_SUMMARY);
        setLoading(false);
        return;
      }
      try {
        const res = await api.getCandidates(sessionId);
        setItems(res.data.candidates);
        sessionStore.setCandidatePool(toDrawPool(res.data.candidates));
        track('candidates_viewed', { count: res.data.candidates.length, fallback: res.data.fallback_used }, sessionId, undefined);
        setSummary(res.data.summary);
      } catch {
        if (ENABLE_MOCK_FALLBACK) {
          const fallbackItems = shuffleCandidates(MOCK_CANDIDATES);
          setItems(fallbackItems);
          sessionStore.setCandidatePool(toDrawPool(fallbackItems));
          setSummary(MOCK_SUMMARY);
        } else {
          setItems([]);
          setSummary('');
          setLoadError('候选加载失败，请稍后重试。');
        }
      } finally {
        setLoading(false);
      }
    };
    run();
  }, [navigate]);

  const handleDraw = async () => {
    const sessionId = sessionStore.getSessionId();
    if (!sessionId) return;
    setLaunching(true);
    setDrawError('');
    const visiblePool = filteredItems.length ? filteredItems : items;
    sessionStore.setCandidatePool(toDrawPool(visiblePool));

    if (sessionId.startsWith('mock_session_fallback')) {
      if (!ENABLE_MOCK_FALLBACK) {
        setDrawError('当前环境禁用本地抽签，请返回首页重新发起。');
        setLaunching(false);
        return;
      }
      const pool = items.length ? items : MOCK_CANDIDATES;
      const picked = pool[Math.floor(Math.random() * pool.length)];
      sessionStore.setPickId(`mock_pick_fallback_${Date.now()}`);
      sessionStore.setPicked({
        candidate_id: picked.candidate_id,
        name: picked.name,
        type: picked.type,
        distance_m: picked.distance_m,
        eta_min: picked.eta_min,
        transport_mode: picked.transport_mode,
        budget_text: picked.budget_text,
        reason: picked.ai_judgement,
      });
      await new Promise((resolve) => setTimeout(resolve, 260));
      navigate('/result');
      return;
    }

    // 非 mock 场景下，不在本页阻塞等待 AI，直接进入结果页展示过渡动画
    sessionStore.setPickId('');
    sessionStore.setPicked({});
    await new Promise((resolve) => setTimeout(resolve, 260));
    navigate('/result');
  };

  const availableTypes = useMemo(() => {
    const set = new Set(items.map((c) => c.type).filter(Boolean));
    return ['all', ...Array.from(set)];
  }, [items]);

  const filteredItems = useMemo(() => {
    let next = [...items];

    if (budgetFilter !== 'all') {
      const maxBudget = budgetFilter === 'le30' ? 30 : 50;
      next = next.filter((c) => parseBudgetUpper(c.budget_text) <= maxBudget);
    }

    if (typeFilter !== 'all') {
      next = next.filter((c) => c.type === typeFilter);
    }

    if (distanceSort === 'near') {
      next.sort((a, b) => (a.distance_m || 0) - (b.distance_m || 0));
    } else if (distanceSort === 'far') {
      next.sort((a, b) => (b.distance_m || 0) - (a.distance_m || 0));
    }

    return next;
  }, [items, budgetFilter, typeFilter, distanceSort]);

  const formatDistance = (m: number) =>
    m >= 1000 ? `${(m / 1000).toFixed(1)}km` : `${m}m`;

  const places = filteredItems.map((c) => ({
    id: c.candidate_id,
    name: c.name,
    type: c.type,
    distance: c.distance_m
      ? `${c.transport_mode || '出行'}约${c.eta_min}分钟 · ${formatDistance(c.distance_m)}`
      : `${c.transport_mode || '出行'}约${c.eta_min}分钟`,
    budget: c.budget_text,
    aiJudgement: c.ai_judgement,
    riskLabel: c.risk_label,
  }));

  return (
    <div className="min-h-screen bg-[#f0fdf4]">
      <AnimatePresence>
        {launching && (
          <motion.div
            key="launching"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.16, ease: 'easeOut' }}
          >
            <LaunchingOverlay />
          </motion.div>
        )}
      </AnimatePresence>

      {/* 筛选栏 */}
      <div className="sticky top-0 z-10 bg-white/80 backdrop-blur-2xl border-b border-black/8 px-5 py-3">
        <div className="flex items-center gap-2 max-w-2xl mx-auto">
          <button
            onClick={() => {
              setBudgetFilter((prev) => (prev === 'all' ? 'le30' : prev === 'le30' ? 'le50' : 'all'));
            }}
            className="flex items-center gap-1 px-3.5 py-2 rounded-2xl bg-black/5 text-sm text-[#1d1d1f] hover:bg-black/10 transition-colors"
          >
            {budgetFilter === 'all' ? '预算: 全部' : budgetFilter === 'le30' ? '预算: ≤30' : '预算: ≤50'}
            <ChevronDown className="w-4 h-4 text-[#6e6e73]" />
          </button>
          <button
            onClick={() => {
              setDistanceSort((prev) => (prev === 'default' ? 'near' : prev === 'near' ? 'far' : 'default'));
            }}
            className="flex items-center gap-1 px-3.5 py-2 rounded-2xl bg-black/5 text-sm text-[#1d1d1f] hover:bg-black/10 transition-colors"
          >
            {distanceSort === 'default' ? '距离: 默认' : distanceSort === 'near' ? '距离: 由近到远' : '距离: 由远到近'}
            <ChevronDown className="w-4 h-4 text-[#6e6e73]" />
          </button>
          <button
            onClick={() => {
              const idx = availableTypes.indexOf(typeFilter);
              const nextIdx = idx >= 0 ? (idx + 1) % availableTypes.length : 0;
              setTypeFilter(availableTypes[nextIdx]);
            }}
            className="flex items-center gap-1 px-3.5 py-2 rounded-2xl bg-black/5 text-sm text-[#1d1d1f] hover:bg-black/10 transition-colors"
          >
            类型: {typeFilter === 'all' ? '全部' : typeFilter}
            <ChevronDown className="w-4 h-4 text-[#6e6e73]" />
          </button>
          <button
            onClick={() => {
              setBudgetFilter('all');
              setDistanceSort('default');
              setTypeFilter('all');
            }}
            className="ml-auto flex items-center gap-1 px-3.5 py-2 rounded-2xl text-sm text-[#6e6e73] hover:text-[#1d1d1f] hover:bg-black/5 transition-colors"
          >
            <RotateCw className="w-4 h-4" />重筛
          </button>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-5 py-6 pb-36 space-y-6">
        {/* AI 摘要条 */}
        {summary && (
          <div className="bg-white/70 backdrop-blur-2xl rounded-2xl px-4 py-3 text-sm text-[#1d1d1f] border border-white/50 shadow-[0_4px_16px_rgba(0,0,0,0.06)]">
            {summary}
          </div>
        )}
        {loadError && (
          <div className="bg-amber-50 border border-amber-300 text-amber-800 rounded-2xl px-4 py-3 text-sm">
            {loadError}
          </div>
        )}
        {drawError && (
          <div className="bg-amber-50 border border-amber-300 text-amber-800 rounded-2xl px-4 py-3 text-sm">
            {drawError}
          </div>
        )}
        {loading && !summary && (
          <div className="bg-white/50 rounded-2xl px-4 py-3 h-10 animate-pulse" />
        )}

        {/* 候选卡片列表 */}
        <div className="space-y-4">
          {loading ? (
            <>
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </>
          ) : (
            places.map((place) => <CandidateCard key={place.id} place={place} />)
          )}
        </div>
      </div>

      {/* CTA 固定底部 */}
      <div className="fixed bottom-16 left-0 right-0 px-5 z-10">
        <div className="bg-gradient-to-t from-[#f0fdf4]/95 to-transparent pb-3 pt-4">
          <div className="max-w-2xl mx-auto">
            <PrimaryButton
              onClick={handleDraw}
              variant="secondary"
              disabled={loading || places.length === 0 || launching}
            >
              <span className="inline-flex items-center justify-center gap-2">
                {launching ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                {launching ? '正在呼叫 AI 翻牌…' : '开始抓阄'}
              </span>
            </PrimaryButton>
          </div>
        </div>
      </div>
    </div>
  );
}
