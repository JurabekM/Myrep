import brandMark from "./brand-mark.png";

interface BrandMarkProps {
  className?: string;
}

/**
 * «Baraka Dastur» belgisi: yashil fonda krem «B» va tilla bug'doy boshog'i. Rasm `scripts/make_icon.py`
 * tomonidan ilova ikonkasi bilan bitta chizmadan yaratiladi (mobil ilova belgisi bilan bir xil).
 */
export function BrandMark({ className }: BrandMarkProps) {
  return <img src={brandMark} alt="" aria-hidden="true" draggable={false} className={className} />;
}
