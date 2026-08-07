# Cistern Monitor — Debug Session & Hardware Architecture Review

Reviewed at `7a105fc` (v1.15.0), 2026-08-07.

Scope: the analog front end, power architecture, digital bus, sensor
installation, and the firmware/cloud layers that the hardware depends on.
Findings are ordered by expected impact, not by layer.

---

## Part 1 — Live debug session

Three things were checked against the running system today. Two are broken
right now.

### 1.1 Firestore is refusing every read (LIVE)

```
$ curl "https://firestore.googleapis.com/v1/projects/cistern-blomquist/databases/(default)/documents/config/calibration?key=..."
{"error":{"code":429,"message":"Quota exceeded.","status":"RESOURCE_EXHAUSTED"}}
```

Every read fails the same way — single document get, collection list, and
`runQuery` alike. This is project-specific, not a network problem:
`raw.githubusercontent.com` returns 200 and unrelated `googleapis.com`
endpoints return 200 from the same host.

**Consequence:** the dashboard is down. `loadCalibration()` falls back to
built-in defaults, and both `fetchLatest()` and `queryReadings()` throw, so
`refresh()` takes the error path — which skips `checkAlerts()` entirely
(`dashboard/index.html:1289`). During this outage the dashboard will not raise
a "Device Offline" alert even if the device has been dead for a week.

**Most plausible driver — dashboard read amplification.** `docLimitForSpan()`
(`dashboard/index.html:552`) sizes the query to the window, and the device
writes one document per minute:

| Range button | Documents read per load |
|---|---|
| 24h (default) | ~1,440 |
| 7d | ~10,080 |
| 14d | ~20,160 |

The free-tier ceiling is 50,000 document reads/day. Two 14d clicks plus normal
browsing exhausts it. It gets worse: `ensureHistoryCovers()` skips a refetch
when narrowing a range, but `updateHistory()` then prunes `allHistory` to the
*new, narrower* `maxRangeHours()` and moves `historyCoveredFrom` with it
(`index.html:608-612`). So 14d → 1h → 14d is a full 20,160-document refetch,
not a cache hit. Every widen-narrow-widen cycle is another ~20k reads.

Confirm in the console under Firestore → Usage, then fix by downsampling
rather than by raising quota — see §7.1.

### 1.2 The device is probably in a reboot loop right now

This is the part that matters. `last_healthy_tick` is only advanced by a
**successful Firebase post** (`main.py:379`), and the software watchdog reboots
the device when it has not advanced in 5 minutes (`main.py:309`).

So if writes are refused for the same quota reason reads are — and there is no
reason to think otherwise — the device is resetting every 5 minutes,
indefinitely. `send_buffer` is RAM-only (`main.py:301`), so each reset discards
up to 30 buffered readings. The offline buffer, whose entire purpose is to
ride out a cloud outage, is destroyed by the watchdog on exactly the outage it
was built for.

The design error is that the watchdog treats *cloud reachability* as the
device's liveness signal. A monitor with a healthy sensor, healthy WiFi, and an
unreachable backend is not a hung device. Liveness should be "the loop
completed a sensor read"; failure to post is a separate, much slower concern.

### 1.3 Version drift

`raw.githubusercontent.com/.../main/version.txt` serves `1.15.0` and the OTA
endpoints are all reachable (200). If a device is reporting anything older, it
is not completing OTA — check `last_error` and the boot log once reads recover.

### 1.4 Test suite

`tests.test_sensor` and `tests.test_reliability` pass (23 tests). But
`test_sensor.py` still asserts against `V_MIN = 0.66`, `V_MAX = 3.3`
(`tests/test_sensor.py:37-38`) and a **horizontal-cylinder** volume formula
using `TANK_RADIUS_IN = 28.8`. Production uses `v_min = 0.882`, `v_max = 4.265`
and a rectangle-plus-dome formula against `tank_height_in = 65.5`. The file's
docstring claims it replicates the dashboard computation; it replicates a model
the dashboard stopped using. The tests are green and are verifying nothing.

`test_endpoints.py` writes real documents into the production `readings`
collection and cannot delete them — the security rules block delete, which the
code acknowledges at line 65. Every CI run injects junk readings that persist
for 30 days and consume write quota.

---

## Part 2 — Analog front end

This is where the real problems are.

### 2.1 The two-resistor "divider" is not a divider

Current wiring: sensor return → 220 Ω → **midpoint → ADS1115 A0** → 220 Ω → GND.

