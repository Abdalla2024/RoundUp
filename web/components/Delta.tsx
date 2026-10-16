import { signedMoney } from "@/lib/format";
import { Icon } from "./Icon";

/** A signed money figure that never relies on colour: the plus or minus sign is part of the text and an up or down arrow sits beside it
 *  (the arrow is decoration, hidden from screen readers, which read the sign). Green and red only say "gain" and "loss" in this made-up
 *  market. `neutral` is for the difference between two strategies, which is not a gain or a loss: colour or an arrow would read as better or worse, so it shows the sign only.
 *  The sign is read from the API's own string; nothing is calculated. */
export function Delta({ value, neutral = false }: { value: string; neutral?: boolean }) {
  const negative = value.startsWith("-"), zero = /^-?0+(\.0+)?$/.test(value);
  const kind = zero || neutral ? "flat" : negative ? "neg" : "pos";
  return (
    <span className={`delta ${kind}`}>
      {!zero && !neutral && <Icon name={negative ? "down" : "up"} size={18} />}
      <span>{signedMoney(value)}</span>
    </span>
  );
}
