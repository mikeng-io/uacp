# S1 Entry Gate — the containerized boundary

- Result: **PASS**
- Image: `proving-ground/hermes-bare:s1`
- Smoke model: `qwen3.5:4b`
- Started: 2026-07-17T19:46:52.702534+00:00  Ended: 2026-07-17T19:47:26.162786+00:00

The gate proves what S0 deferred: the image builds, the ACP adapter is present in-image,
a full ACP round-trip crosses the container boundary, and the injected provider env
contract is not merely received but USED (a dead endpoint must fail — negative control).

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
    #14 writing image sha256:566f6240b3e19d9daf29ec9e2ce8a66d8511bdda89eb0ab7770302c74a68b270 done
    #14 naming to docker.io/proving-ground/hermes-bare:s1 done
    #14 DONE 0.0s
    
    View build details: docker-desktop://dashboard/build/desktop-linux/desktop-linux/v1fs7bk1q2h8rnvcvoasuy4kd
```

### R2_ADAPTER — ACP adapter present in-image: PASS

```
$ docker run --rm proving-ground/hermes-bare:s1 hermes acp --check
exit 0; output: 'Hermes ACP check OK'
```

### R3_ROUNDTRIP — Full ACP round-trip into container yields a model reply: PASS

```
$ docker run -i --rm --add-host=host.docker.internal:host-gateway -v /var/folders/qv/7qgx9_pn67x1jtv0crtq3n1m0000gn/T/pg-entry-pos-h8ntrd_o:/workspace -w /workspace -e OPENAI_BASE_URL=http://host.docker.internal:11434/v1 -e OPENAI_API_KEY=ollama -e UACP_MODEL_ID=qwen3.5:4b proving-ground/hermes-bare:s1
prompt: 'Reply with exactly the single word: PONG'  endpoint: http://host.docker.internal:11434/v1
outcome=completed stop_reason=end_turn updates=58 text='The user is asking me to reply with a very specific response - just the single word "PONG". This seems like a simple echo or interaction, possibly testing my ab'
container stderr tail: 2026-07-17 19:46:57 [INFO] run_agent: OpenAI client created (chat_completion_stream_request, shared=False) thread=Thread-1 (_call):281473396961664 provider=custom base_url=http://host.docker.internal:11434/v1 model=qwen3.5:4b | 2026-07-17 19:47:01 [INFO] run_agent: OpenAI client closed (stream_request_complete, shared=False, tcp_force_closed=0) thread=Thread-1 (_call):281473396961664 provider=custom base_url=http://host.docker.internal:11434/v1 model=qwen3.5:4b | 2026-07-17 19:47:01 [INFO] agent.conversation_loop: API call #1: model=qwen3.5:4b provider=custom in=12910 out=59 total=12969 latency=4.1s | 2026-07-17 19:47:01 [INFO] agent.conversation_loop: Turn ended: reason=text_response(finish_reason=stop) model=qwen3.5:4b api_calls=1/90 budget=1/90 tool_turns=0 last_msg_role=assistant response_len=4 session=a353b6d7-303f-46d2-95d5-88597fc44a9c
```

### R4_ENV_USED — Injected env contract received AND used (dead endpoint must fail): PASS

```
$ docker run -i --rm --add-host=host.docker.internal:host-gateway -v /var/folders/qv/7qgx9_pn67x1jtv0crtq3n1m0000gn/T/pg-entry-neg-ie6vs4mk:/workspace -w /workspace -e OPENAI_BASE_URL=http://host.docker.internal:1/v1 -e OPENAI_API_KEY=ollama -e UACP_MODEL_ID=qwen3.5:4b proving-ground/hermes-bare:s1
prompt: 'Reply with exactly the single word: PONG'  endpoint: http://host.docker.internal:1/v1 (unreachable)
negative outcome=completed stop_reason=end_turn updates=4 genuine_reply=False backend_failed=True text='API call failed after 3 retries: Connection error.'
container stderr tail:    ⏱️  Elapsed: 21.23s  Context: 2 msgs, ~3,898 tokens | ❌ API failed after 3 retries — Connection error. |    💀 Final error: Connection error. | 2026-07-17 19:47:26 [ERROR] agent.conversation_loop: API call failed after 3 retries. Connection error. | provider=custom model=qwen3.5:4b msgs=2 tokens=~3,898
PASS-evidence: the negative reached the INJECTED dead endpoint and failed to connect (so the injected env drove the endpoint, not a baked-in default).
```

## Env-contract differential (R4 evidence)

| control | endpoint | outcome | stop_reason | genuine reply? | backend failed? |
|---|---|---|---|---|---|
| positive | host ollama | completed | end_turn | True | False |
| negative | dead endpoint | completed | end_turn | False | True |

positive reply text: `The user is asking me to reply with a very specific response - just the single word "PONG". This seems like a simple echo or interaction, possibly testing my ability to follow instructions. Let me mak`

negative reply text: `API call failed after 3 retries: Connection error.`

