# History files

These files were written by the code of the approval run, before the publication version. They are kept byte for byte, because their
hashes are cited (the approval seeds were drawn from frozen_approval_original.sha256) and because they record what was frozen at each
version of the protocol. The paths in them are the Portuguese paths of the code at that time (for example corredor/ for runner/,
concorrentes/ for competitors/, metricas/ for metrics/, geradores/ for generators/, dados/ for data/, protocolo/ for protocol/); the
map to the current names is in protocol/publication/keymap.json.

| file | what it is |
|---|---|
| frozen_v1.sha256 | the frozen file of protocol version 1 (protocol, section 10) |
| frozen_v1_1.sha256 | the frozen file of protocol version 1.1 |
| frozen_v1_2.sha256 | the frozen file of protocol version 1.2, on which the development run ran |
| frozen_approval_original.sha256 | the frozen file of protocol version 2, on which the approval run ran (sha256 ed41901cf9662f62e12598e99573e58713a5e81504c7293e4543e57151606eb6); protocol/seeds.json was drawn from it |
| approval_warnings_original.sha256 | the warnings manifest of the approval run: one sha256 per series (2,047 series) of the warning lists of every method and configuration and of the detector's records and events, keyed by the series names of the approval run (sha256 of the file 8af1b154452f32a89aa842df288f08f4ae2c4f5b9f64293e38ab5de852d0d16b) |

Each frozen file has 69 lines. The last line of each is not a file: it records the sha256 of the result of a check of the detector code
made before freezing (a1ac5de4c3f76ccf5f54499694d060db31e25c257cca8a2de265c2f76685ffb7). The frozen files of versions 1, 1.1 and 1.2
also list the top-level readme (LEIA-ME.md) and the reproduction script (reproduzir.sh) of that time; from version 2 on, the frozen
file is an explicit list without the documentation that receives the table (protocol, section 10, v2, item 2).

The seeds can be drawn again from the approval frozen file: `python -m runner.seeds protocol/history/frozen_approval_original.sha256`
writes protocol/seeds.json with the same seeds.
