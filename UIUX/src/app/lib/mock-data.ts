import { Place, PersonaReview } from '../types';

export const mockPlaces: Place[] = [
  {
    id: '1',
    name: '新泾公园',
    type: '公园',
    distance: '骑车12分钟',
    budget: '¥0',
    aiJudgement: '现在去比较轻松，适合一个人待一会',
    riskLabel: '傍晚人会变多',
  },
  {
    id: '2',
    name: '社区咖啡店',
    type: '咖啡',
    distance: '骑车10分钟',
    budget: '¥28',
    aiJudgement: '距离近，坐一小时不会有负担',
    riskLabel: '周末3点后可能满座',
  },
  {
    id: '3',
    name: '上生新所',
    type: '文化空间',
    distance: '地铁15分钟',
    budget: '¥0-50',
    aiJudgement: '有新鲜感，适合随便逛逛',
  },
  {
    id: '4',
    name: '苏州河畔骑行道',
    type: '户外',
    distance: '骑车8分钟',
    budget: '¥0',
    aiJudgement: '风景好，可以边骑边看，比较放松',
    riskLabel: '下午太阳比较晒',
  },
  {
    id: '5',
    name: '天山书局',
    type: '书店',
    distance: '步行18分钟',
    budget: '¥0-30',
    aiJudgement: '安静，适合一个人翻翻书',
  },
];

export const personaReviews: Record<string, PersonaReview> = {
  '独处型': {
    persona: '独处型',
    review: '这里不会逼你社交，适合一个人慢慢待着。',
    risk: '傍晚可能没有你想的那么空。',
    conclusion: '我会去。',
  },
  '探索型': {
    persona: '探索型',
    review: '可以发现一些周边没注意过的角落，有点意思。',
    risk: '可能没有特别惊喜的地方。',
    conclusion: '值得试试。',
  },
  '务实型': {
    persona: '务实型',
    review: '时间和金钱成本都合理，不会后悔。',
    risk: '如果下雨就不太方便。',
    conclusion: '靠谱选择。',
  },
  '审美型': {
    persona: '审美型',
    review: '环境还不错，有一些美的细节可以留意。',
    risk: '光线不是最佳时段。',
    conclusion: '可以去看看。',
  },
  '老饕': {
    persona: '老饕',
    review: '看品类和评分，这家大概率不会让你失望。',
    risk: '没有真实口碑数据，踩雷概率未知。',
    conclusion: '值得一试。',
  },
  '效率党': {
    persona: '效率党',
    review: '距离近，出餐应该不慢，午休时间够用。',
    risk: '高峰期可能排队，建议早点去。',
    conclusion: '时间上可以。',
  },
  '精算师': {
    persona: '精算师',
    review: '人均在合理范围内，不算坑。',
    risk: '实际消费可能超出预期，注意隐形消费。',
    conclusion: '性价比过关。',
  },
  '氛围感': {
    persona: '氛围感',
    review: '环境信息有限，但这个品类通常还行。',
    risk: '实际氛围可能和想象有落差。',
    conclusion: '可以去感受一下。',
  },
};
