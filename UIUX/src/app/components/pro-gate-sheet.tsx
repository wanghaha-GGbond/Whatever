import { X, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface ProGateSheetProps {
  open: boolean;
  onClose: () => void;
}

export function ProGateSheet({ open, onClose }: ProGateSheetProps) {
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
            onClick={onClose}
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
              <button onClick={onClose} className="text-[#6e6e73] hover:text-[#1d1d1f] transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-sm text-[#6e6e73] mb-6 leading-relaxed">
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

            <button
              disabled
              className="w-full py-3.5 rounded-2xl bg-gradient-to-r from-amber-400 to-amber-500 text-white font-semibold text-sm opacity-60 cursor-not-allowed"
            >
              即将开放 · 敬请期待
            </button>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
