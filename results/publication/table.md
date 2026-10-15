| row | detector | best competitor | its value | standard error of the difference | verdict | status |
|---|---|---|---|---|---|---|
| S1 relation breaks: alert | 0.996 | cjsd|q_tau=0.9,q_tau_x=1.0,tau=0.015012273678999061,tau_x=-0.0018571807304241794 | 0.701 | 0.027 | WON | PASSED |
| S2 input changes: log | 0.929 | cjsd|q_tau=1.0,q_tau_x=1.0,tau=0.015475023824050216,tau_x=-0.0018571807304241794 | 0.879 | 0.009 | WON | PASSED |
| S3 where: detection with the right field, among N | 0.996 | adwin/field|delta=1e-06 | 0.438 | 0.022 | WON | PASSED |
| S4a what: right direction | 1.000 (n = 209; null 0.500, n = 209) | - | - | 0.035 | ABOVE NULL | PASSED |
| S4b what: size within 0.25 sd | 1.000 (n = 179; null 0.240, n = 179) | - | - | 0.032 | ABOVE NULL | PASSED |
| S4c what: became the new normal on the steps that stay | 0.978 (n = 180; null 0.000, n = 180) | - | - | 0.011 | ABOVE NULL | PASSED |
| S5 slow drift: in the log and no alert | 1.000 | per_field_test|alpha=0.05,window=1000,window_step=250 | 1.000 | 0.000 | TIED | PASSED |
| S6 declared limit L1: slow_real | 0.929 | cjsd|q_tau=1.0,q_tau_x=1.0,tau=0.015475023824050216,tau_x=-0.0018571807304241794 | 0.333 | 0.099 | WON | limit L1 not confirmed in this sample |
| S6 declared limit L2: cat_real | 0.520 | cjsd|q_tau=1.0,q_tau_x=1.0,tau=0.015475023824050216,tau_x=-0.0018571807304241794 | 0.114 | 0.101 | WON | limit L2 not confirmed in this sample |
| S6 declared limit L3: xor | 0.000 | cjsd|q_tau=0.9,q_tau_x=1.0,tau=0.015012273678999061,tau_x=-0.0018571807304241794 | 0.967 | 0.033 | LOST | limit L3 confirmed |
| S7 nulls: runs with a warning (ceiling: alert 2%, log 5%) | alert 0/370; log 6/370 | - | - | - | - | PASSED |
| P1 NAB: event F1 | 0.165 | hddm_w/field|drift_confidence=0.01 | 0.405 | 0.070 | LOST | FAILED |
| P1L4 NAB: events shorter than 10 items (limit L4) | - (n = 0) | - | - | - | NO DATA | limit L4 not measured (n = 0) |
| P1c NAB (warmup500, information only): event F1 | 0.213 | hddm_a/field|drift_confidence=1e-05 | 0.351 | 0.056 | LOST | information only |
| P4 SMD: event F1 | 0.063 | cjsd|q_tau=1.0,q_tau_x=1.0,tau=None,tau_x=-0.008886549564022128 | 0.000 | 0.006 | WON | FAILED (detector's null above the ceiling) |
| P4L4 SMD: events shorter than 10 items (limit L4) | 0.071 (n = 127) | cjsd|q_tau=1.0,q_tau_x=1.0,tau=None,tau_x=-0.008886549564022128 | 0.000 | 0.024 | WON | limit L4 not confirmed in this sample |
| P4o SMD where: detection with the right fields, among 38 | 0.180 | - | - | - | NO COMPETITOR | FAILED (detector's null above the ceiling) |
| P5 SMAP: event F1 | 0.091 | per_field_test|alpha=0.01,window=500,window_step=50 | 0.368 | 0.045 | LOST | FAILED (detector's null above the ceiling) |
| P5L4 SMAP: events shorter than 10 items (limit L4) | - (n = 0) | - | - | - | NO DATA | limit L4 not measured (n = 0) |
| P6 MSL: event F1 | 0.222 | per_field_test|alpha=0.05,window=250,window_step=250 | 0.176 | 0.102 | TIED | FAILED (detector's null above the ceiling) |
| P6L4 MSL: events shorter than 10 items (limit L4) | - (n = 0) | - | - | - | NO DATA | limit L4 not measured (n = 0) |
| M1 contingency: warning on the route's error field within 60 min | 0.700 | matrix_profile|k=4.0,m=100 | 1.000 | 0.142 | LOST | FAILED |
| M2 incident: warning on the probe within 10 min and start attributed inside the window | 1.000 | hddm_w/field|drift_confidence=0.001 | 1.000 | 0.000 | TIED | PASSED |
| M3 regime change: became the new normal within 15 days | 0.667 (n = 15; null 0.000, n = 155) | - | - | 0.122 | ABOVE NULL | PASSED |
| M4 drift: the portfolio becomes the new normal in the normal lives and never without drift | normal [2, 0, 1]; no_drift [1] | - | - | - | - | FAILED |
| M5 return: back to normal within 180 min after the outage | 0.000 (n = 7; null 0.000, n = 8) | - | - | 0.000 | NOT ABOVE NULL | FAILED |

**The benchmark: FAILED** (18 rows decide; not passed: P1 NAB: event F1, P4 SMD: event F1, P4o SMD where: detection with the right fields, among 38, P5 SMAP: event F1, P6 MSL: event F1, M1 contingency: warning on the route's error field within 60 min, M4 drift: the portfolio becomes the new normal in the normal lives and never without drift, M5 return: back to normal within 180 min after the outage)

**NAB score (standard profile; official NAB rules; information only)**

Approval series, default and tuned configurations (36 series)

| method and configuration | score |
|---|---|
| htm|threshold=0.9999 | 54.92 |
| htm|threshold=0.5014187204194446 | 43.76 |
| isolation_forest|q=0.9999 | 36.20 |
| ddm/field|drift_threshold=3.0,warm_start=100 | 33.36 |
| page_hinkley/field|delta=0.005,min_instances=30,threshold=50.0 | 33.09 |
| ddm/field|drift_threshold=3.0,warm_start=30 | 32.69 |
| adwin/field|delta=0.002 | 30.94 |
| adwin/field|delta=1e-06 | 30.70 |
| watch|sr=10000.0,ville=100.0 | 25.32 |
| kswin/field|alpha=1e-05,stat_size=30,window_size=300 | 24.39 |
| watch|sr=1000000.0,ville=20.0 | 23.71 |
| hddm_a/field|drift_confidence=0.001 | 22.44 |
| page_hinkley/field|delta=0.0005,min_instances=30,threshold=200.0 | 19.62 |
| hddm_w/field|drift_confidence=0.01 | 18.65 |
| ewma/field|L=4.0,lam=0.3 | 17.40 |
| hddm_a/field|drift_confidence=1e-05 | 17.20 |
| cusum/field|h=8.0,k=1.0 | 15.84 |
| hddm_w/field|drift_confidence=0.001 | 14.72 |
| detector|default | 14.27 |
| per_field_test|alpha=0.05,window=1000,window_step=250 | 6.21 |
| kswin/field|alpha=0.005,stat_size=30,window_size=100 | 5.84 |
| per_field_test|alpha=0.001,window=1000,window_step=50 | 4.21 |
| cjsd|q_tau=1.0,q_tau_x=1.0,tau=None,tau_x=0.0001334877264830281 | 0.00 |
| cjsd|q_tau=0.9,q_tau_x=0.9,tau=None,tau_x=-0.004383720895909596 | 0.00 |
| matrix_profile|k=3.0,m=100 | -0.08 |
| matrix_profile|k=None,m=100 | -0.15 |
| ewma/field|L=3.0,lam=0.2 | -27.80 |
| cusum/field|h=5.0,k=0.5 | -65.31 |
| isolation_forest|q=None | -118.70 |

All 58 series, default configurations (58 series)

| method and configuration | score |
|---|---|
| ddm/field|drift_threshold=3.0,warm_start=30 | 35.00 |
| htm|threshold=0.5014187204194446 | 34.94 |
| watch|sr=10000.0,ville=100.0 | 28.28 |
| hddm_a/field|drift_confidence=0.001 | 26.39 |
| adwin/field|delta=0.002 | 23.18 |
| hddm_w/field|drift_confidence=0.001 | 22.55 |
| page_hinkley/field|delta=0.005,min_instances=30,threshold=50.0 | 16.93 |
| detector|default | 16.27 |
| per_field_test|alpha=0.05,window=1000,window_step=250 | 7.73 |
| cjsd|q_tau=1.0,q_tau_x=1.0,tau=None,tau_x=0.0001334877264830281 | 0.00 |
| matrix_profile|k=None,m=100 | -0.16 |
| kswin/field|alpha=0.005,stat_size=30,window_size=100 | -5.03 |
| ewma/field|L=3.0,lam=0.2 | -88.70 |
| cusum/field|h=5.0,k=0.5 | -144.54 |
| isolation_forest|q=None | -173.34 |

Published, not measured here: HTM (the htmcore detector of the NAB community) scores 63.08 on the whole corpus (htm-community/NAB, results/final_results.json, commit 98cdba6). That number is from 2019 and 2020, from an earlier version of the htm.core likelihood, with the threshold optimized by NAB on the whole corpus; the current htmcore code, which this benchmark runs, was changed in 2021 with no new published score (see the record of the approval).