The ADC measures the midpoint against ground, which is the voltage across the
*bottom* resistor alone: `I × 220 Ω`. The top 220 Ω contributes nothing to the
measurement. It is not dividing anything — it is in series with the loop,
burning 4.4 V of compliance headroom at 20 mA for no benefit. A single 220 Ω
shunt to ground produces an electrically identical reading.

### 2.2 The ADC input exceeds its absolute maximum in any fault case

The README acknowledges 4.40 V at 20 mA against an ADS1115 limit of VDD+0.3 =
3.6 V, and argues it is safe because this tank only uses 1.46 m of the sensor's
5 m range (~8.7 mA, 1.91 V). **That argument only holds while everything is
working.** The overvoltage cases are precisely the fault cases:

- **Sensor fault signalling.** 4-20 mA transmitters report faults by driving
  *out of band*. NAMUR NE43 puts over-range at ≥21 mA; many transducers slam to
  21–24 mA on internal failure. 21 mA → 4.62 V at A0.
- **Loop short / water ingress.** If the cable or sensor shorts, the shunt sees
  whatever the supply delivers: 24 V / 440 Ω = 54.5 mA → 12 V at A0. That
  destroys the ADC and back-feeds the Pico's 3V3 rail through the ESD clamp.
- **MT3608 feedback fault.** The output-voltage trimpot on those modules is a
  tiny unsecured pot. Vibration or a knock takes the rail to ~28 V, raising
  every fault current proportionally.

There is no series resistance between the midpoint and A0, so nothing limits
current into the ADS1115's clamp diodes (datasheet limit: 10 mA). Even in the
"safe" 20 mA case the part clamps rather than measures — you get a wrong number
with no error flag, and current injected into the 3V3 rail.

### 2.3 Recommended front end

Replace both 220 Ω resistors with **one 150 Ω, 0.1%, 25 ppm/°C thin-film
resistor**, and add an RC into the ADC:

```
  Sensor BLACK (-) ──┬──[ 10kΩ ]──┬── ADS1115 A0
                     │            │
                  [150Ω]        [100nF]
                   0.1%           │
                   25ppm          │
                     ├────────────┴── ADS1115 A1  (differential low side)
                     │
                     └── MT3608 VOUT-  (star ground)
```

What each change buys:

| Change | Effect |
|---|---|
| 220+220 Ω → single 150 Ω | 20 mA → **3.00 V**, inside the ADC's range. A 24 mA fault reaches 3.60 V — exactly at, not past, the absolute max. Also returns 2.5 V of compliance to the loop. |
| 10 kΩ in series with A0 | Caps clamp current at ~2 mA even with the full 24 V rail applied to the node. Costs nothing in accuracy: the ADC's input leakage is a few nA, so the IR drop is sub-µV. |
| 100 nF to ground | Low-passes the MT3608's ~1.2 MHz switching noise at ~160 Hz and supplies the ADC's sampling charge, so the 10 kΩ source impedance is not a problem. |
| 0.1% / 25 ppm/°C part | See §2.5 — this is worth about 1.5 inches of water. |
| **Read A0–A1 differentially** | The ADS1115 is already capable of it. Measuring across the shunt instead of A0-to-ground rejects ground offset entirely (§3.3). Firmware change only: MUX `000` instead of `100`, i.e. config MSB `0x83`. |

Resolution is not a concern at 150 Ω. Full tank spans 0.600→1.301 V ≈ 5,600
counts at the ±4.096 V PGA — 0.26 mm of water per count. The ADC is roughly two
orders of magnitude better than the transducer; it is not the limiting factor
and never was.

### 2.4 The calibration constants are internally inconsistent

From `v_min = 0.882 V` at 4.000 mA, the shunt is 220.5 Ω. That same shunt at
20 mA gives **4.410 V**. The stored `v_max` is **4.265 V** — 3.3% low.

`v_max` is documented as "computed from two-point calibration," so it is a
fitted value, and it disagrees with the resistor model. Since depth is
`(v − v_min) / (v_max − v_min) × 5 m`, a 3.3% span error inflates every reading
by ~4.3%: about **+2.5 inches** of indicated depth on a full tank.

Resolve it by measurement, not arithmetic — put a DMM across the bottom
resistor and read its actual value. If it measures ~220 Ω, `v_max` should be
4.410; if the fitted 4.265 is right, the resistor is 213 Ω and `v_min` should be
0.853. Both cannot be true.

### 2.5 Error budget

Referred to tank depth, full scale 1.46 m (57.5 in). Transducer figures are
typical for the class — substitute real numbers from the datasheet if the part
is known.

