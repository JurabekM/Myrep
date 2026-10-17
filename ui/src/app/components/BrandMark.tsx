interface BrandMarkProps {
  className?: string;
}

/** Ilova belgisi: qorong'i fonda geometrik sakkiz burchakli yulduz (scripts/make_icon.py bilan bir xil). */
export function BrandMark({ className }: BrandMarkProps) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" focusable="false" className={className}>
      <rect width="32" height="32" rx="8" className="fill-raised" />
      <polygon
        className="fill-accent"
        points="16,4 18.87,9.07 24.49,7.51 22.93,13.13 28,16 22.93,18.87 24.49,24.49 18.87,22.93 16,28 13.13,22.93 7.51,24.49 9.07,18.87 4,16 9.07,13.13 7.51,7.51 13.13,9.07"
      />
    </svg>
  );
}
