import { MapPin, ChevronDown, Loader2 } from 'lucide-react';

interface LocationBarProps {
  address?: string;        // 真实地名（逆地理编码后）
  locStatus?: 'idle' | 'ok' | 'denied';
  onSwitchClick?: () => void;
}

export function LocationBar({ address, locStatus, onSwitchClick }: LocationBarProps) {
  const label =
    locStatus === 'idle' ? '定位中…' :
    locStatus === 'denied' ? '未获取到定位' :
    address ? `${address}附近` :
    '当前位置附近';

  return (
    <div className="sticky top-0 z-20 flex items-center justify-between px-5 py-3.5 bg-white/80 backdrop-blur-2xl border-b border-black/8">
      <div className="flex items-center gap-1.5">
        {locStatus === 'idle'
          ? <Loader2 className="w-3.5 h-3.5 text-[#6e6e73] animate-spin" />
          : (
            <span className={`w-2 h-2 rounded-full ${locStatus === 'ok' ? 'bg-[#16a34a]' : 'bg-black/20'}`} />
          )
        }
        <span className="text-sm text-[#6e6e73]">{label}</span>
      </div>
      <button
        onClick={onSwitchClick}
        className="flex items-center gap-1 px-2.5 py-1 rounded-2xl hover:bg-black/5 transition-colors"
      >
        <span className="text-xs text-[#6e6e73]">切换</span>
        <ChevronDown className="w-3.5 h-3.5 text-[#6e6e73]" />
      </button>
    </div>
  );
}
