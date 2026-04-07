import { useState, useEffect, useRef, useCallback } from 'react';
import { Navigation, RotateCw, MessageSquarePlus, Sparkles, MapPin, Loader2 } from 'lucide-react';
import { PersonaTabs } from '../components/persona-tabs';
import { PersonaSliceView } from '../components/persona-slice-view';
import { ShareCardNode } from '../components/share-card-node';
import { CELEBRITIES } from '../lib/celebrities';
import { isPro } from '../lib/pro';
import { CelebrityPersonaCard } from '../components/celebrity-persona-card';
import { ProGateSheet } from '../components/pro-gate-sheet';
import { PrimaryButton } from '../components/primary-button';
import { motion, AnimatePresence } from 'motion/react';
import { api } from '../lib/api';
import { sessionStore } from '../lib/session';
import { API_BASE_URL } from '../lib/env';
import { useNavigate } from 'react-router';
import { mockPlaces, personaReviews } from '../lib/mock-data';
import { track } from '../lib/analytics';
import { ENABLE_MOCK_FALLBACK } from '../lib/env';
import { useShareCard } from '../hooks/use-share-card';
import type { PersonaSlice } from '../types';

interface DrawCard {
  candidate_id: string;
  name: string;
  type: string;
}

interface PickedPlace {
  candidate_id?: string;
  name: string;
  type: string;
  distance_m?: number;
  eta_min: number;
  transport_mode?: string;
  budget_text: string;
  reason: string;
  nav_url?: string;
  location?: string;
}

interface ReviewData {
  persona: string;
  summary: string;
  slices: PersonaSlice[];
  review: string;
  risk: string | null;
  conclusion: string;
}

function isValidPicked(value: unknown): value is PickedPlace {
  if (!value || typeof value !== 'object') return false;
  const v = value as Partial<PickedPlace>;
  return (
    typeof v.name === 'string' &&
    v.name.length > 0 &&
    typeof v.type === 'string' &&
    v.type.length > 0 &&
    typeof v.eta_min === 'number' &&
    typeof v.budget_text === 'string'
  );
}

const MOCK_DISTANCES: Record<string, number> = {
  '1': 2300,
  '2': 1900,
  '3': 2600,
  '4': 1700,
  '5': 2100,
};

function randomMockPicked(): PickedPlace {
  const item = mockPlaces[Math.floor(Math.random() * mockPlaces.length)] ?? mockPlaces[0];
  const eta = parseInt(item.distance.replace(/[^0-9]/g, ''), 10) || 15;
  const transportMode =
    item.distance.includes('步行') ? '步行' :
    item.distance.includes('地铁') ? '地铁' :
    '骑车';

  return {
    candidate_id: `mock_${item.id}_${Date.now()}`,
    name: item.name,
    type: item.type,
    eta_min: eta,
    distance_m: MOCK_DISTANCES[item.id] ?? 0,
    transport_mode: transportMode,
    budget_text: item.budget,
    reason: item.aiJudgement,
  };
}

function fallbackDrawCards(): DrawCard[] {
  return Array.from({ length: 10 }, (_, i) => {
    const p = mockPlaces[i % mockPlaces.length];
    return {
      candidate_id: `fallback_${i}_${p.id}`,
      name: p.name,
      type: p.type,
    };
  });
}

function placeholderDrawCards(): DrawCard[] {
  return Array.from({ length: 10 }, (_, i) => ({
    candidate_id: `placeholder_${i}`,
    name: `候选地点 ${i + 1}`,
    type: '待揭晓',
  }));
}

function cardsFromPicked(picked: PickedPlace): DrawCard[] {
  return Array.from({ length: 10 }, (_, i) => ({
    candidate_id: `${picked.candidate_id || 'picked'}_${i}`,
    name: picked.name,
    type: picked.type,
  }));
}

