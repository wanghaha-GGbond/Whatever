// UIUX/src/app/components/persona-slice-view.tsx
import { useRef } from 'react';
import type { PersonaSlice } from '../types';

const SCENE_EMOJI: Record<string, string> = {
  to_door: '🚶',
  enter:   '🌳',
  during:  '🎯',
  leave:   '🚪',
};

interface PersonaSliceViewProps {
  slices: PersonaSlice[];
}

export function PersonaSliceView({ slices }: PersonaSliceViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  if (!slices || slices.length === 0) {
    return (
      <div className="bg-white/70 backdrop-blur-2xl rounded-3xl p-5 border border-white/50 text-sm text-[#6e6e73]">
        切片加载中…
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* 横向滑动区 */}
      <div
        ref={scrollRef}
        className="flex gap-3 overflow-x-auto pb-2 snap-x snap-mandatory"
        style={{ scrollbarWidth: 'none' }}
      >
        {slices.map((slice, idx) => (
          <div
            key={slice.scene}
            className="flex-shrink-0 w-[200px] bg-white/80 backdrop-blur rounded-2xl p-4 border border-black/8 shadow-[0_2px_12px_rgba(0,0,0,0.06)] snap-start"
          >
            {/* Scene tag */}
            <div className="inline-flex items-center gap-1 bg-[#dcfce7] text-[#16a34a] text-[10px] rounded px-2 py-0.5 mb-3">
              <span>{SCENE_EMOJI[slice.scene] ?? '📍'}</span>
              <span>{slice.tag}</span>
            </div>

            {/* Text */}
            <p className="text-sm text-[#1d1d1f] leading-relaxed mb-3">
              {slice.text || '—'}
            </p>

            {/* Emotion tag + progress */}
            <div className="flex items-center justify-between">
              {slice.emotion ? (
                <span className="text-[10px] bg-[#f1f5f9] text-[#6e6e73] rounded px-2 py-0.5">
                  {slice.emotion}
                </span>
              ) : <span />}
              <span className="text-[10px] text-[#9ca3af]">{idx + 1} / {slices.length}</span>
            </div>
          </div>
        ))}
      </div>

      {/* 滑动指示点 */}
      <div className="flex justify-center gap-1.5">
        {slices.map((slice) => (
          <div
            key={slice.scene}
            className="h-[3px] rounded-full bg-[#d1d5db]"
            style={{ width: slice.scene === 'to_door' ? '20px' : '8px' }}
          />
        ))}
      </div>
    </div>
  );
}
