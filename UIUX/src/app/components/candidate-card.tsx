import { AlertTriangle } from 'lucide-react';
import { Place } from '../types';

interface CandidateCardProps {
  place: Place;
}

export function CandidateCard({ place }: CandidateCardProps) {
  return (
    <div className="bg-white/70 backdrop-blur-2xl rounded-3xl p-5 border border-white/50 shadow-[0_8px_32px_rgba(0,0,0,0.08)] hover:shadow-[0_12px_40px_rgba(0,0,0,0.12)] transition-all">
      <div className="flex items-start justify-between gap-3 mb-1.5">
        <h3 className="font-semibold text-[#1d1d1f]">{place.name}</h3>
        <span className="text-xs text-[#6e6e73] bg-black/5 px-3 py-1 rounded-full shrink-0 mt-0.5">{place.type}</span>
      </div>
      <div className="flex items-center gap-1.5 text-xs text-[#6e6e73] mb-3">
        <span>{place.distance}</span>
        <span>·</span>
        <span>{place.budget}</span>
      </div>
      <p className="text-sm text-[#1d1d1f]/75 leading-relaxed mb-3">{place.aiJudgement}</p>
      {place.riskLabel && (
        <div className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-black/5 text-[#6e6e73] text-xs">
          <AlertTriangle className="w-3 h-3" />
          {place.riskLabel}
        </div>
      )}
    </div>
  );
}
