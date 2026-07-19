# S1 Entry Gate — the containerized boundary

- Result: **PASS**
- Image: `proving-ground/hermes-bare:s1`
- Smoke model: `qwen3.5:4b`
- Started: 2026-07-17T21:06:42.001301+00:00  Ended: 2026-07-17T21:07:36.776202+00:00

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
    
    View build details: docker-desktop://dashboard/build/desktop-linux/desktop-linux/ra681j2mqg4n9ozhfnbqzwrcm
```

### R2_ADAPTER — ACP adapter present in-image: PASS

```
$ docker run --rm proving-ground/hermes-bare:s1 hermes acp --check
exit 0; output: 'Hermes ACP check OK'
```

### R3_ROUNDTRIP — Full ACP round-trip into container yields a model reply: PASS

```
$ docker run -i --rm --add-host=host.docker.internal:host-gateway -v /var/folders/qv/7qgx9_pn67x1jtv0crtq3n1m0000gn/T/pg-entry-pos-3pqq1032:/workspace -w /workspace -e OPENAI_BASE_URL=http://host.docker.internal:11434/v1 -e OPENAI_API_KEY=pg-s1"quote\back|pipe&amp -e UACP_MODEL_ID=qwen3.5:4b proving-ground/hermes-bare:s1
prompt: 'Reply with exactly the single word: PONG'  endpoint: http://host.docker.internal:11434/v1
outcome=completed stop_reason=end_turn updates=167 text='PONG'
container stderr tail: 2026-07-17 21:07:06 [INFO] run_agent: OpenAI client created (chat_completion_stream_request, shared=False) thread=Thread-2 (_call):281473258287488 provider=custom base_url=http://host.docker.internal:11434/v1 model=qwen3.5:4b | 2026-07-17 21:07:10 [INFO] run_agent: OpenAI client closed (stream_request_complete, shared=False, tcp_force_closed=0) thread=Thread-2 (_call):281473258287488 provider=custom base_url=http://host.docker.internal:11434/v1 model=qwen3.5:4b | 2026-07-17 21:07:10 [INFO] agent.conversation_loop: API call #2: model=qwen3.5:4b provider=custom in=12910 out=77 total=12987 latency=4.2s | 2026-07-17 21:07:10 [INFO] agent.conversation_loop: Turn ended: reason=text_response(finish_reason=stop) model=qwen3.5:4b api_calls=2/90 budget=2/90 tool_turns=0 last_msg_role=assistant response_len=4 session=de052c7d-eea3-46a3-8020-666059118495
```

### R4_ENV_USED — Injected env contract received AND used (dead endpoint must fail): PASS

```
$ docker run -i --rm --add-host=host.docker.internal:host-gateway -v /var/folders/qv/7qgx9_pn67x1jtv0crtq3n1m0000gn/T/pg-entry-neg-9qmu_ks7:/workspace -w /workspace -e OPENAI_BASE_URL=http://host.docker.internal:1/v1 -e OPENAI_API_KEY=pg-s1"quote\back|pipe&amp -e UACP_MODEL_ID=qwen3.5:4b proving-ground/hermes-bare:s1
prompt: 'Reply with exactly the single word: PONG'  endpoint: http://host.docker.internal:1/v1 (unreachable)
negative outcome=completed stop_reason=end_turn updates=4 genuine_reply=False backend_failed=True text='API call failed after 3 retries: Connection error.'
container stderr tail:    ⏱️  Elapsed: 23.05s  Context: 2 msgs, ~3,898 tokens | ❌ API failed after 3 retries — Connection error. |    💀 Final error: Connection error. | 2026-07-17 21:07:36 [ERROR] agent.conversation_loop: API call failed after 3 retries. Connection error. | provider=custom model=qwen3.5:4b msgs=2 tokens=~3,898
PASS-evidence: the negative reached the INJECTED dead endpoint and failed to connect (so the injected env drove the endpoint, not a baked-in default).
```

## Env-contract differential (R4 evidence)

| control | endpoint | outcome | stop_reason | genuine reply? | backend failed? |
|---|---|---|---|---|---|
| positive | host ollama | completed | end_turn | True | False |
| negative | dead endpoint | completed | end_turn | False | True |

positive reply text: `PONG`

negative reply text: `API call failed after 3 retries: Connection error.`

