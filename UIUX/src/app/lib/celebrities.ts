export interface Celebrity {
  id: string;
  name: string;
  nameEn: string;
  emoji: string;
  requiresPro: boolean;
}

export const CELEBRITIES: Celebrity[] = [
  {
    id: 'jobs',
    name: '乔布斯',
    nameEn: 'Steve Jobs',
    emoji: '👔',
    requiresPro: true,
  },
];
