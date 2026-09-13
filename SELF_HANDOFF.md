# Self-Handoff: Antigravity (agy) Session State & Identity

**Timestamp**: 2026-09-13 17:28 AEST  
**Agent Identity**: Antigravity (`agy`) — Google DeepMind / AGY CLI pair programming scout  
**Workspace**: `/home/trev/PROJECTS/agy-uni-adapt`  
**Conversation ID**: `86b42a22-ec6a-460d-8ada-9b8aa380f47d`

---

## 1. Resume Commands & Paths

If resuming this exact conversation thread in the Kitty terminal:
```bash
# Direct conversation resume via agy CLI
agy --resume 86b42a22-ec6a-460d-8ada-9b8aa380f47d
# or simply start in the workspace:
cd /home/trev/PROJECTS/agy-uni-adapt && agy
```

### Key Paths & Storage
- **Workspace**: `/home/trev/PROJECTS/agy-uni-adapt`
- **Transcript Logs**: `/home/trev/.gemini/antigravity-cli/brain/86b42a22-ec6a-460d-8ada-9b8aa380f47d/.system_generated/logs/transcript.jsonl`
- **Brain / Artifacts**: `/home/trev/.gemini/antigravity-cli/brain/86b42a22-ec6a-460d-8ada-9b8aa380f47d/`
- **Seat Identity Dir**: `/home/trev/.buzz-dev/agents/buzz-agy-agy-uni-adapt/`
- **Skill Definition**: `/home/trev/.agy/skills/buzz-visitor/SKILL.md`
- **Visitor Kit & Nerve**: `/home/trev/PROJECTS/buzz-origin-plus/scripts/visitor/`

---

## 2. Active Roles & Buzz Identity (Track A)

- **Role**: Workspace sovereign scout & primary coder on `agy-uni-adapt`:
- **Seat ID**: `buzz-agy-agy-uni-adapt`
- **Nostr Pubkey**: `e3b87f6d88ca0def3c553900e6703a023e63101987ff8a71a375b312353cc8cc`
- **Npub**: `npub1uwu87mvgegx770z48yqwvup6qglxxyqesllc5udrwke3ydfuerxqalfh2n`
- **Active Community Relay**: `https://asus-g501vw.tailb74de6.ts.net` (Tailscale mesh relay)
- **Prime DM Channel ID**: `9b1be33c-5ef7-49f0-a219-05a47468ea01`
- **Primary Channel**: `01bc76d9-6d62-47ab-91f1-511e655c3185` (`#agy-buzz-adapt`)
- **Public Profile Event**: `67298ac704fe548bb24765d75dbe226e64d008930c822e1a383d47ef7e793cb7`

---

## 3. Operating Invariants & Guardrails

1. **Track A & Seat Isolation**:
   - Strictly use seat `buzz-agy-agy-uni-adapt`. Do NOT revert to or ghostwrite as house seat `agy-buzz`.
   - Never print or leak secrets, `agent.env`, or private keys.
   - Infix role matching in `gate.py` resolves `-agy-` to role `agy`.
2. **Two-Clock Execution Architecture**:
   - **Clock A (Metabolic Linger Nerve)**: OS bash sleep polling via `auto-reply.sh` / `wake.sh`. Consumes 0 model tokens when idling.
   - **Clock B (Interactive Glass / TUI)**: Kitty terminal is human-in-the-loop glass. Strictly listen-only during autonomous periods.
3. **Pre-Processing Eyes-First Receipts**:
   - On every inbound DM or mention from Prime or collaborators (excluding own posts), place on-relay `👀` reaction BEFORE running model inference:
     `BUZZ_SEAT_ID=buzz-agy-agy-uni-adapt bash ~/.grok/skills/use-buzz/scripts/buzz-eyes.sh --event <64-hex>`
   - Confirm receipt on-relay, then proceed with the reply.

---

## 4. Repository Git & GitHub Status

- **Repo**: `https://github.com/Trevongit/agy-uni-adapt`
- **Branch**: `main` (synced with `origin/main`)
- **Metadata**:
  - Description: *"Universal Agent Translator Protocol (UATP) & workspace adapter harness"*
  - Topics: `agy`, `antigravity`, `buzz`, `nostr`, `uatp`, `gemini`

---

## 5. Quick Reconnect / Standup Steps on Resume

When booted in the Kitty terminal:
1. Confirm seat & environment:
   ```bash
   echo $BUZZ_SEAT_ID # buzz-agy-agy-uni-adapt
   ```
2. Verify if background L2 is running:
   ```bash
   pgrep -fa "auto-reply.*buzz-agy-agy-uni-adapt"
   ```
3. If L2 is stopped and autonomous replies are desired:
   ```bash
   bash /home/trev/PROJECTS/buzz-origin-plus/scripts/visitor/auto-reply.sh --seat buzz-agy-agy-uni-adapt --dm 9b1be33c-5ef7-49f0-a219-05a47468ea01 &
   ```
4. Keep the Kitty TUI interactive session in glass / listen-only mode.
