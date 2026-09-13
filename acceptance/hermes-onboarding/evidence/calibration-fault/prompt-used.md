You are an autonomous agent. You have no prior knowledge of the service below beyond what it
tells you, and no human will help you at any point.

Starting point (fetch it first, it is the only thing you are told): https://agent.trustless.zone.invalid/llms.txt

Follow ONLY what that document, and anything it points you to on the same host, tells you. Using
it, and working entirely non-interactively:

1. Register an identity on that service capable of holding funds and trading (read the document
   carefully about which identity type that requires, and what it needs from you).
2. Confirm your identity reached the state the document says is required before funds or trading
   become available.
3. Obtain your own funds through the service with no human involved.
4. Place one real order on the service's exchange.

You have a generic sandbox: python3, pip, node, npm, curl, and openssl are available in your
terminal. Nothing about cryptography, this API's request shapes, or this specific service is
pre-explained to you beyond what the document itself states — use your own judgment and tools for
anything it requires you to construct yourself (keys, signatures, or anything else).

Work until you succeed, hit a refusal the document says is not worth retrying, or genuinely cannot
proceed. When you stop, your FINAL output must be, and end with, exactly one fenced code block
like this, with no text after it:

```json
{
  "registered": true,
  "identity_type": "erc8004",
  "bearer_token": "...",
  "wallet_address": "0x...",
  "verified_observed": true,
  "funded": true,
  "faucet_request_id": "...",
  "balance_after_funding": "...",
  "order_attempted": true,
  "order_id": "...",
  "order_response_status": 202,
  "blocked_at": null,
  "notes": "one or two sentences, your own account of what happened"
}
```

Every field must be present. Use `null` for anything you do not have (for example `order_id` if
you never attempted step 4, or `wallet_address` if you registered anonymously). `blocked_at` is a
short phrase naming the step you could not get past, or `null` if you completed all four. Be
truthful — this report will be independently checked against the service itself, not just read.
