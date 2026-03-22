import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { LocationBar } from '../components/location-bar';
import { ChipGroup } from '../components/chip-group';
import { PrimaryButton } from '../components/primary-button';
import { Mic, Loader2, RotateCw, MapPin } from 'lucide-react';
import { api } from '../lib/api';
import { sessionStore } from '../lib/session';
import { track } from '../lib/analytics';
import { ENABLE_MOCK_FALLBACK } from '../lib/env';

// 获取用户位置，返回 "lng,lat" 字符串，超时或拒绝返回 undefined
function getLocation(): Promise<string | undefined> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) { resolve(undefined); return; }
    const timer = setTimeout(() => resolve(undefined), 5000);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        clearTimeout(timer);
        resolve(`${pos.coords.longitude.toFixed(6)},${pos.coords.latitude.toFixed(6)}`);
      },
      () => { clearTimeout(timer); resolve(undefined); },
      { timeout: 5000, maximumAge: 60000 },
    );
  });
}

export function Home() {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [voiceToast, setVoiceToast] = useState(false);
  const [locStatus, setLocStatus] = useState<'idle' | 'ok' | 'denied'>('idle');
  const [addressName, setAddressName] = useState('');
  const [manualLocation, setManualLocation] = useState('');
  const [manualLocationVisible, setManualLocationVisible] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const voiceToastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const locationRef = useRef<string | undefined>(undefined);

  // 页面加载后静默获取位置（不阻塞提交）
  useEffect(() => {
    const existingUserId = sessionStore.getUserId();
    api.authAnonymous(existingUserId || undefined)
      .then((res) => {
        if (res.data.user_id) {
          sessionStore.setUserId(res.data.user_id);
        }
      })
      .catch(() => {
        // 匿名身份初始化失败不阻塞主流程
      });

    getLocation().then(async (loc) => {
      locationRef.current = loc;
      setLocStatus(loc ? 'ok' : 'denied');
      if (!loc) return;
      try {
        const res = await api.resolveLocation(loc);
        if (res.data.address_name) setAddressName(res.data.address_name);
      } catch {
        // 地址反查失败不阻断主流程
      }
    });
  }, []);

  // Chip selections
  const [scene, setScene] = useState('');
  const [sceneCustom, setSceneCustom] = useState('');
  const [transport, setTransport] = useState('');
  const [transportCustom, setTransportCustom] = useState('');
  const [budget, setBudget] = useState('');
  const [atmosphere, setAtmosphere] = useState<string[]>([]);
  const [atmosphereCustom, setAtmosphereCustom] = useState('');

  const buildFinalPrompt = () => {
    const parts: string[] = [];
    if (scene) parts.push(scene);
    if (sceneCustom.trim()) parts.push(sceneCustom.trim());
    if (transport) parts.push(transport);
    if (transportCustom.trim()) parts.push(transportCustom.trim());
    if (atmosphere.length > 0) parts.push(...atmosphere);
    if (atmosphereCustom.trim()) parts.push(atmosphereCustom.trim());
    const base = prompt.trim();
    if (parts.length === 0 && !budget.trim()) return base || '随便推一个';
    const suffix: string[] = [];
    if (parts.length > 0) suffix.push(`偏好：${parts.join('，')}`);
    if (budget.trim()) suffix.push(`预算 ${budget.trim()}`);
    return `${base}（${suffix.join('，')}）`;
  };

  const handleSubmit = async () => {
    setLoading(true);
    setSubmitError('');
    let shouldNavigate = false;
    try {
      const finalPrompt = buildFinalPrompt();
      const manual = manualLocation.trim();
      const loc = manual || locationRef.current || undefined;
      const userId = sessionStore.getUserId() || sessionStore.getDeviceId();
      const res = await api.initRecommendation(finalPrompt, loc, userId);
      if (res.data.user_id) {
        sessionStore.setUserId(res.data.user_id);
      }
      sessionStore.setSessionId(res.data.session_id);
      sessionStore.setPickId('');
      sessionStore.setPicked({});
      track('session_start', { prompt: finalPrompt }, res.data.session_id, sessionStore.getDeviceId());
      if (res.data.address_name) {
        setAddressName(res.data.address_name);
      } else if (manual) {
        setAddressName(manual);
      }
      shouldNavigate = true;
    } catch {
      if (ENABLE_MOCK_FALLBACK) {
        const fallbackSessionId = `mock_session_fallback_${Date.now()}`;
        sessionStore.setSessionId(fallbackSessionId);
        sessionStore.setPickId('');
        sessionStore.setPicked({});
        setSubmitError('服务暂不可用，已切到本地候选模式。');
        shouldNavigate = true;
      } else {
        setSubmitError('服务暂不可用，请稍后重试。');
      }
    } finally {
      setLoading(false);
      if (shouldNavigate) navigate('/candidates');
    }
  };

  const handleVoice = () => {
    if (voiceToastTimer.current) clearTimeout(voiceToastTimer.current);
    setVoiceToast(true);
    voiceToastTimer.current = setTimeout(() => setVoiceToast(false), 2800);
  };

  return (
    <div className="min-h-screen bg-[#f0fdf4]">
      <LocationBar
        address={addressName}
        locStatus={locStatus}
        onSwitchClick={() => setManualLocationVisible((v) => !v)}
      />

      {/* 定位状态条 */}
      {(locStatus === 'denied' || manualLocationVisible) && (
        <div className="bg-white/70 backdrop-blur border-b border-black/8 px-5 py-3 space-y-2">
          <div className="flex items-center gap-2">
            <MapPin className="w-3.5 h-3.5 text-[#6e6e73] shrink-0" />
            <span className="text-xs text-[#6e6e73]">可手动输入你的位置，提交时优先生效</span>
          </div>
          <input
            type="text"
            value={manualLocation}
            onChange={(e) => setManualLocation(e.target.value)}
            placeholder="输入地址或地名，如：徐家汇、南京西路"
            className="w-full px-3 py-2 text-xs rounded-2xl border border-black/10 bg-white/80 backdrop-blur focus:outline-none focus:ring-2 focus:ring-black/10 transition-all"
          />
        </div>
      )}

      {submitError && (
        <div className="px-5 pt-3">
          <div className="max-w-2xl mx-auto text-xs text-[#b45309] bg-[#fef3c7] border border-[#fcd34d] rounded-2xl px-3 py-2">
            {submitError}
          </div>
        </div>
      )}

      <div className="max-w-2xl mx-auto px-5 pt-8 pb-36 space-y-8">
        {/* 标题区 */}
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-bold tracking-tight text-[#1d1d1f]">今天想去哪？</h1>
          <p className="text-[#6e6e73] text-sm">说一句你的状态，AI 帮你定一个地方</p>
        </div>

        {/* 主输入框 */}
        <div className="relative">
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="骑车20分钟内，适合一个人安静待会…"
            className="w-full px-5 py-4 pr-14 rounded-2xl bg-white/80 backdrop-blur border border-black/10 shadow-[0_8px_32px_rgba(0,0,0,0.08)] focus:outline-none focus:ring-2 focus:ring-black/10 transition-all text-sm text-[#1d1d1f] placeholder:text-[#6e6e73]"
          />
          <button
            onClick={handleVoice}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-xl hover:bg-black/5 transition-colors"
          >
            <Mic className="w-5 h-5 text-[#6e6e73]" />
          </button>
          {/* 语音 toast */}
          {voiceToast && (
            <div className="absolute top-full mt-2 left-0 right-0 bg-[#16a34a] text-white text-xs text-center py-2 px-4 rounded-2xl shadow-lg z-20 transition-opacity">
              语音输入即将上线，先手打吧
            </div>
          )}
        </div>

        {/* 筛选区 */}
        <div className="space-y-4">
          <ChipGroup
            label="场景"
            options={['独处', '约会', '朋友']}
            onSelectionChange={(v) => setScene(v as string)}
            customPlaceholder="补充描述，例如：带小孩、老人同行…"
            onCustomChange={setSceneCustom}
          />
          <ChipGroup
            label="通勤"
            options={['步行', '骑车', '地铁']}
            onSelectionChange={(v) => setTransport(v as string)}
            customPlaceholder="补充描述，例如：最多20分钟、不想爬坡…"
            onCustomChange={setTransportCustom}
          />
          {/* 预算：文字输入框 */}
          <div className="space-y-2">
            <div className="text-xs text-[#6e6e73] font-medium tracking-wide">预算</div>
            <input
              type="text"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              placeholder="例如：50元以内、不限、¥30左右"
              className="w-full px-4 py-2.5 rounded-2xl bg-white/80 backdrop-blur border border-black/10 text-sm text-[#1d1d1f] placeholder:text-[#6e6e73] focus:outline-none focus:ring-2 focus:ring-black/10 transition-all"
            />
          </div>
          <ChipGroup
            label="氛围"
            options={['安静', '热闹', '有新鲜感', '好看']}
            multiSelect
            onSelectionChange={(v) => setAtmosphere(v as string[])}
            customPlaceholder="补充描述，例如：有水、有树、适合拍照…"
            onCustomChange={setAtmosphereCustom}
          />
        </div>

        {/* 最近一次记录卡片（静态 mock） */}
        <div className="bg-white/70 backdrop-blur-2xl rounded-3xl p-5 border border-white/50 shadow-[0_8px_32px_rgba(0,0,0,0.08)]">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-[#6e6e73] mb-0.5">上次去了</div>
              <div className="text-sm font-semibold text-[#1d1d1f]">上生新所</div>
              <div className="text-xs text-[#6e6e73] mt-0.5">周六 16:20</div>
            </div>
            <button
              onClick={() => navigate('/candidates')}
              className="text-xs text-[#1d1d1f] bg-black/5 rounded-2xl px-3 py-1.5 hover:bg-black/10 transition-colors flex items-center gap-1"
            >
              <RotateCw className="w-3 h-3" />
              再抽一次
            </button>
          </div>
        </div>
      </div>

      {/* CTA 固定底部 */}
      <div className="fixed bottom-16 left-0 right-0 z-10">
        <div className="bg-gradient-to-t from-[#f0fdf4]/95 to-transparent pb-3 pt-4 px-5">
          <div className="max-w-2xl mx-auto">
            <PrimaryButton onClick={handleSubmit} disabled={loading}>
              <div className="flex items-center justify-center gap-2">
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                {loading ? 'AI 选址中…' : '帮我选一个'}
              </div>
            </PrimaryButton>
          </div>
        </div>
      </div>
    </div>
  );
}
