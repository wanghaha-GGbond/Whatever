export interface Place {
  id: string;
  name: string;
  type: string;
  distance: string;
  budget: string;
  aiJudgement: string;
  riskLabel?: string;
}

export interface HistoryItem {
  id: string;
  place: Place;
  timestamp: string;
  conditions: string;
  satisfaction?: 'good' | 'neutral' | 'bad';
}

export interface PersonaReview {
  persona: string;
  review: string;
  risk: string;
  conclusion: string;
}

export interface DecisionRequest {
  prompt: string;
  scene?: string;
  transport?: string;
  budget?: string;
  atmosphere?: string[];
}
