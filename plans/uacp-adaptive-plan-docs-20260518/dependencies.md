# Dependencies

```text
T1 skill doctrine
  -> T2 config wording
  -> T3 validator + T6 fixtures
  -> T4 Heartgate kernel
  -> T5 Guardian policy
  -> T7 verification/council
```

T3 and T6 may proceed together after schema details are final.

T4 depends on T2 semantics and T6 negative cases.

T5 can proceed independently but must not overclaim hard interception.

T7 blocks VERIFY if validator or Heartgate negative cases do not fail closed.
