"""
Standalone port of the NAB "htmcore" detector (htm-community/NAB,
nab/detectors/htmcore/htmcore_detector.py, commit
98cdba6d9b698db102b1701ab8a885e88435467b) for a single univariate series.

Pipeline per record (copied from HtmcoreDetector.initialize/modelRun):
  RDSE(value) + DateEncoder(timeOfDay) -> SpatialPooler -> TemporalMemory
  -> raw anomaly (tm.anomaly) -> AnomalyLikelihood(learningPeriod)
  -> anomaly_score = max(spatialAnomaly, likelihood)

Differences from the NAB code (none affect the arithmetic of the scores):
  * no NAB base class / pandas DataFrame / CSV I/O; the series is passed in.
  * the probationary period is computed with NAB's formula
    (min(floor(0.15 * N), 0.15 * 5000)) from len(values).
  * HTMCORE_OPTIMIZE / params.json and the pandaVis baking code are dropped;
    `params` (nested dict) overrides default_parameters instead.
  * if `timestamps` is None, synthetic timestamps are generated
    (2015-01-01 00:00 + i * 5 minutes) because the detector always encodes
    the time of day.
  * optional params['seed']: NAB uses seed=0 for SP and TM and leaves the
    RDSE seed at 0; in htm.core seed 0 means "pick a random seed", so the NAB
    detector is NOT deterministic (scores differ between runs). By default
    this port keeps that behaviour; params={'seed': N} (N > 0) uses N as
    the seed of RDSE, SP and TM and makes runs reproducible.

Requires htm.core (package "htm") built from https://github.com/htm-community/htm.core.
"""

import copy
import datetime
import math
import time

# htm.core imports (same as the NAB detector, minus the unused Predictor)
from htm.bindings.sdr import SDR, Metrics
from htm.encoders.rdse import RDSE, RDSE_Parameters
from htm.encoders.date import DateEncoder
from htm.bindings.algorithms import SpatialPooler
from htm.bindings.algorithms import TemporalMemory
from htm.algorithms.anomaly_likelihood import AnomalyLikelihood

# Fraction outside of the range of values seen so far that will be considered
# a spatial anomaly regardless of the anomaly likelihood calculation.
SPATIAL_TOLERANCE = 0.05

# NAB runner default (nab/runner.py: self.probationaryPercent = 0.15)
PROBATIONARY_PERCENT = 0.15

# Verbatim copy of NAB htmcore default_parameters
default_parameters = {
  # there are 2 (3) encoders: "value" (RDSE) & "time" (DateTime weekend, timeOfDay)
  'enc': {
    "value" : # RDSE for value
      {'resolution': 0.001,
        'size': 4000,
        'sparsity': 0.10
      },
    "time": {  # DateTime for timestamps
        'timeOfDay': (21, 9.49),
        'weekend': 0 #21 TODO try impact of weekend
        }},
  'predictor': {'sdrc_alpha': 0.1},
  'sp': {
    'boostStrength': 0.0,
    'columnCount': 2048,
    'localAreaDensity': 40/2048,
    'potentialPct': 0.4,
    'synPermActiveInc': 0.003,
    'synPermConnected': 0.2,
    'synPermInactiveDec': 0.0005},
  'tm': {
    'activationThreshold': 13,
    'cellsPerColumn': 32,
    'initialPerm': 0.21,
    'maxSegmentsPerCell': 128,
    'maxSynapsesPerSegment': 32,
    'minThreshold': 10,
    'newSynapseCount': 20,
    'permanenceDec': 0.1,
    'permanenceInc': 0.1},
}


def getProbationPeriod(probationPercent, fileLength):
  """Copy of nab.util.getProbationPeriod."""
  return min(
    math.floor(probationPercent * fileLength),
    probationPercent * 5000)


def _deep_update(base, override):
  for k, v in override.items():
    if isinstance(v, dict) and isinstance(base.get(k), dict):
      _deep_update(base[k], v)
    else:
      base[k] = v
  return base


def _to_datetime(t):
  if isinstance(t, datetime.datetime):          # includes pandas.Timestamp
    return t
  if hasattr(t, "to_pydatetime"):
    return t.to_pydatetime()
  if isinstance(t, str):
    return datetime.datetime.fromisoformat(t)
  try:                                          # numpy.datetime64
    import numpy as np
    if isinstance(t, np.datetime64):
      return datetime.datetime.utcfromtimestamp(
        (t - np.datetime64(0, "s")) / np.timedelta64(1, "s"))
  except ImportError:
    pass
  if isinstance(t, (int, float)):               # epoch seconds
    return datetime.datetime.utcfromtimestamp(float(t))
  raise TypeError("unsupported timestamp type: %r" % type(t))


