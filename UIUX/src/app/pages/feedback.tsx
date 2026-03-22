import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { Loader2, Star } from 'lucide-react';
import { PrimaryButton } from '../components/primary-button';
import { api } from '../lib/api';
import { sessionStore } from '../lib/session';
import { track } from '../lib/analytics';

interface PickedPlace {
  name: string;
  type: string;
  reason?: string;
}

const FEEDBACK_TAGS = ['值得再去', '适合独处', '适合聊天', '拍照好看', '踩雷', '太吵', '排队久', '性价比高'];
const RATING_LABELS: Record<number, string> = {
  1: '很差',
  2: '一般',
  3: '还行',
  4: '不错',
  5: '超预期',
};

function parseCost(raw: string): number | undefined {
  const num = Number(raw.trim());
  if (!Number.isFinite(num) || num < 0) return undefined;
  return Math.round(num);
}

export function Feedback() {
  const navigate = useNavigate();
  const sessionId = sessionStore.getSessionId();
  const pickId = sessionStore.getPickId();
  const picked = sessionStore.getPicked<PickedPlace>();
  const [went, setWent] = useState(true);
  const [satisfaction, setSatisfaction] = useState(4);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [actualCost, setActualCost] = useState('');
  const [transportUsed, setTransportUsed] = useState('骑车');
  const [tags, setTags] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const disabled = !sessionId || !pickId || submitting;
  const canSubmit = useMemo(() => {
    if (!sessionId || !pickId) return false;
    if (!went) return true;
    return content.trim().length >= 8;
  }, [content, went, sessionId, pickId]);

  const toggleTag = (tag: string) => {
    setTags((prev) => {
      if (prev.includes(tag)) return prev.filter((x) => x !== tag);
      if (prev.length >= 5) return prev;
      return [...prev, tag];
    });
  };

  const handleSubmit = async () => {
    if (!canSubmit || disabled) return;
    setError('');
    setSubmitting(true);
    try {
      await api.submitFeedback({
        sessionId,
        pickId,
        userId: sessionStore.getUserId() || sessionStore.getDeviceId(),
        went,
        satisfaction,
        actualCost: parseCost(actualCost),
        title: title.trim(),
        content: content.trim(),
        tags,
        transportUsed,
      });
      track('feedback_submitted', {
        went,
        satisfaction,
        tags_count: tags.length,
        has_content: Boolean(content.trim()),
      }, sessionId, sessionStore.getUserId() || sessionStore.getDeviceId());
      navigate('/history');
    } catch {
      setError('反馈提交失败，请稍后重试。');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f0fdf4]">
      <div className="max-w-2xl mx-auto px-5 py-8 pb-28 space-y-6">
        <div>
          <h1 className="text-xl font-bold text-[#1d1d1f]">去后反馈</h1>
          <p className="text-[#6e6e73] mt-1 text-sm">像写短评一样，告诉 AI 这次体验如何</p>
        </div>

        <div className="rounded-3xl border border-white/50 bg-white/75 backdrop-blur-2xl p-5 space-y-2">
          <div className="text-xs text-[#6e6e73]">本次地点</div>
          <div className="text-lg font-semibold text-[#1d1d1f]">{picked?.name || '本次抽签地点'}</div>
          <div className="text-sm text-[#6e6e73]">{picked?.type || '未分类'}</div>
          {picked?.reason ? (
            <p className="text-sm text-[#1d1d1f] bg-black/4 rounded-2xl p-3 mt-2">{picked.reason}</p>
          ) : null}
        </div>

        <div className="rounded-3xl border border-white/50 bg-white/75 backdrop-blur-2xl p-5 space-y-4">
          <div className="text-sm font-medium text-[#1d1d1f]">你真的去了吗？</div>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => setWent(true)}
              className={`rounded-2xl px-4 py-2.5 text-sm transition-colors ${went ? 'bg-[#16a34a] text-white' : 'bg-black/5 text-[#1d1d1f]'}`}
            >
              去了
            </button>
            <button
              onClick={() => setWent(false)}
              className={`rounded-2xl px-4 py-2.5 text-sm transition-colors ${!went ? 'bg-[#16a34a] text-white' : 'bg-black/5 text-[#1d1d1f]'}`}
            >
              没去
            </button>
          </div>
        </div>

        <div className="rounded-3xl border border-white/50 bg-white/75 backdrop-blur-2xl p-5 space-y-4">
          <div className="text-sm font-medium text-[#1d1d1f]">满意度</div>
          <div className="flex items-center gap-2">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                onClick={() => setSatisfaction(n)}
                className={`w-10 h-10 rounded-full inline-flex items-center justify-center transition-all ${
                  satisfaction >= n ? 'bg-amber-400 text-white shadow-[0_6px_16px_rgba(245,158,11,0.35)]' : 'bg-black/6 text-[#6e6e73]'
                }`}
                aria-label={`评分${n}`}
              >
                <Star className="w-4 h-4" />
              </button>
            ))}
            <span className="text-sm text-[#6e6e73] ml-2">{RATING_LABELS[satisfaction]}</span>
          </div>
        </div>

        <div className="rounded-3xl border border-white/50 bg-white/75 backdrop-blur-2xl p-5 space-y-4">
          <div className="text-sm font-medium text-[#1d1d1f]">短评</div>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="一句话标题（可选）"
            className="w-full rounded-2xl border border-black/10 bg-white/85 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-black/10"
          />
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder={went ? '写下真实体验，至少 8 个字…' : '没去的原因也可以写下来（可选）'}
            className="w-full min-h-[120px] rounded-2xl border border-black/10 bg-white/85 px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-black/10"
          />
          <div className="text-xs text-[#6e6e73] text-right">{content.trim().length}/2000</div>
        </div>

        <div className="rounded-3xl border border-white/50 bg-white/75 backdrop-blur-2xl p-5 space-y-4">
          <div className="text-sm font-medium text-[#1d1d1f]">标签（最多 5 个）</div>
          <div className="flex flex-wrap gap-2">
            {FEEDBACK_TAGS.map((tag) => {
              const active = tags.includes(tag);
              return (
                <button
                  key={tag}
                  onClick={() => toggleTag(tag)}
                  className={`rounded-full px-3 py-1.5 text-xs transition-colors ${active ? 'bg-[#16a34a] text-white' : 'bg-black/6 text-[#1d1d1f]'}`}
                >
                  {tag}
                </button>
              );
            })}
          </div>
        </div>

        <div className="rounded-3xl border border-white/50 bg-white/75 backdrop-blur-2xl p-5 space-y-3">
          <div className="text-sm font-medium text-[#1d1d1f]">补充信息（可选）</div>
          <div className="grid grid-cols-2 gap-3">
            <input
              value={actualCost}
              onChange={(e) => setActualCost(e.target.value)}
              placeholder="实际花费（元）"
              className="w-full rounded-2xl border border-black/10 bg-white/85 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-black/10"
            />
            <select
              value={transportUsed}
              onChange={(e) => setTransportUsed(e.target.value)}
              className="w-full rounded-2xl border border-black/10 bg-white/85 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-black/10"
            >
              <option value="步行">步行</option>
              <option value="骑车">骑车</option>
              <option value="地铁">地铁</option>
              <option value="打车">打车</option>
              <option value="其他">其他</option>
            </select>
          </div>
        </div>

        {error ? (
          <div className="rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {error}
          </div>
        ) : null}
      </div>

      <div className="fixed bottom-16 left-0 right-0 px-5 z-10">
        <div className="bg-gradient-to-t from-[#f0fdf4]/95 to-transparent pb-3 pt-4">
          <div className="max-w-2xl mx-auto space-y-2">
            <PrimaryButton onClick={handleSubmit} disabled={!canSubmit || disabled}>
              <span className="inline-flex items-center justify-center gap-2">
                {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                {submitting ? '提交中…' : '提交这次反馈'}
              </span>
            </PrimaryButton>
            <PrimaryButton variant="outline" onClick={() => navigate('/result')} disabled={submitting}>
              返回结果页
            </PrimaryButton>
          </div>
        </div>
      </div>
    </div>
  );
}