function normalizeDrawCards(
  cards: DrawCard[],
  opts?: { allowMockFallback?: boolean; picked?: PickedPlace },
): DrawCard[] {
  const allowMockFallback = opts?.allowMockFallback ?? true;
  const cleaned = cards
    .filter((c) => c && c.name && c.type)
    .slice(0, 10)
    .map((c, i) => ({
      candidate_id: c.candidate_id || `candidate_${i}`,
      name: c.name,
      type: c.type,
    }));

  if (cleaned.length >= 10) return cleaned;

  if (!allowMockFallback) {
    if (opts?.picked) return cardsFromPicked(opts.picked);
    if (cleaned.length > 0) return cleaned;
    return placeholderDrawCards();
  }

  const fillers = fallbackDrawCards();
  while (cleaned.length < 10) {
    const f = fillers[cleaned.length % fillers.length];
    cleaned.push({
      candidate_id: `${f.candidate_id}_${cleaned.length}`,
      name: f.name,
      type: f.type,
    });
  }
  return cleaned;
}

function ThinkingBridge() {
  const steps = [
    'AI 正在根据你的偏好选地址',
    '正在评估候选地点匹配度',
    '正在生成 AI 入选理由',
  ];
  const [step, setStep] = useState(0);

  useEffect(() => {
    const t = setInterval(() => {
      setStep((s) => (s + 1) % steps.length);
    }, 900);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_15%_10%,#dcfce7_0%,#f0fdf4_35%,#ecfeff_100%)] flex items-center justify-center px-5">
      <div className="w-full max-w-md rounded-3xl border border-white/70 bg-white/70 backdrop-blur-2xl p-6 shadow-[0_20px_60px_rgba(15,23,42,0.12)] space-y-5">
        <div className="flex items-center gap-3">
          <motion.div
            className="h-10 w-10 rounded-2xl bg-gradient-to-br from-emerald-300 to-cyan-300"
            animate={{ rotate: [0, 12, -8, 0], scale: [1, 1.04, 1] }}
            transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
          />
          <div>
            <div className="text-sm font-semibold text-slate-900">AI 正在为你翻牌</div>
            <div className="text-xs text-slate-500">这一步会花几秒生成理由</div>
          </div>
        </div>

        <AnimatePresence mode="wait">
          <motion.p
            key={step}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="text-sm text-slate-700"
          >
            {steps[step]}
          </motion.p>
        </AnimatePresence>

        <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-emerald-400 via-cyan-400 to-blue-400"
            animate={{ x: ['-100%', '100%'] }}
            transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
          />
        </div>
      </div>
    </div>
  );
}

function findPickedCardIndex(cards: DrawCard[], picked: PickedPlace): number {
  if (picked.candidate_id) {
    const byId = cards.findIndex((c) => c.candidate_id === picked.candidate_id);
    if (byId >= 0) return byId;
  }
  const byName = cards.findIndex((c) => c.name === picked.name);
  if (byName >= 0) return byName;
  return 0;
}

function buildFallbackReview(persona: string, picked?: PickedPlace | null): ReviewData {
  const base = personaReviews[persona] ?? personaReviews['独处型'];
  if (!picked) return { ...base, summary: base.review, slices: [] };
  return {
    ...base,
    summary: base.review,
    slices: [],
    review: `${picked.name}：${base.review}`,
    risk: `${picked.name}可能的风险：${base.risk}`,
  };
}

function formatDistance(m?: number) {
  if (!m) return '';
  return m >= 1000 ? `${(m / 1000).toFixed(1)}km` : `${m}m`;
}

interface DrawingAnimationProps {
  cards: DrawCard[];
  settleIndex: number;
  onDone: () => void;
}

function DrawingAnimation({ cards, settleIndex, onDone }: DrawingAnimationProps) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [phase, setPhase] = useState<'shuffle' | 'eliminate' | 'final_draw' | 'reveal'>('shuffle');
  const [alive, setAlive] = useState<boolean[]>(() => cards.map(() => true));
  const shuffleTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const eliminateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const finalDrawTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const doneRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const n = cards.length;
    if (!n) {
      onDone();
      return;
    }

    const target = Math.max(0, Math.min(settleIndex, n - 1));
    const aliveSet = new Set<number>(Array.from({ length: n }, (_, i) => i));
    let idx = 0;
    let shuffleTicks = 0;

    setPhase('shuffle');
    setAlive(Array.from({ length: n }, () => true));
    setActiveIdx(0);

    const finish = () => {
      setPhase('reveal');
      setActiveIdx(target);
      setAlive(Array.from({ length: n }, (_, i) => i === target));
      if (navigator.vibrate) navigator.vibrate(90);
      doneRef.current = setTimeout(onDone, 1450);
    };

    const startFinalDraw = () => {
      const finalists = Array.from(aliveSet);
      if (finalists.length <= 1) {
        finish();
        return;
      }
      setPhase('final_draw');
      let t = 0;
      finalDrawTimerRef.current = setInterval(() => {
        t += 1;
        const current = finalists[t % finalists.length];
        setActiveIdx(current);
        if (t >= 14) {
          if (finalDrawTimerRef.current) clearInterval(finalDrawTimerRef.current);
          setActiveIdx(target);
          finish();
        }
      }, 120);
    };

    const scheduleElimination = (delayMs: number) => {
      eliminateTimerRef.current = setTimeout(() => {
        const removable = Array.from(aliveSet).filter((i) => i !== target);
        if (removable.length <= 0) {
          startFinalDraw();
          return;
        }

        const removedIdx = removable[Math.floor(Math.random() * removable.length)];
        aliveSet.delete(removedIdx);
        setActiveIdx(removedIdx);
        if (navigator.vibrate) navigator.vibrate(18);
        setAlive((prev) => prev.map((v, i) => (i === removedIdx ? false : v)));

        if (aliveSet.size <= 3) {
          startFinalDraw();
          return;
        }

        const remaining = aliveSet.size;
        const nextDelay = remaining <= 3 ? 460 : remaining <= 6 ? 320 : 240;
        scheduleElimination(nextDelay);
      }, delayMs);
    };

    shuffleTimerRef.current = setInterval(() => {
      idx = (idx + 1) % n;
      shuffleTicks += 1;
      setActiveIdx(idx);
      if (shuffleTicks >= Math.max(20, n * 2)) {
        if (shuffleTimerRef.current) clearInterval(shuffleTimerRef.current);
        setPhase('eliminate');
        scheduleElimination(260);
      }
    }, 85);

    return () => {
      if (shuffleTimerRef.current) clearInterval(shuffleTimerRef.current);
      if (eliminateTimerRef.current) clearTimeout(eliminateTimerRef.current);
      if (finalDrawTimerRef.current) clearInterval(finalDrawTimerRef.current);
      if (doneRef.current) clearTimeout(doneRef.current);
    };
  }, [cards, settleIndex, onDone]);

  const aliveCount = alive.filter(Boolean).length || cards.length;
  const ritualText =
    phase === 'shuffle'
      ? '洗牌中'
      : phase === 'eliminate'
        ? `命运筛选中 · 剩余 ${aliveCount} 张`
        : phase === 'final_draw'
          ? '最终抽取中'
          : '命运已揭晓';

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_35%_10%,#dcfce7_0%,#ecfeff_42%,#f0fdf4_100%)] relative overflow-hidden flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_76%,rgba(16,185,129,0.2),transparent_60%)]" />
      <div className="relative z-10 w-full max-w-[440px] space-y-6">
        <AnimatePresence mode="wait">
          <motion.p
            key={ritualText}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.16 }}
            className="text-center text-[11px] tracking-[0.24em] uppercase text-emerald-700"
          >
            {ritualText}
          </motion.p>
        </AnimatePresence>

        <div className="grid grid-cols-5 gap-2 sm:gap-3">
          {cards.map((card, idx) => {
            const isAlive = alive[idx] ?? true;
            const isActive = phase !== 'reveal' && idx === activeIdx;
            const isRevealWinner = phase === 'reveal' && idx === settleIndex;
            const isEliminated = !isAlive && !isRevealWinner;
            const sigil = ['SUN', 'MOON', 'STAR', 'WAVE', 'WIND', 'TREE', 'FIRE', 'MIST', 'NOVA', 'AURA'][idx % 10];

            return (
              <motion.div
                key={card.candidate_id}
                animate={{
                  y: isRevealWinner ? -14 : isActive ? -5 : isEliminated ? 6 : 0,
                  rotate: isEliminated ? (idx % 2 === 0 ? -7 : 7) : ((idx % 5) - 2) * 1.3,
                  scale: isRevealWinner ? 1.38 : isActive ? 1.03 : isEliminated ? 0.9 : 1,
                  opacity: isEliminated ? 0.22 : 1,
                  boxShadow: isRevealWinner
                    ? '0 12px 30px rgba(16,185,129,0.32)'
                    : isActive
                      ? '0 8px 22px rgba(16,185,129,0.24)'
                      : '0 4px 12px rgba(15,23,42,0.1)',
                }}
                transition={{ duration: 0.22, ease: 'easeOut' }}
                className={`aspect-[3/4] rounded-xl border border-emerald-100/70 overflow-hidden bg-white/75 ${isRevealWinner ? 'z-20' : ''}`}
              >
                {isRevealWinner ? (
                  <div className="h-full w-full bg-gradient-to-b from-emerald-300/35 via-emerald-100/20 to-emerald-900/70 p-2 flex flex-col justify-between ring-1 ring-emerald-100/70">
                    <Sparkles className="w-3.5 h-3.5 text-emerald-100/95" />
                    <div>
                      <div className="text-[9px] text-emerald-50/95 tracking-[0.16em]">DESTINY</div>
                      <div className="text-[8px] text-emerald-100/90 mt-1">RESULT LOCKED</div>
                    </div>
                  </div>
                ) : (
                  <div className="h-full w-full bg-gradient-to-b from-white/95 via-emerald-50/85 to-emerald-100/55 flex flex-col items-center justify-center relative">
                    <div className="absolute inset-x-2 top-2 h-px bg-emerald-200/75" />
                    <div className="absolute inset-x-2 bottom-2 h-px bg-emerald-200/75" />
                    <div className="text-[9px] tracking-[0.18em] text-emerald-700/85">{sigil}</div>
                    <div className="text-[8px] text-emerald-600/70 mt-1">CARD {idx + 1}</div>
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>

        <p className="text-center text-xs text-slate-600">
          {phase === 'shuffle'
            ? '牌组正在重排命运顺序…'
            : phase === 'eliminate'
              ? '逐张淘汰中，保留最终候选…'
              : phase === 'final_draw'
                ? '最后一抽，命运即将揭晓…'
                : '结果锁定，正在揭晓…'}
        </p>
      </div>
    </div>
  );
}

function ResultRevealTransition() {
  return (
    <div className="min-h-screen flex items-center justify-center px-5 overflow-hidden [perspective:1200px] relative">
      <motion.div
        className="absolute inset-0 bg-[radial-gradient(circle_at_35%_10%,#dcfce7_0%,#ecfeff_42%,#f0fdf4_100%)]"
        initial={{ scale: 1, filter: 'blur(0px)' }}
        animate={{ scale: 1.08, filter: 'blur(7px)' }}
        transition={{ duration: 0.66, ease: [0.22, 0.7, 0.24, 1] }}
      />
      <motion.div
        className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(16,185,129,0.08)_0%,rgba(15,23,42,0.2)_78%)]"
        initial={{ opacity: 0.15 }}
        animate={{ opacity: 0.45 }}
        transition={{ duration: 0.62, ease: 'easeOut' }}
      />

      <motion.div
        className="relative w-[148px] h-[214px] [transform-style:preserve-3d] z-10"
        initial={{ opacity: 1, scale: 1, rotateX: -3, rotateY: 0, y: 0, z: 0 }}
        animate={{ opacity: 0, scale: 2.65, rotateX: 13, rotateY: -28, y: -34, z: 420 }}
        transition={{ duration: 0.66, ease: [0.2, 0.7, 0.2, 1] }}
      >
        <motion.div
          initial={{ opacity: 0.75, scale: 1 }}
          animate={{ opacity: 0, scale: 1.42 }}
          transition={{ duration: 0.62, ease: 'easeOut' }}
          className="absolute -inset-8 rounded-[30px] bg-emerald-300/35 blur-2xl"
        />

        <motion.div
          initial={{ rotateY: 0 }}
          animate={{ rotateY: 78 }}
          transition={{ duration: 0.66, ease: [0.2, 0.7, 0.2, 1] }}
          className="absolute inset-0 rounded-2xl [transform-style:preserve-3d]"
        >
          <div className="absolute inset-0 rounded-2xl border border-emerald-100/80 bg-gradient-to-b from-emerald-300/35 via-emerald-100/20 to-emerald-900/70 shadow-[0_20px_60px_rgba(16,185,129,0.28)] [backface-visibility:hidden] flex items-center justify-center">
            <div className="text-[11px] tracking-[0.24em] text-emerald-100/95">DESTINY</div>
          </div>
          <div className="absolute inset-0 rounded-2xl border border-cyan-100/80 bg-gradient-to-b from-cyan-200/45 via-cyan-100/30 to-cyan-900/70 [transform:rotateY(180deg)] [backface-visibility:hidden] flex items-center justify-center">
            <div className="text-[11px] tracking-[0.22em] text-cyan-50/95">REVEAL</div>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}

export function Result() {
  const navigate = useNavigate();
  const [isDrawing, setIsDrawing] = useState(true);
  const [isRevealing, setIsRevealing] = useState(false);
  const [selectedPersona, setSelectedPersona] = useState('独处型');
  const [reviewCache, setReviewCache] = useState<Record<string, ReviewData>>({});
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewError, setReviewError] = useState('');
  const [proGateOpen, setProGateOpen] = useState(false);
  const [pageError, setPageError] = useState('');
  const [picked, setPicked] = useState<PickedPlace | null>(null);
  const [pickedLoading, setPickedLoading] = useState(true);
  const [drawCards, setDrawCards] = useState<DrawCard[]>([]);
  const [settleIndex, setSettleIndex] = useState(0);
  const revealTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const review = reviewCache[selectedPersona] ?? null;

  const { share, sharing } = useShareCard();

  const sharePersona2 = selectedPersona === '务实型' ? '独处型' : '务实型';
  const shareReview1 = reviewCache[selectedPersona];
  const shareReview2 = reviewCache[sharePersona2];
  const shareReady = !!picked && !!shareReview1 && !!shareReview2;

  const personas = ['独处型', '探索型', '务实型', '审美型', '老饕', '效率党', '精算师', '氛围感'];

  const handlePersonaChange = (persona: string) => {
    setSelectedPersona(persona);
    track('persona_tab_clicked', { persona }, sessionStore.getSessionId(), sessionStore.getDeviceId());
  };

  const handleCelebrityClick = useCallback(async (celebrity: typeof CELEBRITIES[0]) => {
    if (!isPro()) {
      setProGateOpen(true);
      return;
    }
    const sessionId = sessionStore.getSessionId();
    const pickId = sessionStore.getPickId();
    if (!sessionId || !pickId) return;

    const cacheKey = `celebrity:${celebrity.id}`;
    if (reviewCache[cacheKey]) {
      setSelectedPersona(cacheKey);
      return;
    }

    setSelectedPersona(cacheKey);
    setReviewLoading(true);
    setReviewError('');
    try {
      const reviewRes = await api.personaReview(sessionId, pickId, celebrity.name, celebrity.id);
      setReviewCache((prev) => ({ ...prev, [cacheKey]: reviewRes.data }));
    } catch {
      setReviewError('名人视角加载失败，请稍后重试。');
    } finally {
      setReviewLoading(false);
    }
  }, [reviewCache]);

  const loadPersonaReview = useCallback(async (persona: string, showLoading = true) => {
    const sessionId = sessionStore.getSessionId();
    const pickId = sessionStore.getPickId();
    if (!sessionId || !pickId) return;

    let alreadyCached = false;
    setReviewCache((prev) => { alreadyCached = !!prev[persona]; return prev; });
    if (alreadyCached) return;

    if (showLoading) { setReviewLoading(true); setReviewError(''); }
    try {
      const reviewRes = await api.personaReview(sessionId, pickId, persona);
      setReviewCache((prev) => ({ ...prev, [persona]: reviewRes.data }));
    } catch {
      if (showLoading) {
        if (ENABLE_MOCK_FALLBACK) {
          const fb = buildFallbackReview(persona, picked);
          setReviewCache((prev) => ({ ...prev, [persona]: fb }));
        } else {
          setReviewError('人格试玩加载失败，请稍后重试。');
        }
      }
    } finally {
      if (showLoading) setReviewLoading(false);
    }
  }, [picked]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const loadPicked = async () => {
      const startedAt = Date.now();
      const sessionId = sessionStore.getSessionId();
      if (!sessionId) {
        navigate('/');
        return;
      }
      setPageError('');

      const pickId = sessionStore.getPickId();
      const isMockSession = sessionId.startsWith('mock_session_fallback');
      const isMockPick = pickId.startsWith('mock_pick_fallback');
      const cachedPickedRaw = sessionStore.getPicked<unknown>();
      const cachedPicked = isValidPicked(cachedPickedRaw) ? cachedPickedRaw : null;

      let finalPicked: PickedPlace;
      if (isMockSession || isMockPick) {
        if (!ENABLE_MOCK_FALLBACK) {
          setPickedLoading(false);
          setIsDrawing(false);
          setPageError('当前环境已禁用本地兜底，请返回首页重新发起推荐。');
          return;
        }
        finalPicked = cachedPicked ?? randomMockPicked();
        sessionStore.setPicked(finalPicked);
        if (!pickId) sessionStore.setPickId(`mock_pick_fallback_${Date.now()}`);
      } else {
        if (cachedPicked && pickId) {
          finalPicked = cachedPicked;
          sessionStore.setPicked(finalPicked);
        } else {
          try {
            const res = await api.pick(sessionId);
            finalPicked = res.data.picked;
            sessionStore.setPicked(finalPicked);
            sessionStore.setPickId(res.data.pick_id);
            track('pick_drawn', { name: res.data.picked.name, type: res.data.picked.type }, sessionId, sessionStore.getDeviceId());
          } catch {
            if (!ENABLE_MOCK_FALLBACK) {
              setPickedLoading(false);
              setIsDrawing(false);
              setPageError('未找到有效抽签结果，请返回候选页重新抽签。');
              return;
            }
            finalPicked = randomMockPicked();
            sessionStore.setPicked(finalPicked);
            sessionStore.setPickId(`mock_pick_fallback_${Date.now()}`);
          }
        }
      }

      const basePool = normalizeDrawCards(sessionStore.getCandidatePool<DrawCard>(), {
        allowMockFallback: ENABLE_MOCK_FALLBACK,
        picked: finalPicked,
      });
      const foundIdx = findPickedCardIndex(basePool, finalPicked);
      const syncedPool = [...basePool];
      if (foundIdx < 0 || !syncedPool.some((c) => c.name === finalPicked.name)) {
        syncedPool[0] = {
          candidate_id: finalPicked.candidate_id || `picked_${Date.now()}`,
          name: finalPicked.name,
          type: finalPicked.type,
        };
      }

      const nextSettleIdx = findPickedCardIndex(syncedPool, finalPicked);
      setDrawCards(syncedPool);
      sessionStore.setCandidatePool(syncedPool);
      setSettleIndex(nextSettleIdx >= 0 ? nextSettleIdx : 0);
      setPicked(finalPicked);
      const waitMs = Math.max(0, 720 - (Date.now() - startedAt));
      if (waitMs > 0) {
        await new Promise((resolve) => setTimeout(resolve, waitMs));
      }
      setPickedLoading(false);
      setIsDrawing(true);
    };

    loadPicked();
    return () => {
      if (revealTimerRef.current) clearTimeout(revealTimerRef.current);
    };
  }, [navigate]);

  // 当抽卡结束、选中人格变化时，加载当前人格 review（celebrity:* 由 handleCelebrityClick 自行加载，跳过）
  useEffect(() => {
    if (!isDrawing && !selectedPersona.startsWith('celebrity:')) {
      loadPersonaReview(selectedPersona);
    }
  }, [selectedPersona, isDrawing, loadPersonaReview]);

  // 结果页挂载后预加载务实型（用于分享卡片第2条摘要）
  useEffect(() => {
    if (!isDrawing) {
      const preloadPersona = selectedPersona === '务实型' ? '独处型' : '务实型';
      loadPersonaReview(preloadPersona, false);
    }
  }, [isDrawing]); // eslint-disable-line react-hooks/exhaustive-deps

  const onFeedback = () => {
    const sessionId = sessionStore.getSessionId();
    if (!sessionId) return;
    track('feedback_entry_clicked', { persona: selectedPersona }, sessionId, sessionStore.getDeviceId());
    navigate('/feedback');
  };

  const handleNavigate = () => {
    if (!picked) return;
    track('nav_clicked', { name: picked.name }, sessionStore.getSessionId(), sessionStore.getDeviceId());
    const url = picked.nav_url || `https://uri.amap.com/search?keyword=${encodeURIComponent(picked.name)}&dev=0&style=2`;
    window.open(url, '_blank');
  };

  if (isDrawing) {
    if (pickedLoading) {
      return <ThinkingBridge />;
    }
    return (
      <DrawingAnimation
        cards={drawCards}
        settleIndex={settleIndex}
        onDone={() => {
          setIsDrawing(false);
          setIsRevealing(true);
          if (revealTimerRef.current) clearTimeout(revealTimerRef.current);
          revealTimerRef.current = setTimeout(() => setIsRevealing(false), 520);
        }}
      />
    );
  }

  if (isRevealing) {
    return <ResultRevealTransition />;
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#fefce8_0%,#ecfdf5_42%,#dcfce7_100%)]">
      <div className="max-w-2xl mx-auto px-5 py-8 space-y-8">
        {pageError && (
          <div className="rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {pageError}
          </div>
        )}

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center space-y-1"
        >
          <p className="text-xs text-[#6e6e73] tracking-widest uppercase">命运已拍板</p>
          <h1 className="text-[#1d1d1f] text-2xl font-bold tracking-tight">今天去这里</h1>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="bg-white/75 backdrop-blur-2xl rounded-3xl p-6 border border-amber-200/60 shadow-[0_14px_42px_rgba(180,83,9,0.16)]"
        >
          {pickedLoading ? (
            <div className="space-y-3">
              <div className="bg-black/8 h-6 rounded-2xl animate-pulse w-32" />
              <div className="bg-black/5 h-4 rounded-2xl animate-pulse w-48" />
              <div className="bg-black/5 h-16 rounded-2xl animate-pulse mt-4" />
            </div>
          ) : picked ? (
            <>
              <div className="flex items-start justify-between gap-3 mb-2">
                <h2 className="text-xl font-bold text-[#1d1d1f]">{picked.name}</h2>
                <span className="text-xs bg-black/5 text-[#6e6e73] px-3 py-1 rounded-full shrink-0 mt-0.5">
                  {picked.type}
                </span>
              </div>
              <div className="text-xs text-[#6e6e73] mb-4">
                {picked.transport_mode || '出行'}约{picked.eta_min}分钟
                {picked.distance_m ? ` · ${formatDistance(picked.distance_m)}` : ''}
                &nbsp;·&nbsp;{picked.budget_text}
              </div>
              <div className="bg-gradient-to-br from-emerald-50/80 to-cyan-50/60 rounded-2xl px-4 py-3 border border-emerald-100/60">
                <div className="text-xs tracking-widest text-emerald-700/70 mb-1.5">命运独白</div>
                <p className="text-sm leading-relaxed text-[#1d1d1f] italic">{picked.reason}</p>
              </div>
            </>
          ) : (
            <div className="text-sm text-amber-700">暂无可展示的抽签结果，请返回候选页重试。</div>
          )}
        </motion.div>

        {/* 地图预览 */}
        {picked?.location && sessionStore.getSessionId() && sessionStore.getPickId() && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.32 }}
            className="rounded-2xl overflow-hidden border border-black/8 shadow-sm cursor-pointer active:opacity-80 transition-opacity"
            onClick={handleNavigate}
          >
            <img
              src={`${API_BASE_URL}/map/preview?session_id=${sessionStore.getSessionId()}&pick_id=${sessionStore.getPickId()}`}
              alt="地图预览"
              className="w-full h-[160px] object-cover"
              onError={(e) => { (e.currentTarget.parentElement as HTMLElement).style.display = 'none'; }}
            />
            <div className="px-4 py-2.5 bg-white/80 backdrop-blur-sm flex items-center gap-2 text-xs text-[#6e6e73]">
              <MapPin className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>点击前往导航</span>
            </div>
          </motion.div>
        )}

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="space-y-4"
        >
          <div className="flex items-baseline gap-2">
            <h3 className="font-semibold text-[#1d1d1f]">人格试玩</h3>
            <span className="text-xs text-[#6e6e73]">选一个，调用 AI 评估这同一个地点</span>
          </div>
          {/* 名人视角行 */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-amber-700">★ 名人视角</span>
              <span className="text-[10px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full font-medium">PRO</span>
            </div>
            <div className="flex gap-2.5 overflow-x-auto pb-1 scrollbar-hide">
              {CELEBRITIES.map((celebrity) => (
                <CelebrityPersonaCard
                  key={celebrity.id}
                  celebrity={celebrity}
                  selected={selectedPersona === `celebrity:${celebrity.id}`}
                  unlocked={isPro()}
                  onClick={() => handleCelebrityClick(celebrity)}
                />
              ))}
              <div className="flex-shrink-0 flex items-center justify-center min-w-[80px] h-[76px] rounded-2xl border border-dashed border-slate-300 text-[10px] text-slate-400 px-2 text-center">
                🔜<br />更多即将<br />上线
              </div>
            </div>
          </div>

          <PersonaTabs personas={personas} defaultPersona={selectedPersona} onPersonaChange={handlePersonaChange} />

          <div className="min-h-[140px]">
            {reviewLoading ? (
              <div className="flex gap-3 overflow-hidden">
                {[1, 2].map((i) => (
                  <div key={i} className="flex-shrink-0 w-[200px] h-[120px] bg-white/70 rounded-2xl animate-pulse border border-white/50" />
                ))}
              </div>
            ) : reviewError ? (
              <div className="rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                {reviewError}
              </div>
            ) : review ? (
              <AnimatePresence mode="wait">
                <motion.div
                  key={selectedPersona}
                  initial={{ opacity: 0, x: 16 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -16 }}
                  transition={{ duration: 0.18, ease: 'easeOut' }}
                >
                  <PersonaSliceView slices={review.slices} />
                </motion.div>
              </AnimatePresence>
            ) : null}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="space-y-3 pb-8"
        >
          {/* 分享主按钮 */}
          <PrimaryButton
            onClick={() => picked && share(picked.name)}
            disabled={sharing || !shareReady}
          >
            <div className="flex items-center justify-center gap-2">
              {sharing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              {sharing ? '生成分享图…' : shareReady ? '✦ 分享这个命运' : '准备分享卡…'}
            </div>
          </PrimaryButton>

          {/* 次级操作 */}
          <div className="grid grid-cols-3 gap-2">
            <PrimaryButton variant="outline" onClick={handleNavigate}>
              <div className="flex items-center justify-center gap-1.5">
                <Navigation className="w-4 h-4" />
                导航
              </div>
            </PrimaryButton>
            <PrimaryButton
              variant="outline"
              onClick={() => {
                track('redraw_clicked', {}, sessionStore.getSessionId(), sessionStore.getDeviceId());
                navigate('/candidates');
              }}
            >
              <div className="flex items-center justify-center gap-1.5">
                <RotateCw className="w-4 h-4" />
                重抽
              </div>
            </PrimaryButton>
            <PrimaryButton variant="outline" onClick={onFeedback}>
              <div className="flex items-center justify-center gap-1.5">
                <MessageSquarePlus className="w-4 h-4" />
                反馈
              </div>
            </PrimaryButton>
          </div>
        </motion.div>
      </div>

      {/* 隐藏的分享卡片 DOM 节点，供 html2canvas 截图 */}
      {picked && (
        <ShareCardNode
          placeName={picked.name}
          placeType={picked.type}
          etaMin={picked.eta_min}
          transportMode={picked.transport_mode ?? '出行'}
          budgetText={picked.budget_text}
          destinyQuote={picked.reason}
          personaLabel1={selectedPersona}
          personaSummary1={shareReview1?.summary ?? shareReview1?.review ?? ''}
          personaLabel2={sharePersona2}
          personaSummary2={shareReview2?.summary ?? shareReview2?.review ?? ''}
        />
      )}
      <ProGateSheet open={proGateOpen} onClose={() => setProGateOpen(false)} />
    </div>
  );
}