class HtmcoreModel:
  """Same state and steps as NAB HtmcoreDetector (initialize + modelRun)."""

  def __init__(self, probationaryPeriod, parameters=None,
               useLikelihood=True, useSpatialAnomaly=True, seed=None):
    self.seed = int(seed) if seed else 0   # 0 = NAB default (random in htm.core)
    self.probationaryPeriod = probationaryPeriod
    self.useLikelihood      = useLikelihood
    self.useSpatialAnomaly  = useSpatialAnomaly
    self.inputs_ = []
    self.iteration_ = 0
    self.initialize(parameters if parameters is not None else default_parameters)

  def initialize(self, parameters):
    # setup spatial anomaly
    if self.useSpatialAnomaly:
      # Keep track of value range for spatial anomaly detection
      self.minVal = None
      self.maxVal = None

    ## setup Enc, SP, TM, Likelihood
    self.encTimestamp = DateEncoder(timeOfDay= parameters["enc"]["time"]["timeOfDay"],
                                    weekend  = parameters["enc"]["time"]["weekend"])

    scalarEncoderParams            = RDSE_Parameters()
    scalarEncoderParams.size       = parameters["enc"]["value"]["size"]
    scalarEncoderParams.sparsity   = parameters["enc"]["value"]["sparsity"]
    scalarEncoderParams.resolution = parameters["enc"]["value"]["resolution"]
    # Added (optional): NAB leaves the RDSE seed at 0 (= random in htm.core).
    if self.seed:
      scalarEncoderParams.seed     = self.seed

    self.encValue = RDSE( scalarEncoderParams )
    encodingWidth = (self.encTimestamp.size + self.encValue.size)
    self.enc_info = Metrics( [encodingWidth], 999999999 )

    # SpatialPooler
    spParams = parameters["sp"]
    self.sp = SpatialPooler(
      inputDimensions            = (encodingWidth,),
      columnDimensions           = (spParams["columnCount"],),
      potentialPct               = spParams["potentialPct"],
      potentialRadius            = encodingWidth,
      globalInhibition           = True,
      localAreaDensity           = spParams["localAreaDensity"],
      synPermInactiveDec         = spParams["synPermInactiveDec"],
      synPermActiveInc           = spParams["synPermActiveInc"],
      synPermConnected           = spParams["synPermConnected"],
      boostStrength              = spParams["boostStrength"],
      wrapAround                 = True,
      seed                       = self.seed,  # NAB: 0
    )
    self.sp_info = Metrics( self.sp.getColumnDimensions(), 999999999 )

    # TemporalMemory
    tmParams = parameters["tm"]
    self.tm = TemporalMemory(
      columnDimensions          = (spParams["columnCount"],),
      cellsPerColumn            = tmParams["cellsPerColumn"],
      activationThreshold       = tmParams["activationThreshold"],
      initialPermanence         = tmParams["initialPerm"],
      connectedPermanence       = spParams["synPermConnected"],
      minThreshold              = tmParams["minThreshold"],
      maxNewSynapseCount        = tmParams["newSynapseCount"],
      permanenceIncrement       = tmParams["permanenceInc"],
      permanenceDecrement       = tmParams["permanenceDec"],
      predictedSegmentDecrement = 0.0,
      maxSegmentsPerCell        = tmParams["maxSegmentsPerCell"],
      maxSynapsesPerSegment     = tmParams["maxSynapsesPerSegment"],
      externalPredictiveInputs  = self.encTimestamp.size,
      seed                      = self.seed,  # NAB: 0
    )
    self.tm_info = Metrics( [self.tm.numberOfCells()], 999999999 )

    # setup likelihood, these settings are used in NAB
    if self.useLikelihood:
      learningPeriod         = int(math.floor(self.probationaryPeriod / 2.0))
      self.anomalyLikelihood = AnomalyLikelihood(learningPeriod)

  def modelRun(self, ts, val):
    """Returns (anomalyScore, rawScore), as NAB HtmcoreDetector.modelRun."""
    self.inputs_.append( val )
    self.iteration_ += 1

    # 1. Encoding
    dateBits        = self.encTimestamp.encode(ts)
    valueBits       = self.encValue.encode(float(val))
    encoding = SDR( self.encTimestamp.size + self.encValue.size ).concatenate([valueBits, dateBits])
    self.enc_info.addData( encoding )

    # 2. Spatial Pooler
    activeColumns = SDR( self.sp.getColumnDimensions() )
    self.sp.compute(encoding, True, activeColumns)
    self.sp_info.addData( activeColumns )

    # 3. Temporal Memory
    self.tm.compute(activeColumns, learn=True)
    self.tm_info.addData( self.tm.getActiveCells().flatten() )

    # 4.2 Anomaly
    spatialAnomaly = 0.0
    if self.useSpatialAnomaly:
      # Update min/max values and check if there is a spatial anomaly
      if self.minVal != self.maxVal:
        tolerance = (self.maxVal - self.minVal) * SPATIAL_TOLERANCE
        maxExpected = self.maxVal + tolerance
        minExpected = self.minVal - tolerance
        if val > maxExpected or val < minExpected:
          spatialAnomaly = 1.0
      if self.maxVal is None or val > self.maxVal:
        self.maxVal = val
      if self.minVal is None or val < self.minVal:
        self.minVal = val

    temporalAnomaly = raw = self.tm.anomaly
    if self.useLikelihood:
      temporalAnomaly = self.anomalyLikelihood.compute(temporalAnomaly)

    anomalyScore = max(spatialAnomaly, temporalAnomaly) # this is the "main" anomaly, compared in NAB
    return (anomalyScore, raw)


