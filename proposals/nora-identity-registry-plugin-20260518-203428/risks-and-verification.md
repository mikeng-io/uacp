# Risks and Verification

## Material risks

- High: identity leakage from source registry into public Nora context.
- Medium: wrong sender context due to loose handle matching.
- Medium: runtime hook incompatibility with Nora profile plugin loading.
- Medium: prompt-injection confusion if identity context is treated as user instruction.

## Required verification

- Registry compiles and lookup count/card count are expected.
- Known sender resolves to the expected sanitized card.
- Unknown sender produces no prompt injection.
- Runtime JSON and prompt context contain no raw private fields.
- Plugin imports under Nora `HERMES_HOME`.
- Fake gateway event mutates `event.channel_prompt` only for matched sender.
- Focused audit passes before any gateway restart.
