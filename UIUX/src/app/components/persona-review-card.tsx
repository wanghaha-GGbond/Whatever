import { PersonaReview } from '../types';

interface PersonaReviewCardProps {
  review: PersonaReview;
}

export function PersonaReviewCard({ review }: PersonaReviewCardProps) {
  return (
    <div className="bg-white/70 backdrop-blur-2xl rounded-3xl p-5 border border-white/50 shadow-[0_8px_32px_rgba(0,0,0,0.08)] space-y-4">
      <div>
        <div className="text-xs text-[#6e6e73] uppercase tracking-widest mb-1.5">体验</div>
        <p className="text-sm text-[#1d1d1f] leading-relaxed">{review.review}</p>
      </div>

      <div>
        <div className="text-xs text-[#6e6e73] uppercase tracking-widest mb-1.5">风险</div>
        <p className="text-sm text-[#1d1d1f]/70 leading-relaxed">{review.risk}</p>
      </div>

      <div className="pt-3 border-t border-black/8 flex items-center justify-between">
        <div className="text-xs text-[#6e6e73] uppercase tracking-widest">结论</div>
        <p className="text-base font-semibold text-[#1d1d1f]">{review.conclusion}</p>
      </div>
    </div>
  );
}
