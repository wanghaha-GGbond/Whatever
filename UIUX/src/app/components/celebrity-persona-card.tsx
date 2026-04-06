import type { Celebrity } from '../lib/celebrities';

interface CelebrityPersonaCardProps {
  celebrity: Celebrity;
  selected: boolean;
  unlocked: boolean;
  onClick: () => void;
}

export function CelebrityPersonaCard({ celebrity, selected, unlocked, onClick }: CelebrityPersonaCardProps) {
  return (
    <button
      onClick={onClick}
      className={[
        'flex-shrink-0 flex flex-col items-center gap-1 px-4 py-3 rounded-2xl min-w-[88px] transition-all',
        'border',
        selected && unlocked
          ? 'bg-gradient-to-b from-[#2c2c2e] to-[#1c1c1e] border-emerald-400/60 shadow-[0_0_12px_rgba(52,211,153,0.3)]'
          : 'bg-gradient-to-b from-[#2c2c2e] to-[#1c1c1e] border-[#48484a]/80',
      ].join(' ')}
    >
      <span className="text-xl leading-none">{celebrity.emoji}</span>
      <span className="text-[12px] font-semibold text-white leading-tight">{celebrity.name}</span>
      <span className="text-[9px] text-[#8e8e93] leading-tight">{celebrity.nameEn}</span>
      {!unlocked && (
        <span className="mt-1 text-[9px] bg-amber-500 text-white px-1.5 py-0.5 rounded-full font-medium">
          🔒 PRO
        </span>
      )}
      {unlocked && selected && (
        <span className="mt-1 text-[9px] bg-emerald-500 text-white px-1.5 py-0.5 rounded-full font-medium">
          ✓ 已选
        </span>
      )}
    </button>
  );
}
