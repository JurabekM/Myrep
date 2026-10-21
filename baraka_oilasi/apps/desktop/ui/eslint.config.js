import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "src/bindings.ts", "src/i18n/*.json"] },
  js.configs.recommended,
  ...tseslint.configs.strict,
  reactHooks.configs.flat.recommended,
  {
    languageOptions: { globals: globals.browser },
    rules: {
      // UI pul hisoblamaydi (BARAKA_OILASI 4.3): summalar yadroda parse va formatlanadi.
      "no-restricted-globals": [
        "error",
        { name: "parseFloat", message: "Pul UI'da hisoblanmaydi — summani string sifatida yadroga yuboring." },
        { name: "parseInt", message: "Pul UI'da hisoblanmaydi — summani string sifatida yadroga yuboring." },
      ],
      "no-restricted-properties": [
        "error",
        { object: "Number", property: "parseFloat", message: "Pul UI'da hisoblanmaydi." },
        { object: "Math", property: "round", message: "Yaxlitlash faqat yadroda (round_half_up)." },
      ],
    },
  },
);