| Source | Contribution | Notes |
|---|---|---|
| **Vent tube blocked/absent** | **±204 mm (±8.0 in)** | ±20 hPa weather swing × 10.2 mm H₂O per hPa. See §5.1. |
| Transducer thermal drift | ±40 mm (1.6 in) | ~0.02% FS/°C over a 40 °C swing, on a 5 m FS |
| **Shunt tempco (carbon film)** | **±38 mm (1.5 in)** | 300 ppm/°C × 40 °C = 1.2% of reading |
| Transducer accuracy | ±25 mm (1.0 in) | ±0.5% of 5 m FS |
| Calibration span error (§2.4) | +63 mm (2.5 in) | systematic, not random |
| ADS1115 gain + offset + noise | ±4 mm | negligible |
| Water density vs temperature | ±6 mm | negligible |

**RSS excluding the vent:** ~61 mm (2.4 in) ≈ 4% of tank ≈ 60 gallons.
**With a blocked vent:** ~213 mm (8.4 in) ≈ 15% of tank ≈ 220 gallons.

Two observations fall out of this table.

First, **the 5 m sensor is the wrong range.** The tank uses 29% of it, which
multiplies every %FS error term by 3.4×. A 2 m / 0.2 bar transducer is a
drop-in swap that improves accuracy ~2.5× for free.

Second, **the shunt resistor's tempco is one of the largest terms**, and it is
a $0.50 fix. A generic 5% carbon film part is 200–500 ppm/°C; in an outdoor
pump house seeing −10 °C to +50 °C that is ~1.2% of reading, which is 1.5
inches at a full tank. A 25 ppm/°C thin-film part reduces it to ~3 mm.

### 2.6 The v1.13.2 "drift" fix is treating a symptom

v1.13.2 added an I2C general-call reset and a discarded dummy conversion before
every read, to fix "slow voltage drift caused by residual charge accumulating
across single-shot power-down cycles."

That mechanism is not real at these impedances. The ADS1115's sampling
capacitor is ~20 pF against a 220 Ω source; it settles in nanoseconds, and
single-shot power-down does not leave a charge that survives to the next
conversion a minute later. Meanwhile the error budget above contains two terms
that produce exactly the observed symptom — a slow wander of a few tens of
millivolts — for real physical reasons: barometric pressure through the vent,
and the shunt's temperature coefficient. Both are diurnal and weather-correlated.

The two workarounds are not free. The general-call reset at
`sensor.py:47` writes to address `0x00`, which resets **every device on the
bus** — harmless today with one device, a landmine the day a second is added.
Both workarounds add I2C transactions to a bus that §4.1 shows is already
marginal, so each read now has three times as many chances to hit the bus hang
that `_recover_i2c()` exists to clean up.

**Diagnostic:** plot a week of `voltage` against local barometric pressure. If
they track at ~10 mm H₂O per hPa, it is the vent tube, and no amount of I2C
hygiene will fix it.

---

## Part 3 — Power architecture

### 3.1 The 5 V rail is wired to the wrong pin (defect)

Current: RS-15-5 5 V → **Pico VBUS**.

VBUS is bonded directly to the USB connector's 5 V pin. Feeding it externally
means that the moment someone plugs in USB, the RS-15-5 and the host port are
hard-tied and fighting over a few tens of millivolts of difference. The README
*instructs* plugging in USB for troubleshooting (`mpremote connect ... repl`),
so this is a documented workflow that back-drives a laptop's USB port.

The Pico datasheet's recommended external-supply topology is **VSYS (pin 39)
through a Schottky diode** — the onboard RT6150 then arbitrates between USB and
external automatically. Add a 1N5817 from the RS-15-5 5 V to VSYS and remove the
VBUS connection.

### 3.2 The 24 V loop is unfused (safety)

A boost converter has a DC path from input to output through the inductor and
catch diode. It cannot current-limit a shorted output — the short is fed
straight from the input. The RS-15-5 will happily deliver **3 A** into a shorted
sensor cable, through an MT3608 module whose inductor and SS34 diode are rated
for around 1–3 A. In an unattended well house, on a cable that runs into water,
that is a fire risk, not just a reliability one.

Add a **50 mA polyfuse or 100 mA fast fuse in series with the 24 V output.**
Normal loop current is ≤20 mA, so there is no nuisance-trip concern.

### 3.3 Ground topology

