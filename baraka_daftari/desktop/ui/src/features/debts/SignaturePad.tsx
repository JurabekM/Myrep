import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

/** Chizilgan imzoni PNG baytlari sifatida beradi (sichqoncha, pero yoki sensorli ekran). */
export function SignaturePad({
  label,
  onChange,
}: {
  label: string;
  onChange: (png: number[] | null) => void;
}) {
  const { t } = useTranslation();
  const canvas = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    const ctx = canvas.current?.getContext('2d');
    if (ctx) {
      ctx.lineWidth = 2;
      ctx.lineCap = 'round';
      ctx.strokeStyle = '#000';
    }
  }, []);

  const pos = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  };

  const emit = () => {
    canvas.current?.toBlob((blob) => {
      if (!blob) return;
      void blob.arrayBuffer().then((buf) => {
        onChange(Array.from(new Uint8Array(buf)));
      });
    }, 'image/png');
  };

  return (
    <div>
      <p className="text-sm">{label}</p>
      <canvas
        ref={canvas}
        aria-label={label}
        width={320}
        height={110}
        className="mt-1 touch-none rounded border border-accent/50 bg-white"
        onPointerDown={(e) => {
          const ctx = canvas.current?.getContext('2d');
          if (!ctx) return;
          e.currentTarget.setPointerCapture(e.pointerId);
          drawing.current = true;
          const p = pos(e);
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
        }}
        onPointerMove={(e) => {
          if (!drawing.current) return;
          const ctx = canvas.current?.getContext('2d');
          if (!ctx) return;
          const p = pos(e);
          ctx.lineTo(p.x, p.y);
          ctx.stroke();
          setDirty(true);
        }}
        onPointerUp={() => {
          drawing.current = false;
          emit();
        }}
      />
      <button
        type="button"
        className="mt-1 text-sm underline"
        disabled={!dirty}
        onClick={() => {
          const c = canvas.current;
          c?.getContext('2d')?.clearRect(0, 0, c.width, c.height);
          setDirty(false);
          onChange(null);
        }}
      >
        {t('receipt.clearSignature')}
      </button>
    </div>
  );
}
