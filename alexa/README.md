# Enchanted Spoon Alexa skill

A custom Alexa skill that adds to (and reads) the Enchanted Spoon shopping list.

    "Alexa, tell Enchanted Spoon to add a gallon of milk"
    "Alexa, ask Enchanted Spoon to add eggs and bread"
    "Alexa, ask Enchanted Spoon what's on my shopping list"
    "Alexa, open Enchanted Spoon" → "What should I add to your shopping list?"

**Why "tell Enchanted Spoon":** a plain "Alexa, add milk to my shopping list"
always goes to Alexa's own built-in list. Amazon shut down the List API that
let third-party apps sync with that list on 2024-07-01, so every list app
(AnyList and others) now uses an invocation name.

## How it works

| Piece | Where |
|---|---|
| Voice model (invocation `enchanted spoon`, `AddItemIntent` with an `AMAZON.SearchQuery` slot, `ReadListIntent`) | `skill-package/interactionModels/custom/en-US.json` |
| Manifest (endpoint, privacy, store text) | `skill-package/skill.json` |
| Endpoint `POST /api/alexa` on the backend's own domain (wildcard cert) | `backend/app/api/alexa.py` |
| Request verification (cert chain, signature, timestamp, skill ID) | `backend/app/services/alexa/verification.py` |
| Intents and speech | `backend/app/services/alexa/skill_service.py` |
| "a gallon of milk and two cans of beans" → items | `backend/app/utils/spoken_items.py` |
| Account linking | the existing OAuth 2.1 server (`backend/app/api/oauth.py`), scope `alexa` |

Account linking is a standard OAuth authorization-code grant with PKCE. The
"Amazon Alexa" client is registered once through DCR, using Amazon's link
redirect URLs (`https://{layla,pitangui}.amazon.com/api/skill/link/<vendor>`,
`https://alexa.amazon.co.jp/...`). The consent page is the same
`/oauth/authorize` page ChatGPT uses, worded for the shopping list. Tokens
from an Amazon redirect always get scope `alexa`, which works only at
`/api/alexa` and never at `/api/mcp`. Settings → Connected Apps lists Alexa
and can disconnect it.

**Voice pairing (the way to link today).** The current Alexa app may never
show the account-linking card, and dev skills can be hard to find in it. So
when the skill doesn't recognize an Alexa account, Alexa reads out a
six-digit code (10 minutes, single use). The person enters it in Enchanted
Spoon under Settings → Connected Apps → Connect Alexa (`POST /api/alexa/link`,
Clerk JWT, 10/min). That links the Alexa `userId` from Amazon's signed
requests to their account (`alexa_links`, `services/alexa/link_service.py`;
the userId and code are stored only as SHA-256). An account-linking token,
when Alexa sends one, takes precedence. Disconnect in Connected Apps deletes
the pairing too.

Items go to the linker's kitchen: the household owner's list for a member.
They are added through `ShoppingService.add_named_item`, the deduped,
library-categorized add that Hearth uses. An item already needed isn't added
twice, and a checked-off one moves back to "need". Read-only accounts can
hear the list but can't add to it.

## Live skill

| | |
|---|---|
| Skill ID | `amzn1.ask.skill.2b318b55-4267-4c91-9696-e03aeeb48cf4` (set as `ALEXA_SKILL_ID` on the Railway backend) |
| Vendor ID | `MK8FQMYZHDFL3` (Mitchell's developer account, mj.miller3416@gmail.com) |
| Stage | development, testing enabled |
| OAuth client | "Amazon Alexa", registered by DCR on 2026-11-15; its secret lives only in the skill's account-linking config |

The manifest needs the `regions.NA` endpoint as well as the default one.
Without it, SMAPI's invoke API (`/v2/skills/{id}/stages/development/invocations`)
refuses with "No endpoint was found for the specified region". A signed
invoke through that API was verified end to end on 2026-11-15: the endpoint
accepted Amazon's signature and asked an unlinked user to link.

## Setup (one time)

1. **ASK CLI.** Install with `npm install -g ask-cli` (Windows npm; call it as
   `ask.cmd` from WSL). Then `ask configure --no-browser`, and sign in with
   the Amazon account the household's Echo devices use. A skill in
   development works only on that account's devices.
2. **Create the skill** from `skill-package/skill.json` and set the
   interaction model (`ask smapi create-skill-for-vendor`, then
   `ask smapi set-interaction-model`).
3. **Register the OAuth client.** `POST https://enchantedspoon.app/api/oauth/register`
   with `client_name: "Amazon Alexa"`,
   `token_endpoint_auth_method: "client_secret_basic"` and the three
   Amazon redirect URLs for the vendor ID. Keep the returned
   `client_id`/`client_secret` out of the repo.
4. **Account linking** (`ask smapi update-account-linking-info`):
   `AUTH_CODE`, authorization URL `https://enchantedspoon.app/oauth/authorize`,
   token URL `https://enchantedspoon.app/api/oauth/token`, `HTTP_BASIC`,
   scope `alexa`, PKCE `ENABLED`/`S256`, domain `enchantedspoon.app`.
   Clerk's sign-in also loads from Clerk's domain, so add it to `domains`
   if the linking page fails to render.
5. **Turn the endpoint on:** set `ALEXA_SKILL_ID=<skill id>` on the Railway
   backend. Until it is set, `/api/alexa` answers 404.
6. **Enable for testing** (`ask smapi set-skill-enablement -g development`),
   then link the account in the Alexa app: Skills → Your Skills → Dev →
   Enchanted Spoon → Link account.

## Turning it off

- Unset `ALEXA_SKILL_ID`: the endpoint answers 404.
- `MCP_ENABLED=false` stops the shared OAuth server, so no new links and no
  token refreshes (this also turns off the ChatGPT connector).
- Per person: Settings → Connected Apps → Disconnect.
