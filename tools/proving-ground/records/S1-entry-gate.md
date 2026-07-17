# S1 Entry Gate — the containerized boundary

- Result: **PASS**
- Image: `proving-ground/hermes-bare:s1`
- Smoke model: `qwen3.5:4b`
- Started: 2026-07-17T20:53:15.466167+00:00  Ended: 2026-07-17T20:53:48.893589+00:00

The gate proves what S0 deferred: the image builds, the ACP adapter is present in-image,
a full ACP round-trip crosses the container boundary, and the injected provider env
contract is not merely received but USED (a dead endpoint must fail — negative control).

Raw runner-side ACP transcripts (ground truth for R3/R4): `records/entry-gate/pos-transcript.log`, `records/entry-gate/neg-transcript.log`.

## Requirements

| Req | Requirement | Result |
|---|---|---|
| R1_BUILD | Cell image builds | **PASS** |
| R2_ADAPTER | ACP adapter present in-image | **PASS** |
| R3_ROUNDTRIP | Full ACP round-trip into container yields a model reply | **PASS** |
| R4_ENV_USED | Injected env contract received AND used (dead endpoint must fail) | **PASS** |

### R1_BUILD — Cell image builds: PASS

```
$ docker build -t proving-ground/hermes-bare:s1 /Users/mike/Workplace/uacp/.worktrees/pg-s1/tools/proving-ground/images/hermes
exit 0 in 2s
build tail:
    #12 CACHED
    
    #13 [9/9] WORKDIR /workspace
    #13 CACHED
    
    #14 exporting to image
    #14 exporting layers done
    #14 writing image sha256:b74f88fc440585483374e71707fa788ae758aa9734da41c25660f649a859e159 done
    #14 naming to docker.io/proving-ground/hermes-bare:s1 done
    #14 DONE 0.0s
    
    View build details: docker-desktop://dashboard/build/desktop-linux/desktop-linux/jq9xk9e328qmhapodgzinukn5
```

### R2_ADAPTER — ACP adapter present in-image: PASS

```
$ docker run --rm proving-ground/hermes-bare:s1 hermes acp --check
exit 0; output: 'Hermes ACP check OK'
```

### R3_ROUNDTRIP — Full ACP round-trip into container yields a model reply: PASS

```
$ docker run -i --rm --add-host=host.docker.internal:host-gateway -v /var/folders/qv/7qgx9_pn67x1jtv0crtq3n1m0000gn/T/pg-entry-pos-4y6g8uny:/workspace -w /workspace -e OPENAI_BASE_URL=http://host.docker.internal:11434/v1 -e OPENAI_API_KEY=pg-s1"quote\back|pipe&amp -e UACP_MODEL_ID=qwen3.5:4b proving-ground/hermes-bare:s1
prompt: 'Reply with exactly the single word: PONG'  endpoint: http://host.docker.internal:11434/v1
outcome=completed stop_reason=end_turn updates=69 text='The user wants me to reply with the exact phrase "PONG" - just that single word as a response. This is simple and direct, no tools needed for this task since it'
container stderr tail: 2026-07-17 20:53:20 [INFO] run_agent: OpenAI client created (chat_completion_stream_request, shared=False) thread=Thread-1 (_call):281472999616896 provider=custom base_url=http://host.docker.internal:11434/v1 model=qwen3.5:4b | 2026-07-17 20:53:25 [INFO] run_agent: OpenAI client closed (stream_request_complete, shared=False, tcp_force_closed=0) thread=Thread-1 (_call):281472999616896 provider=custom base_url=http://host.docker.internal:11434/v1 model=qwen3.5:4b | 2026-07-17 20:53:25 [INFO] agent.conversation_loop: API call #1: model=qwen3.5:4b provider=custom in=12910 out=70 total=12980 latency=4.3s | 2026-07-17 20:53:25 [INFO] agent.conversation_loop: Turn ended: reason=text_response(finish_reason=stop) model=qwen3.5:4b api_calls=1/90 budget=1/90 tool_turns=0 last_msg_role=assistant response_len=4 session=3b73c14f-d98e-45fb-9d73-4a2fd902303f
```

### R4_ENV_USED — Injected env contract received AND used (dead endpoint must fail): PASS

```
$ docker run -i --rm --add-host=host.docker.internal:host-gateway -v /var/folders/qv/7qgx9_pn67x1jtv0crtq3n1m0000gn/T/pg-entry-neg-6d4swwck:/workspace -w /workspace -e OPENAI_BASE_URL=http://host.docker.internal:1/v1 -e OPENAI_API_KEY=pg-s1"quote\back|pipe&amp -e UACP_MODEL_ID=qwen3.5:4b proving-ground/hermes-bare:s1
prompt: 'Reply with exactly the single word: PONG'  endpoint: http://host.docker.internal:1/v1 (unreachable)
negative outcome=completed stop_reason=end_turn updates=4 genuine_reply=False backend_failed=True text='API call failed after 3 retries: Connection error.'
container stderr tail:    ⏱️  Elapsed: 20.43s  Context: 2 msgs, ~3,898 tokens | ❌ API failed after 3 retries — Connection error. |    💀 Final error: Connection error. | 2026-07-17 20:53:48 [ERROR] agent.conversation_loop: API call failed after 3 retries. Connection error. | provider=custom model=qwen3.5:4b msgs=2 tokens=~3,898
PASS-evidence: the negative reached the INJECTED dead endpoint and failed to connect (so the injected env drove the endpoint, not a baked-in default).
```

## Env-contract differential (R4 evidence)

| control | endpoint | outcome | stop_reason | genuine reply? | backend failed? |
|---|---|---|---|---|---|
| positive | host ollama | completed | end_turn | True | False |
| negative | dead endpoint | completed | end_turn | False | True |

positive reply text: `The user wants me to reply with the exact phrase "PONG" - just that single word as a response. This is simple and direct, no tools needed for this task since it's literally asking me to output one spe`

negative reply text: `API call failed after 3 retries: Connection error.`

