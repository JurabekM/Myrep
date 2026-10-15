import ru from "../i18n/ru.json";
import uzCyrl from "../i18n/uz-Cyrl.json";
import uz from "../i18n/uz.json";

describe("i18n", () => {
  it("barcha lokallarda kalitlar bir xil", () => {
    const base = Object.keys(uz).sort();
    expect(Object.keys(ru).sort()).toEqual(base);
    expect(Object.keys(uzCyrl).sort()).toEqual(base);
  });

  it("oʻzbekcha matnlarda toʻgʻri tutuq belgilari ishlatiladi", () => {
    expect(uz["home.paidToSelf"]).toContain("ʻ");
    expect(uzCyrl["home.paidToSelf"]).toBe("Ўзингизга тўланган (шу ой)");
  });
});
