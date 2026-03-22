import { useState, useEffect, useRef } from 'react';
import { Navigation, RotateCw, Bookmark, Sparkles } from 'lucide-react';
import { PersonaTabs } from '../components/persona-tabs';
import { PersonaReviewCard } from '../components/persona-review-card';
import { PrimaryButton } from '../components/primary-button';
import { motion, AnimatePresence } from 'motion/react';
import { api } from '../lib/api';
import { sessionStore } from '../lib/session';
import { useNavigate } from 'react-router';
import { mockPlaces, personaReviews } from '../lib/mock-data';
import { track } from '../lib/analytics';

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
}

interface ReviewData {
  persona: string;
  review: string;
  risk: string;
  conclusion: string;
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

function normalizeDrawCards(cards: DrawCard[]): DrawCard[] {
  const cleaned = cards
    .filter((c) => c && c.name && c.type)
    .slice(0, 10)
    .map((c, i) => ({
      candidate_id: c.candidate_id || `candidate_${i}`,
      name: c.name,
      type: c.type,
    }));

  if (cleaned.length >= 10) return cleaned;

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
  if (!picked) return base;
  return {
    ...base,
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
  const [revealed, setRevealed] = useState(false);
  const [finalized, setFinalized] = useState(false);
  const [showFinalCard, setShowFinalCard] = useState(false);
  const tickerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const revealRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const finalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const doneRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const n = cards.length;
    if (!n) {
      onDone();
      return;
    }

    const target = Math.max(0, Math.min(settleIndex, n - 1));
    let idx = 0;
    let settleHitCount = 0;
    let ticks = 0;

    tickerRef.current = setInterval(() => {
      ticks += 1;
      idx = (idx + 1) % n;
      setActiveIdx(idx);

      if (idx === target && ticks > n) {
        settleHitCount += 1;
      }

      if (settleHitCount >= 2) {
        if (tickerRef.current) clearInterval(tickerRef.current);
        setFinalized(true);
        setRevealed(true);
        if (navigator.vibrate) navigator.vibrate(80);
        finalRef.current = setTimeout(() => setShowFinalCard(true), 130);
        doneRef.current = setTimeout(onDone, 1150);
      }
    }, 120);

    revealRef.current = setTimeout(() => setRevealed(true), 1600);

    return () => {
      if (tickerRef.current) clearInterval(tickerRef.current);
      if (revealRef.current) clearTimeout(revealRef.current);
      if (finalRef.current) clearTimeout(finalRef.current);
      if (doneRef.current) clearTimeout(doneRef.current);
    };
  }, [cards, settleIndex, onDone]);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_50%_15%,#3f3f46_0%,#111827_42%,#020617_100%)] relative overflow-hidden flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_70%,rgba(245,158,11,0.25),transparent_55%)]" />
      <div className="relative z-10 w-full max-w-[440px] space-y-6">
        <AnimatePresence mode="wait">
          {!finalized ? (
            <motion.p
              key="drawing"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="text-center text-[11px] tracking-[0.28em] uppercase text-amber-100"
            >
              Destiny Deck Shuffling
            </motion.p>
          ) : (
            <motion.p
              key="done"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center text-[11px] tracking-[0.28em] uppercase text-emerald-100"
            >
              Card Locked
            </motion.p>
          )}
        </AnimatePresence>

