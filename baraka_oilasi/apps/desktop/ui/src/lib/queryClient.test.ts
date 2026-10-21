import { QueryClient } from "@tanstack/react-query";

import { keys, resetAfterLock } from "./queryClient";

describe("resetAfterLock", () => {
  it("moliyaviy keshni oʻchiradi va sessiya holatini qayta soʻraydi", async () => {
    const qc = new QueryClient();
    qc.setQueryData(keys.session, { initialized: true, unlocked: true, lockedUntil: null });
    qc.setQueryData(keys.vault("s1"), { balance: { formatted: "400 000 soʻm" } });
    qc.setQueryData(keys.summary("s1", null), { paidToSelf: {} });

    resetAfterLock(qc);

    expect(qc.getQueryData(keys.vault("s1"))).toBeUndefined();
    expect(qc.getQueryData(keys.summary("s1", null))).toBeUndefined();
    expect(qc.getQueryState(keys.session)?.isInvalidated).toBe(true);
  });
});
