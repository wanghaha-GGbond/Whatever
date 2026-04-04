// UIUX/src/app/hooks/use-share-card.ts
import { useState, useCallback } from 'react';
import html2canvas from 'html2canvas';

export function useShareCard() {
  const [sharing, setSharing] = useState(false);

  const share = useCallback(async (placeName: string) => {
    const node = document.getElementById('share-card-node');
    if (!node) return;

    setSharing(true);
    try {
      const canvas = await html2canvas(node, {
        scale: 2,
        useCORS: true,
        backgroundColor: null,
        logging: false,
      });

      const blob = await new Promise<Blob>((resolve, reject) => {
        canvas.toBlob((b) => {
          if (b) resolve(b);
          else reject(new Error('canvas.toBlob failed'));
        }, 'image/png');
      });

      const file = new File([blob], `whatever-${placeName}.png`, { type: 'image/png' });

      // Web Share API Level 2（支持文件分享，iOS 15+ / Android Chrome 支持）
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({
          files: [file],
          title: `Whatever 帮我选了：${placeName}`,
        });
        return;
      }

      // 兜底：下载 PNG
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `whatever-${placeName}.png`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setSharing(false);
    }
  }, []);

  return { share, sharing };
}
