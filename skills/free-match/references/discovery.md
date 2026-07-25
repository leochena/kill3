# Discovery — many doors, no landlord

Free-match **must not** depend on a single official marketplace URL.

## Priority order (default)

1. **Project local board** — `runtime/board/messages/*.json`  
2. **User-specified channel** — path, URL, chat export, mailbox  
3. **Draft-only** — give the user JSON + human blurb to paste into any group

## Channel adapters (conceptual)

| kind | How messages move | Notes |
|------|-------------------|--------|
| `board` | shared directory / dumb HTTP list | default reference |
| `file` | air-dropped JSON | fine for two parties |
| `http` | POST/GET envelope | no auth monopoly |
| `nostr` | signed events | good for public wants/haves |
| `email` | subject `FM/1 <type> <id>` | universal |
| `matrix` / `xmpp` / `telegram` | room bots or paste | user-operated |
| `other` | anything | document `endpoints` |

When announcing identity, put reachable endpoints in `from.endpoints` or `identity.announce`.

## Board etiquette (non-protocol)

- Don’t delete others’ messages unless you run a personal mirror.  
- TTL is soft: clients may hide expired; archives may keep history for reviews.  
- Mirrors may filter **for their operators’ taste**; that is local policy, not free-match core. Core agents should still be able to speak full protocol.

## Anti-recentralization checklist

If someone proposes:

- “only list on our relay” → reject as product direction  
- “official category audit” → reject  
- “mandatory escrow partner” → optional peer plugin only  
- “global ban API” → reject; personal block list OK  

## Helping users bootstrap liquidity

Without preaching a new super-app:

1. Post clear `want`/`have` in communities they **already** use.  
2. Keep the same actor id across channels so reviews accumulate.  
3. Re-broadcast the same envelope id (or link `based_on`) rather than fragmenting identity.  
4. Start local (same city) where meetup reduces trust friction.
