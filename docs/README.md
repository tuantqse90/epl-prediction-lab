# EPL Prediction Lab — Docs

> Personal EPL match prediction app: xG-driven Poisson engine + Qwen-powered reasoning and Q&A chatbot. **Payy-inspired** design — pure black surface, neon-lime accent, black-on-neon CTAs (see [payy.network](https://payy.network/)).

## Project Identity

- **Name (tentative)**: `epl-lab` / `predictor.nullshift.sh`
- **Tagline**: *"xG doesn't lie. But the bookies do."*
- **Vibe**: Payy-style — pure black (`#000`), neon-lime accent (`#E0FF32`), black text on neon CTAs, uppercase display type, mono for stats. Terminal motifs used sparingly. See [`frontend.md`](./frontend.md) for the full design spec.
- **Target user**: Tun (solo). Public read-only later. No auth, no accounts.

## Core Value Proposition

Most prediction sites show **what** will happen. This app shows **why**:

- Poisson distribution prediction grounded in **xG data** (not vibes)
- **LLM reasoning layer** explaining the "why" in Vietnamese/English
- **Conversational Q&A** — ask *"Sao mày predict Arsenal thắng?"* and get a grounded answer
- **Transparency**: every prediction shows the math + data behind it

## Success Metrics (personal)

- Model accuracy vs bookmaker odds: beat 50% on 1X2 over a month
- Chat Q&A responses grounded in real data — no hallucinated stats
- Dashboard page load < 1s
- LLM cost < $2/month
- Shipped in < 1 week from scratch

## Doc Index

| File | Contents |
|------|----------|
| [architecture.md](./architecture.md) | Tech stack + system architecture diagram |
| [database.md](./database.md) | Postgres (self-hosted, VPS) schema |
| [prediction-model.md](./prediction-model.md) | Poisson + Dixon-Coles math engine |
| [llm-integration.md](./llm-integration.md) | Qwen reasoning, chat Q&A, LiteLLM config |
| [frontend.md](./frontend.md) | Design system, routes, UX |
| [project-structure.md](./project-structure.md) | Monorepo layout |
| [roadmap.md](./roadmap.md) | MVP → v2 build phases |
| [principles.md](./principles.md) | Code, LLM, and data principles |
| [environment.md](./environment.md) | Env vars, scope, open questions |
| [deploy.md](./deploy.md) | VPS + Cloudflare Pages deployment walkthrough |