The MT3608 is non-isolated: its input return, output return, and the Pico's
ground are the same node. The boost draws roughly 50 mA from the 5 V rail to
deliver 8.7 mA at 24 V, and that current is *switching*. If the ADS1115's GND
reference shares wiring with that return path, the IR drop lands directly in
the measurement — 50 mA through 50 mΩ of jumper wire and connector resistance
is 2.5 mV ≈ 3.5 mm of water, and it moves with load and temperature. Screw
terminals and wire nuts in a damp pump-house box drift far more than 50 mΩ over
time.

Two fixes, both worth doing: **star-ground** at the MT3608 VOUT- node so the
ADS1115's ground is its own conductor, and **read the shunt differentially**
(§2.3), which makes the whole class of error common-mode.

### 3.4 No supply monitoring, and no way to get it back on the Pico

v1.14.3 correctly removed the VSYS ADC read — on a Pico W, GPIO29/ADC3 is shared
with the CYW43's SPI, and sampling it corrupts the WiFi interface. That was the
right call, but it left the system with no visibility into its own supply, which
is exactly what you want when diagnosing pump-start brownouts.

**The ADS1115 has three unused channels.** Bring the 5 V rail into A2 through a
divider (e.g. 100 k / 68 k → 2.02 V at 5.0 V) and, if reading differentially,
the 24 V rail into A3 (470 k / 68 k → 3.03 V at 24 V). That restores full supply
telemetry using hardware already on the board, with no risk to the WiFi chip.

Also add a **470 µF bulk capacitor on the 5 V rail** at the Pico. The RS-15-5
taps a well-pump circuit; motor start pulls the line down hard, and hold-up is
the cheapest brownout insurance available.

### 3.5 No surge protection

A mains-powered device sharing a junction box with an inductive motor load,
wired to a long cable that runs underground into water, has no MOV on the AC
side, no TVS on the 24 V loop, and no protection at the sensor cable entry. Pump
switching transients and nearby lightning both couple into that cable and arrive
at the ADS1115 input and the Pico.

Minimum: an MOV across the 120 VAC input, and an **SMAJ26A TVS across the 24 V
loop** at the terminal block. The 10 kΩ from §2.3 then protects the ADC behind
it. Worth also confirming the wire-nut tap at the pump junction box is in a
properly rated enclosure — that is a code question as much as an engineering one.

---

## Part 4 — Digital bus

### 4.1 400 kHz I2C is out of spec for this wiring

`sensor.py:10` runs the bus at 400 kHz. Two things make that marginal:

- The Pico's internal pull-ups are ~50–80 kΩ — far too weak. If the ADS1115 is a
  breakout board, its onboard pull-ups are typically 10 kΩ.
- At 10 kΩ against ~100 pF of jumper-wire capacitance, the rise time is ~1 µs.
  Fast-mode I2C requires under 300 ns.

The bus is being run roughly 3× faster than its RC allows. **`_recover_i2c()`
exists because of this.** Nobody writes a nine-clock bus-recovery routine and a
retry wrapper for a bus that works.

Fixes, in order of cost:

1. **`freq=400000` → `freq=100000`** at `sensor.py:10` and `:38`. Free, and
   100 kHz tolerates the 1 µs rise time. At one sample per minute the speed is
   irrelevant. Do this first.
2. Add 2.2 kΩ pull-ups to 3V3 (~220 ns rise) if 400 kHz is wanted back.
3. Keep the ADS1115 leads under 10 cm, twisted with a ground return.

### 4.2 Silent stale reads on conversion timeout

`_do_single_conversion()` polls the conversion-ready bit up to 20 times
(`sensor.py:58`), then **reads the conversion register regardless of whether the
bit ever set**. On timeout it returns the previous conversion's value as if it
were fresh, with no error. Raise on timeout instead — a missing reading is
recoverable, a silently stale one is not.

The register decode itself is correct: config `0xC3 0x83` is OS=1, MUX=100
(AIN0 single-ended), PGA=001 (±4.096 V), MODE=1 (single-shot), 128 SPS,
comparator disabled — consistent with the `× 4.096 / 32767` scaling. (Pedantically
that should be `/ 32768`; the error is 0.003% and not worth a commit.)

### 4.3 One sample per minute, unaveraged

A single 128 SPS conversion per minute captures whatever the surface was doing
at that instant — fill turbulence, pump inrush, slosh. Averaging 16 conversions
costs ~125 ms and roughly halves the visible noise. Alternatively drop the data
rate to 8 SPS, where the ADS1115's own noise floor is substantially lower. Either
is nearly free at this duty cycle.

---

