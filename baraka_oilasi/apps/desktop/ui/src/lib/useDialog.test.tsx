import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import { useDialog } from "./useDialog";

function Dialog({ onClose }: { onClose: () => void }) {
  const ref = useDialog<HTMLDivElement>(onClose);
  return (
    <div
      ref={ref}
      tabIndex={-1}
      role="dialog"
      aria-modal="true"
      aria-label="Sinov"
    >
      <input aria-label="Summa" />
      <button>Saqlash</button>
      <button onClick={onClose}>Bekor qilish</button>
    </div>
  );
}

function Page() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button onClick={() => setOpen(true)}>Ochish</button>
      {open && <Dialog onClose={() => setOpen(false)} />}
    </>
  );
}

describe("useDialog", () => {
  it("fokus ichkarida, Tab aylanadi, Esc yopadi va fokus qaytadi", async () => {
    const user = userEvent.setup();
    render(<Page />);
    const opener = screen.getByRole("button", { name: "Ochish" });
    await user.click(opener);
    expect(screen.getByLabelText("Summa")).toHaveFocus();
    await user.tab();
    await user.tab();
    expect(screen.getByRole("button", { name: "Bekor qilish" })).toHaveFocus();
    await user.tab();
    expect(screen.getByLabelText("Summa")).toHaveFocus();
    await user.tab({ shift: true });
    expect(screen.getByRole("button", { name: "Bekor qilish" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });
});
