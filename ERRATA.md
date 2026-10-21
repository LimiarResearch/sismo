# Errata

Errors and findings reported after publication. The frozen results are never edited in place: an entry that changes a number is
resolved by a new run under a new version of the protocol, and says so.

## 1. WATCH and CTM go over the null ceiling because of the Shiryaev-Roberts threshold (2026-10-21)

**What was checked.** The WATCH code in competitors/watch_original/ against aaronhan223/watch at commit 3d17fca:
- martingales.py is identical to the original, byte for byte (sha256 ffc87486...);
- calculate_p_values is identical to the function of src/p_values.py;
- the Shiryaev-Roberts statistic in competitors/methods.py (_sr) computes the same sum as shiryaev_roberts_procedure of the original,
  sigma_n = sum over i < n of M_n / M_i;
- the input score (distance to the nearest training neighbor, ball tree), the p-values over calibration and test, the martingale
  started at the first test item and the adaptation levels (martingale 100 or Shiryaev-Roberts 1,000) follow src/main.py.

**What was found.** On the 370 null synthetic series of the approval, WATCH writes a log on 370 (default) and 368 (tuned), and an
alert on 23 and 360; CTM, on 370 and 369, and 24 and 362. Both go over the ceilings (alert 2%, log 5%) with both configurations. The
cause is the operating point, not the port:
- with the default Shiryaev-Roberts threshold of 10^4, the expected time to a false alarm is of the order of 10^4 items, below the
  18,000 scored items of a synthetic series;
- in the original composite_jumper_martingale, each of the five jumper rates redistributes the wealth of the whole mixture, not its
  own, so the mixture is not exactly a test martingale. On 40 sequences of 18,000 independent uniform p-values, the Shiryaev-Roberts
  statistic of the original code reached 10^4 at a median of 3,760 items; on 200 sequences, a version where each rate redistributes
  its own wealth reached it at a median of 11,151 items. The martingale itself never reached 100 in either case;
- the tuned configurations (protocol/tuned.json) were chosen by detection alone, without the nulls (protocol, section 4.3), and on the
  synthetic base the choice was Shiryaev-Roberts 1,000.

So WATCH and CTM were not allowed in any synthetic row, and the table compares the detector with the other 13 methods there.

**Known before this entry.** paineis/RESSALVAS.md (caveat 2, and the WATCH paragraph below the table) already records that the
weighted adapter in _watch_segment fits its scale on the whole series and uses items after the current one at the start of the
target, so it is not strictly causal after the first input alarm, and that the ineligibility comes from the Shiryaev-Roberts threshold
and not from that defect. This entry adds the check of the copied code against the original and the behavior of the original mixture
on independent uniform p-values. The adapter defect is still there: the sensitivity below runs the published adapter, unchanged.

**Sensitivity (information only, outside the verdict).** WATCH and CTM were run again on the 1,000 approval synthetic series with two
more configurations: the martingale threshold alone (Ville 100, no Shiryaev-Roberts) and the strictest point of the protocol grid
(Ville 1,000, Shiryaev-Roberts 10^6). The rows were recomputed with the rules of metrics/rows.py, unchanged.

| configuration | nulls: alert (ceiling 2%) | nulls: log (ceiling 5%) | S1 alert F1 | S2 log F1 |
|---|---|---|---|---|
| WATCH, Ville 100 alone | 1/370 | 11/370 | 0.000 | 0.535 |
| WATCH, Ville 1,000, SR 10^6 | 0/370 | 49/370 (over) | 0.000 | 0.571 |
| CTM, Ville 100 alone | 1/370 | 4/370 | 0.000 | 0.532 |
| CTM, Ville 1,000, SR 10^6 | 0/370 | 19/370 (over) | 0.000 | 0.576 |
| the detector | 0/370 | 6/370 | 0.996 | 0.929 |
| best allowed competitor in the table (CJSD) | | | 0.701 | 0.879 |

With the martingale threshold alone, WATCH and CTM stay under both ceilings and would be allowed in S1 and S2. In S1 they write no
alert inside the windows (the input martingale fires first, so every warning is a log); in S2 they reach 0.535 and 0.532, below CJSD.

The script outputs are in protocol/errata/1_watch/ (null_martingale_output.txt, score_output.txt). The 1,000 outputs with the extra
configurations (watch_sensitivity.zip, sha256 a6278032eab29adc5ba64e412ba78455914bd26b89df716562794c19a720067f) can be rebuilt with
protocol/errata/1_watch/sensitivity.py from publication.zip and checked with score.py; they take about 2 hours on 4 cores.

**What changes in the table.** Nothing. With the configurations above allowed, the best competitor of S1 and S2 is still CJSD, and
every verdict and status stays the same. The protocol is not changed: the configurations of a new run are fixed before it, in a
version 2.