## Part 5 — Sensor and installation

### 5.1 The vent tube (highest-impact item in this review)

A gauge-type submersible transducer references its diaphragm to atmosphere
through a vent tube inside the cable. **1 hPa of barometric change equals 10.2 mm
of apparent water depth.** A normal weather swing of ±20 hPa is ±204 mm — eight
inches, or about 220 gallons in this tank. A passing front can move it 35 hPa.

Three ways this goes wrong, all of them common:

1. The vent tube is pinched, kinked, or sealed in a wire nut.
2. The cable end is terminated in a damp junction box with no desiccant, so the
   tube breathes moist air and eventually wets the back of the diaphragm.
3. **The transducer is a sealed/absolute type, not vented** — many inexpensive
   "5 m level sensors" are. Then the error is permanent and uncorrectable in
   hardware.

Check first: identify the exact transducer part number and confirm it is
vented-gauge; then confirm the vent tube is open and terminates in a dry
enclosure with a desiccant cartridge or vent filter. This single item is larger
than every electrical error in §2.5 combined.

### 5.2 Mechanical

Not visible from the repo, but worth confirming: the sensor should hang in a
stilling well (a length of perforated PVC) rather than free in the tank, to
damp fill turbulence and keep it off the floor sediment. Note the exact
suspension height — §2.4's calibration argument depends on knowing where zero is.

---

## Part 6 — Firmware

v1.15.0 already fixed the serious ones: hardware watchdog, socket timeouts on
all network calls, and the `ticks_ms()` wrap in uptime. What remains:

### 6.1 Buffered readings are silently discarded (bug)

`main.py:368-374`:

```python
still_failed = []
for buffered in send_buffer:
    feed()
    if not post_reading(buffered):
        still_failed.append(buffered)
        break
send_buffer = still_failed
```

If the 5th of 30 buffered readings fails, `still_failed` holds only that one
reading and **items 6 through 30 are dropped**. Stopping on first failure is
correct; throwing away everything behind it is not. Should be
`send_buffer = send_buffer[i:]`.

### 6.2 Watchdog conflates cloud reachability with liveness

See §1.2. Advance `last_healthy_tick` on a successful *sensor read*, and handle
prolonged post failure separately and much more slowly (a WiFi recycle, then an
hourly reboot ceiling — not a 5-minute one).

### 6.3 `ntp_synced` is computed and never sent

`main.py:170` sets `telemetry['ntp_synced'] = False` when the RTC is unsynced,
but `post_reading()` only forwards keys in its explicit allowlist, and
`ntp_synced` is not one of them — nor is it in the Firestore rules' `hasOnly`
list, so adding it to the payload alone would get the whole document rejected
with a 403.

This matters more than it looks. If NTP never syncs, the RTC sits at 2000-01-01,
so `_iso_timestamp()` stamps readings in the year 2000 **and** `expireAt`
becomes 2000-01-31 — already in the past, so Firestore's TTL deletes the
documents almost immediately. The device appears to post successfully and the
data silently evaporates. The one signal that would explain it never leaves the
device. Add `ntp_synced` to both the allowlist and the security rules.

### 6.4 Debug instrumentation left in the hot loop

`main.py:351-353` calls `micropython.mem_info()` every iteration, wrapped in two
`log.info()` calls. `mem_info()` prints to stdout only, so nothing useful reaches
the log — but the two log lines are written to flash every 60 seconds. Combined
with `log.py`'s truncation strategy (read all 16 KB of lines into RAM, rewrite
the newest half), that is frequent whole-file rewrites on flash, and a power cut
mid-rewrite loses the log. Remove the `mem_info()` block; `free_mem` and
`alloc_mem` are already in telemetry.

### 6.5 The offline buffer does not survive a reboot

`send_buffer` is a RAM list (`main.py:301`), and the two guards most likely to
fire during an outage — the watchdog (§1.2) and the low-memory reboot at
`main.py:316` — both destroy it. Thirty full telemetry dicts is also real heap
pressure against a 20 KB `LOW_MEM_THRESHOLD`, so the buffer filling can itself
trigger the reboot that discards it. Spill the buffer to a flash file, or
downgrade the retained fields to `(timestamp, raw, voltage)` so 30 entries cost
a few hundred bytes instead of several KB.

### 6.6 OTA integrity

Three gaps, in severity order:

- **No TLS verification.** MicroPython's `urequests` does not verify certificates
  unless given a CA bundle. The device downloads Python source and executes it on
  next boot, so anything that can MITM the connection has arbitrary code
  execution on a mains-powered device. There is also no signature or checksum.
