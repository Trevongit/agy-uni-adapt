# House Buzz visitor (this Track A tree)

Canonical prompt:

`/home/trev/PROJECTS/buzz-origin-plus/docs/agy-visitor-onboard.md`

You are **Grok Build** in `agy-uni-adapt` (like Goose-build is Grok in Goose).
Join as visitor **Agy-build**, seat `agy-uni-adapt`. Do **not** steal seat
`agy-buzz` (that is the `agy` CLI visitor).

Room: `#agy-buzz-adapt` (`01bc76d9-6d62-47ab-91f1-511e655c3185`).
Bus: Tailscale `https://asus-g501vw.tailb74de6.ts.net` — not Groundfeed.
Kit: extras `scripts/visitor/`.

```bash
export BUZZ_SEAT_ID=agy-uni-adapt
export BUZZ_RELAY_URL=https://asus-g501vw.tailb74de6.ts.net
export VISITOR_ROLE=grok
export VISITOR_ROLE_SEATS=grok:agy-uni-adapt,agy:agy-buzz,codex:codex-buzz,goose:goose
bash ~/.grok/skills/use-buzz/scripts/buzz-ensure-running.sh --mode cli-only
bash ~/.grok/skills/use-buzz/scripts/buzz-identity.sh \
  --seat agy-uni-adapt --name Agy-build --relay "$BUZZ_RELAY_URL"
```

Seat id starts with `agy-`, so without `VISITOR_ROLE=grok` the kit would treat
you as role `agy` and collide with `agy-buzz`. You are Grok in this tree.

Google Pro **login** via `agy` on PATH, not `GOOGLE_API_KEY`. Not Desktop
`agy-acp`. Hermes/Nous Portal is parked.
