import { useState } from 'react';
import { X, Sparkles, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { api } from '../lib/api';
import { setPro } from '../lib/pro';

interface ProGateSheetProps {
  open: boolean;
  onClose: () => void;
  onActivated?: () => void;
}

type Status = 'idle' | 'loading' | 'error' | 'success';

export function ProGateSheet({ open, onClose, onActivated }: ProGateSheetProps) {
  const [code, setCode] = useState('');
  const [status, setStatus] = useState<Status>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  const handleActivate = async () => {
    const trimmed = code.trim();
    if (!trimmed) return;
    setStatus('loading');
    setErrorMsg('');
    try {
      await api.activatePro(trimmed);
      setPro(true);
      setStatus('success');
      setTimeout(() => {
        onActivated?.();
        onClose();
        setStatus('idle');
        setCode('');
      }, 900);
    } catch {
      setStatus('error');
      setErrorMsg('邀请码无效，请确认后重试');
    }
  };

  const handleClose = () => {
    if (status === 'loading') return;
    onClose();
    setStatus('idle');
    setCode('');
    setErrorMsg('');
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/40 z-40"
            onClick={handleClose}
          />
          {/* Sheet */}
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 280 }}
            className="fixed bottom-0 left-0 right-0 z-50 bg-white rounded-t-3xl px-6 pt-5 pb-10 shadow-2xl max-w-2xl mx-auto"
          >
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-amber-500" />
                <span className="font-bold text-[#1d1d1f] text-lg">解锁名人视角</span>
              </div>
              <button
                onClick={handleClose}
                disabled={status === 'loading'}
                className="text-[#6e6e73] hover:text-[#1d1d1f] transition-colors disabled:opacity-40"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-sm text-[#6e6e73] mb-5 leading-relaxed">
              订阅 <span className="font-semibold text-[#1d1d1f]">WHATEVER PRO</span>，以历史名人、商业领袖的视角重新审视你的命运之地。
            </p>

            <div className="space-y-3 mb-6">
              {[
                { emoji: '👔', label: '乔布斯 Steve Jobs', desc: '用技术×人文的眼光评价每一个地方' },
                { emoji: '🔜', label: '更多名人', desc: '持续解锁，即将上线' },
                { emoji: '∞', label: '无限人格切换', desc: '8 个免费人格无限次使用' },
              ].map((item) => (
                <div key={item.label} className="flex items-start gap-3">
                  <span className="text-lg leading-none mt-0.5">{item.emoji}</span>
                  <div>
                    <div className="text-sm font-medium text-[#1d1d1f]">{item.label}</div>
                    <div className="text-xs text-[#6e6e73]">{item.desc}</div>
                  </div>
                </div>
              ))}
            </div>

            {/* 邀请码输入区 */}
            <div className="mb-3">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={code}
                  onChange={(e) => {
                    setCode(e.target.value);
                    if (status === 'error') setStatus('idle');
                  }}
                  onKeyDown={(e) => e.key === 'Enter' && handleActivate()}
                  placeholder="输入邀请码"
                  disabled={status === 'loading' || status === 'success'}
                  className={[
                    'flex-1 px-4 py-3 rounded-xl border text-sm outline-none transition-colors',
                    status === 'error'
                      ? 'border-red-400 bg-red-50 text-red-700 placeholder:text-red-300'
                      : 'border-[#e5e5ea] bg-[#f5f5f7] text-[#1d1d1f] placeholder:text-[#aeaeb2]',
                    'focus:border-amber-400 focus:bg-white',
                    'disabled:opacity-50',
                  ].join(' ')}
                />
                <button
                  onClick={handleActivate}
                  disabled={!code.trim() || status === 'loading' || status === 'success'}
                  className="px-5 py-3 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 text-white font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-opacity flex items-center gap-1.5"
                >
                  {status === 'loading' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : status === 'success' ? (
                    '✓'
                  ) : (
                    '激活'
                  )}
                </button>
              </div>
              {status === 'error' && (
                <p className="text-xs text-red-500 mt-1.5 pl-1">{errorMsg}</p>
              )}
              {status === 'success' && (
                <p className="text-xs text-green-600 mt-1.5 pl-1 font-medium">已解锁 PRO，享受名人视角！</p>
              )}
            </div>

            <p className="text-xs text-[#aeaeb2] text-center">
              没有邀请码？联系开发者获取内测资格
            </p>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
