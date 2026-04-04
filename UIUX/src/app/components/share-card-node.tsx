// UIUX/src/app/components/share-card-node.tsx
// 屏幕外渲染的分享卡片 DOM 节点，供 html2canvas 截图使用。
// 不直接展示给用户，通过 id="share-card-node" 被 hook 引用。

interface ShareCardNodeProps {
  placeName: string;
  placeType: string;
  etaMin: number;
  transportMode: string;
  budgetText: string;
  destinyQuote: string;
  personaLabel1: string;
  personaSummary1: string;
  personaLabel2: string;
  personaSummary2: string;
}

export function ShareCardNode({
  placeName,
  placeType,
  etaMin,
  transportMode,
  budgetText,
  destinyQuote,
  personaLabel1,
  personaSummary1,
  personaLabel2,
  personaSummary2,
}: ShareCardNodeProps) {
  return (
    <div
      id="share-card-node"
      style={{
        position: 'fixed',
        left: '-9999px',
        top: 0,
        width: '360px',
        background: 'linear-gradient(135deg, #16a34a 0%, #0d9488 100%)',
        padding: '28px 24px',
        color: 'white',
        fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif',
        borderRadius: '20px',
      }}
    >
      {/* Eyebrow */}
      <div style={{ fontSize: '10px', letterSpacing: '3px', opacity: 0.65, marginBottom: '14px' }}>
        WHATEVER · 命运已拍板
      </div>

      {/* Place name */}
      <div style={{ fontSize: '26px', fontWeight: 700, marginBottom: '4px' }}>
        {placeName}
      </div>

      {/* Meta */}
      <div style={{ fontSize: '11px', opacity: 0.75, marginBottom: '18px' }}>
        {placeType} · {transportMode}约{etaMin}分钟 · {budgetText}
      </div>

      {/* Destiny quote */}
      <div
        style={{
          background: 'rgba(255,255,255,0.15)',
          borderRadius: '10px',
          padding: '12px 14px',
          fontSize: '13px',
          fontStyle: 'italic',
          lineHeight: 1.6,
          marginBottom: '14px',
        }}
      >
        "{destinyQuote}"
      </div>

      {/* Persona summaries */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div
          style={{
            background: 'rgba(0,0,0,0.18)',
            borderRadius: '8px',
            padding: '9px 12px',
            fontSize: '12px',
          }}
        >
          <span style={{ opacity: 0.6 }}>{personaLabel1} · </span>
          {personaSummary1}
        </div>
        <div
          style={{
            background: 'rgba(0,0,0,0.18)',
            borderRadius: '8px',
            padding: '9px 12px',
            fontSize: '12px',
          }}
        >
          <span style={{ opacity: 0.6 }}>{personaLabel2} · </span>
          {personaSummary2}
        </div>
      </div>

      {/* Footer */}
      <div style={{ marginTop: '18px', fontSize: '10px', opacity: 0.45, textAlign: 'right', letterSpacing: '1px' }}>
        WHATEVER.APP · 帮我选一个
      </div>
    </div>
  );
}