def scores(values, timestamps=None, params=None):
  """
  Runs the NAB htmcore detector on one univariate series.

  values     : sequence of numbers.
  timestamps : optional sequence of timestamps (datetime, pandas.Timestamp,
               numpy.datetime64, ISO string or epoch seconds), same length.
               If None: 2015-01-01 00:00 + i * 5 min.
  params     : optional dict. Nested keys 'enc', 'sp', 'tm' override NAB's
               default_parameters; extra keys: 'seed' (None = NAB behaviour,
               random seeds; int > 0 = reproducible), 'probationaryPercent' (0.15),
               'useLikelihood' (True), 'useSpatialAnomaly' (True).

  Returns one float per item: NAB "anomaly_score" =
  max(spatialAnomaly, AnomalyLikelihood.compute(tm.anomaly)).
  """
  values = [float(v) for v in values]
  n = len(values)
  if timestamps is None:
    t0 = datetime.datetime(2015, 1, 1)
    timestamps = [t0 + datetime.timedelta(minutes=5 * i) for i in range(n)]
  else:
    timestamps = [_to_datetime(t) for t in timestamps]
    if len(timestamps) != n:
      raise ValueError("values and timestamps have different lengths")

  params = dict(params or {})
  probationaryPercent = params.pop("probationaryPercent", PROBATIONARY_PERCENT)
  useLikelihood = params.pop("useLikelihood", True)
  useSpatialAnomaly = params.pop("useSpatialAnomaly", True)
  seed = params.pop("seed", None)
  model_params = _deep_update(copy.deepcopy(default_parameters), params)

  model = HtmcoreModel(getProbationPeriod(probationaryPercent, n), model_params,
                       useLikelihood=useLikelihood,
                       useSpatialAnomaly=useSpatialAnomaly, seed=seed)
  out = []
  for ts, v in zip(timestamps, values):
    out.append(float(model.modelRun(ts, v)[0]))
  return out


if __name__ == "__main__":
  # Self-test on a synthetic series only: noisy sine, level shift at t=2000.
  import numpy as np
  rng = np.random.default_rng(0)
  n = 3000
  t = np.arange(n)
  x = np.sin(2 * np.pi * t / 100.0) + 0.1 * rng.standard_normal(n)
  x[2000:] += 3.0
  t0 = time.perf_counter()
  s = scores(x)
  dt = time.perf_counter() - t0
  s = np.asarray(s)
  print("n=%d  time=%.2fs  per1000=%.2fs" % (n, dt, dt / n * 1000))
  print("len(scores)=%d  finite=%s  min=%.4f max=%.4f" % (len(s), np.isfinite(s).all(), s.min(), s.max()))
  print("mean score [500,2000)=%.4f  [2000,2050)=%.4f  max [2000,2050)=%.4f  argmax>=1000: %d"
        % (s[500:2000].mean(), s[2000:2050].mean(), s[2000:2050].max(), 1000 + int(np.argmax(s[1000:]))))
  print("first index >= 0.5 after 1000:", 1000 + int(np.argmax(s[1000:] >= 0.5)) if (s[1000:] >= 0.5).any() else None)