        <div className="grid grid-cols-5 gap-2 sm:gap-3">
          {cards.map((card, idx) => {
            const isActive = idx === activeIdx;
            const isWinner = finalized && idx === settleIndex;
            return (
              <motion.div
                key={card.candidate_id}
                animate={{
                  y: isActive ? -6 : 0,
                  scale: isWinner ? 1.08 : isActive ? 1.03 : 1,
                  boxShadow: isWinner
                    ? '0 12px 32px rgba(16,185,129,0.35)'
                    : isActive
                      ? '0 8px 24px rgba(245,158,11,0.24)'
                      : '0 4px 12px rgba(0,0,0,0.18)',
                }}
                transition={{ duration: 0.16, ease: 'easeOut' }}
                className="aspect-[3/4] rounded-xl border border-white/20 overflow-hidden"
              >
                {isWinner ? (
                  <div className="h-full w-full bg-gradient-to-b from-emerald-200/35 via-emerald-100/20 to-emerald-950/70 p-2 flex flex-col justify-between">
                    <Sparkles className="w-3.5 h-3.5 text-emerald-100" />
                    <div>
                      <div className="text-[9px] text-emerald-50/90 line-clamp-2 leading-tight">{card.name}</div>
                      <div className="text-[8px] text-emerald-100/75 mt-1">{card.type}</div>
                    </div>
                  </div>
                ) : (
                  <div className="h-full w-full bg-gradient-to-b from-amber-200/15 via-white/10 to-slate-900/70 flex items-center justify-center">
                    <div className="text-[11px] tracking-[0.25em] text-amber-100/80">ARCANA</div>
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>

        <p className="text-center text-xs text-slate-200/90">
          {revealed ? '命运卡已锁定，正在同步本次地点…' : '正在从 10 张命运卡中抽取本次去处…'}
        </p>
      </div>

      <AnimatePresence>
        {showFinalCard && cards[settleIndex] && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-20 flex items-center justify-center bg-black/35 backdrop-blur-[2px] pointer-events-none"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.78, rotateY: 0, y: 16 }}
              animate={{ opacity: 1, scale: 1.2, rotateY: 180, y: 0 }}
              transition={{ duration: 0.42, ease: 'easeOut' }}
              className="w-[150px] h-[220px] rounded-2xl [transform-style:preserve-3d]"
            >
              <div className="absolute inset-0 rounded-2xl [backface-visibility:hidden] border border-amber-100/55 bg-gradient-to-b from-amber-200/30 via-white/15 to-slate-900/75 flex items-center justify-center">
                <div className="text-sm tracking-[0.26em] text-amber-100/90">ARCANA</div>
              </div>
              <div className="absolute inset-0 rounded-2xl [backface-visibility:hidden] [transform:rotateY(180deg)] border border-emerald-100/65 bg-gradient-to-b from-emerald-200/40 via-emerald-100/20 to-emerald-950/75 p-3 flex flex-col justify-between shadow-[0_20px_45px_rgba(16,185,129,0.4)]">
                <Sparkles className="w-4 h-4 text-emerald-100" />
                <div>
                  <div className="text-xs text-emerald-50 line-clamp-3 leading-tight">{cards[settleIndex].name}</div>
                  <div className="text-[10px] text-emerald-100/85 mt-1">{cards[settleIndex].type}</div>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function Result() {
  const navigate = useNavigate();
  const [isDrawing, setIsDrawing] = useState(true);
  const [selectedPersona, setSelectedPersona] = useState('独处型');
  const [review, setReview] = useState<ReviewData | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [picked, setPicked] = useState<PickedPlace | null>(null);
  const [pickedLoading, setPickedLoading] = useState(true);
  const [drawCards, setDrawCards] = useState<DrawCard[]>(() =>
    normalizeDrawCards(sessionStore.getCandidatePool<DrawCard>()),
  );
  const [settleIndex, setSettleIndex] = useState(0);

  const personas = ['独处型', '探索型', '务实型', '审美型', '老饕', '效率党', '精算师', '氛围感'];

  const handlePersonaChange = (persona: string) => {
    setSelectedPersona(persona);
    track('persona_tab_clicked', { persona }, sessionStore.getSessionId(), sessionStore.getDeviceId());
  };

  useEffect(() => {
    const loadPicked = async () => {
      const sessionId = sessionStore.getSessionId();
      if (!sessionId) {
        navigate('/');
        return;
      }

      const pickId = sessionStore.getPickId();
      const isMockSession = sessionId.startsWith('mock_session_fallback');
      const isMockPick = pickId.startsWith('mock_pick_fallback');

      let finalPicked: PickedPlace;
      if (isMockSession || isMockPick) {
        finalPicked = sessionStore.getPicked<PickedPlace>() ?? randomMockPicked();
        sessionStore.setPicked(finalPicked);
        if (!pickId) sessionStore.setPickId(`mock_pick_fallback_${Date.now()}`);
      } else {
        finalPicked = sessionStore.getPicked<PickedPlace>() ?? randomMockPicked();
        sessionStore.setPicked(finalPicked);
      }

      const basePool = normalizeDrawCards(sessionStore.getCandidatePool<DrawCard>());
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
      setPickedLoading(false);
    };

    loadPicked();
  }, [navigate]);

  useEffect(() => {
    const loadReview = async () => {
      const sessionId = sessionStore.getSessionId();
      const pickId = sessionStore.getPickId();
      if (!sessionId || !pickId) return;

      setReviewLoading(true);
      try {
        const reviewRes = await api.personaReview(sessionId, pickId, selectedPersona);
        setReview(reviewRes.data);
      } catch {
        setReview(buildFallbackReview(selectedPersona, picked));
      } finally {
        setReviewLoading(false);
      }
    };

    if (!isDrawing) loadReview();
  }, [selectedPersona, isDrawing, picked]);

  const onFeedback = async () => {
    const sessionId = sessionStore.getSessionId();
    const pickId = sessionStore.getPickId();
    if (sessionId && pickId) {
      try {
        await api.submitFeedback(sessionId, pickId, sessionStore.getDeviceId(), selectedPersona, 4);
      } catch {
        // 静默失败，不影响导航
      }
      track('feedback_submitted', { satisfaction: 4, persona: selectedPersona }, sessionId, sessionStore.getDeviceId());
      navigate('/history');
    }
  };

  const handleNavigate = () => {
    if (!picked) return;
    track('nav_clicked', { name: picked.name }, sessionStore.getSessionId(), sessionStore.getDeviceId());
    const url = picked.nav_url || `https://uri.amap.com/search?keyword=${encodeURIComponent(picked.name)}&dev=0&style=2`;
    window.open(url, '_blank');
  };

  if (isDrawing) {
    return (
      <DrawingAnimation
        cards={drawCards}
        settleIndex={settleIndex}
        onDone={() => setIsDrawing(false)}
      />
    );
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#fefce8_0%,#ecfdf5_42%,#dcfce7_100%)]">
      <div className="max-w-2xl mx-auto px-5 py-8 space-y-8">
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
              <div className="bg-black/4 rounded-2xl px-4 py-3">
                <div className="text-xs uppercase tracking-widest text-[#6e6e73] mb-1.5">入选理由</div>
                <p className="text-sm leading-relaxed text-[#1d1d1f]">{picked.reason}</p>
              </div>
            </>
          ) : null}
        </motion.div>

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
          <PersonaTabs personas={personas} defaultPersona={selectedPersona} onPersonaChange={handlePersonaChange} />

          <div className="min-h-[140px]">
            {reviewLoading ? (
              <div className="bg-white/70 backdrop-blur-2xl rounded-3xl p-5 border border-white/50 space-y-3">
                <div className="bg-black/8 h-4 rounded-2xl animate-pulse w-3/4" />
                <div className="bg-black/8 h-4 rounded-2xl animate-pulse w-1/2" />
                <div className="bg-black/5 h-4 rounded-2xl animate-pulse w-2/3 mt-4" />
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
                  <PersonaReviewCard review={review} />
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
          <PrimaryButton onClick={handleNavigate}>
            <div className="flex items-center justify-center gap-2">
              <Navigation className="w-5 h-5" />
              去导航
            </div>
          </PrimaryButton>
          <div className="grid grid-cols-2 gap-3">
            <PrimaryButton
              variant="outline"
              onClick={() => {
                track('redraw_clicked', {}, sessionStore.getSessionId(), sessionStore.getDeviceId());
                navigate('/candidates');
              }}
            >
              <div className="flex items-center justify-center gap-2">
                <RotateCw className="w-4 h-4" />
                重新抽
              </div>
            </PrimaryButton>
            <PrimaryButton variant="outline" onClick={onFeedback}>
              <div className="flex items-center justify-center gap-2">
                <Bookmark className="w-4 h-4" />
                提交反馈
              </div>
            </PrimaryButton>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