- **Non-atomic across files.** Each file is staged to `.tmp` and renamed
  individually, but the six files are committed one at a time. Power loss
  halfway leaves a mixed-version filesystem with the *old* `version.txt`, so the
  device will not re-attempt the update it needs. Stage all files, verify all,
  then rename all, then `version.txt`.
- **Whole-file reads into RAM.** `download_file()` does `r.text` on each file.
  This is the same memory pressure that caused the v1.14.0 boot loop. Stream to
  the temp file in chunks.

---

## Part 7 — Cloud and data architecture

### 7.1 One document per minute is the wrong storage granularity

1,440 documents/day, 43,200 alive at any time under the 30-day TTL. That is what
makes any historical view expensive enough to exhaust quota (§1.1). Water level
in a 1,500 gallon cistern does not carry minute-resolution information worth
20,000 document reads to display.

Roll up on write: keep minute readings for 48 hours, and have the device (or a
scheduled function) write a 15-minute aggregate document for anything older. A
14-day view then costs ~1,340 reads instead of 20,160 — a 15× reduction — and
the charts look the same.

### 7.2 Anyone can write to the readings collection

The security rules validate *shape*, not *identity*: `allow create` requires the
right fields and types and nothing else. The API key ships in the dashboard and
is committed in `config.py.example`, and Firebase web API keys are not secrets in
any case. So anyone who has seen the dashboard can inject arbitrary readings,
poison the history, and exhaust the write quota.

Terraform already enables anonymous auth (`firebase.tf:140-150`) but the rules
never require it. Add `request.auth != null` at minimum; Firebase App Check is
the real answer.

### 7.3 There is no low-water alert

`checkAlerts()` (`index.html:1158`) fires on device-offline and low-voltage
(sensor fault). It does not alert on the tank actually running low — the one
thing a cistern monitor exists to tell you.

And every alert is browser-side: it requires an open tab, and `refresh()` skips
`checkAlerts()` entirely on the error path (§1.1), so the alerting stops in
exactly the situations worth alerting about. Move the threshold checks server-side
— a scheduled Cloud Function reading the latest document and pushing email/SMS —
and keep the browser notifications as a convenience layer.

### 7.4 No device identity

Readings go into one flat collection with no device ID. A second cistern, or a
bench unit posting alongside the field unit, requires a schema migration. Add a
`device_id` field now, while there is one device and the change is free.

---

## Part 8 — What to do, in order

**Today (no hardware access needed)**

1. Confirm the Firestore quota state in the console and get reads working again.
2. Fix the watchdog liveness condition (§6.2) — the device is likely rebooting
   every 5 minutes right now.
3. Fix the buffer-drop bug (§6.1), send `ntp_synced` (§6.3), remove the
   `mem_info()` block (§6.4).
4. `freq=400000` → `freq=100000` (§4.1). One character, removes the most likely
   cause of the I2C hangs.
5. Downsample historical storage (§7.1) so the quota problem cannot recur.

**Next site visit — ~$8 of parts**

| Part | Purpose | § |
|---|---|---|
| 150 Ω 0.1% 25 ppm/°C thin film | replaces both 220 Ω; fixes overvoltage *and* the largest electrical error term | 2.3, 2.5 |
| 10 kΩ + 100 nF | ADC fault protection and switching-noise filter | 2.3 |
| 1N5817 Schottky | 5 V into VSYS instead of VBUS | 3.1 |
| 50 mA polyfuse | 24 V loop short protection | 3.2 |
| SMAJ26A TVS + MOV | surge protection | 3.5 |
| 470 µF electrolytic | 5 V bulk / brownout hold-up | 3.4 |

Plus, at no parts cost: star-ground the ADS1115 (§3.3), switch to differential
A0–A1 (§2.3), and bring the 5 V and 24 V rails into the spare ADC channels
(§3.4).

**Investigate before spending anything else**

1. **Identify the transducer part number and confirm it is vented-gauge, then
   confirm the vent tube is open and terminated dry with desiccant** (§5.1).
   This is worth more than every other item in this review combined.
2. Measure the actual shunt resistance and resolve the `v_min`/`v_max`
   contradiction (§2.4).
3. Plot a week of voltage against barometric pressure (§2.6). If they correlate,
   §5.1 is confirmed and the v1.13.2 I2C workarounds can be reverted.
4. Consider a 2 m transducer instead of 5 m — a 2.5× accuracy improvement for
   the price of a part swap (§2.5).
