import { useId } from "react";

interface BrandMarkProps {
  className?: string;
}

/**
 * «Baraka Dastur» belgisi: yashil fonda krem «B» va oltin sakkiz burchakli yulduz
 * (`scripts/baraka_logo.py` dagi chizma bilan bir xil o'lchamlar, 32 birlik kvadratda).
 */
export function BrandMark({ className }: BrandMarkProps) {
  const maskId = `brand-b-${useId().replace(/:/g, "")}`;
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" focusable="false" className={className}>
      <defs>
        <mask id={maskId}>
          <rect x="7.36" y="5.44" width="12.48" height="11.52" rx="5.76" fill="white" />
          <rect x="7.36" y="13.44" width="14.08" height="13.12" rx="6.56" fill="white" />
          <rect x="10.88" y="8.96" width="5.44" height="4.48" rx="2.24" fill="black" />
          <rect x="10.88" y="16.96" width="7.04" height="6.08" rx="3.04" fill="black" />
          <rect x="7.36" y="5.44" width="3.52" height="21.12" fill="white" />
        </mask>
      </defs>
      <rect width="32" height="32" rx="7" className="fill-brand" />
      <rect width="32" height="32" mask={`url(#${maskId})`} className="fill-brand-letter" />
      <polygon
        className="fill-brand-star"
        points="25.28,4.8 25.89,6.52 27.54,5.74 26.76,7.39 28.48,8 26.76,8.61 27.54,10.26 25.89,9.48 25.28,11.2 24.67,9.48 23.02,10.26 23.80,8.61 22.08,8 23.80,7.39 23.02,5.74 24.67,6.52"
      />
    </svg>
  );
}
