import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { PrimaryButton, SecondaryButton } from "../finance/ui";

/**
 * Imzo chizish maydoni: sichqoncha yoki pero (pointer events). Natija PNG data URL.
 * Rasm faqat shu komponentdan chiqadi; saqlash chaqiruvchida.
 */
export function SignaturePad({
  label,
  onSave,
}: {
  label: string;
  onSave: (pngDataUrl: string) => void;
}) {
  const { t } = useTranslation();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);
  const [dirty, setDirty] = useState(false);

  function context(): CanvasRenderingContext2D | null {
    return canvasRef.current?.getContext("2d") ?? null;
  }

  function point(event: React.PointerEvent<HTMLCanvasElement>): [number, number] {
    const canvas = event.currentTarget;
    const rect = canvas.getBoundingClientRect();
    return [
      ((event.clientX - rect.left) / rect.width) * canvas.width,
      ((event.clientY - rect.top) / rect.height) * canvas.height,
    ];
  }

  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm text-muted">{label}</span>
      <canvas
        ref={canvasRef}
        role="img"
        aria-label={label}
        width={480}
        height={160}
        className="w-full touch-none rounded-lg border border-border bg-white"
        onPointerDown={(event) => {
          const ctx = context();
          if (ctx === null) {
            return;
          }
          drawing.current = true;
          event.currentTarget.setPointerCapture(event.pointerId);
          const [x, y] = point(event);
          ctx.lineWidth = 2.2;
          ctx.lineCap = "round";
          ctx.strokeStyle = "#1f1e1d";
          ctx.beginPath();
          ctx.moveTo(x, y);
        }}
        onPointerMove={(event) => {
          if (!drawing.current) {
            return;
          }
          const ctx = context();
          if (ctx === null) {
            return;
          }
          const [x, y] = point(event);
          ctx.lineTo(x, y);
          ctx.stroke();
          setDirty(true);
        }}
        onPointerUp={() => {
          drawing.current = false;
        }}
        onPointerLeave={() => {
          drawing.current = false;
        }}
      />
      <div className="flex gap-2">
        <PrimaryButton
          disabled={!dirty}
          onClick={() => {
            const canvas = canvasRef.current;
            if (canvas === null) {
              return;
            }
            onSave(canvas.toDataURL("image/png"));
          }}
        >
          {t("agreements.signSave")}
        </PrimaryButton>
        <SecondaryButton
          onClick={() => {
            const canvas = canvasRef.current;
            const ctx = context();
            if (canvas === null || ctx === null) {
              return;
            }
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            setDirty(false);
          }}
        >
          {t("agreements.signClear")}
        </SecondaryButton>
      </div>
    </div>
  );
}
