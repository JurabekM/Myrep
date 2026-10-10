/// Server manzili. Emulyatorda 10.0.2.2 — kompyuterdagi localhost. Production'da --dart-define bilan almashtiriladi.
const apiBaseUrl = String.fromEnvironment(
  'OMBORAI_API_URL',
  defaultValue: 'http://10.0.2.2:8000',
);
