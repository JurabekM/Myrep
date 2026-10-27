# Deploy (11-faza, ADR-0015)

```
deploy/zanjir up staging      # bitta buyruq: maxfiy qiymatlar, build, migratsiya, API, Caddy (HTTPS), kunlik zaxira
deploy/check-staging.sh       # qabul sinovi: smoke, E2E (TLS), zaxira → tiklash → nazorat yig'indilari
deploy/zanjir up prod         # 🛑 2-darvozadan keyin: environments/prod.env to'ldirilgan bo'lishi shart
```

Batafsil — [`../docs/DEPLOY.md`](../docs/DEPLOY.md), kundalik amallar va hodisalar — [`../docs/RUNBOOK.md`](../docs/RUNBOOK.md).
`environments/*.env` va `*.age-key` commit qilinmaydi.
