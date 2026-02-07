**Calibration Data Structure**

```json
{
  "vl53l0x_0": {
    "baseline_mm": 100.5,
    "offset": 0,
    "timestamp": 1638360000,
    "samples": 10
  },
  "vl53l0x_1": {
    "baseline_mm": 105.2,
    "offset": 0,
    "timestamp": 1638360000,
    "samples": 10
  }
}
```

**Fields:**
- `baseline_mm`: The "home" position distance
- `offset`: Additional correction factor
- `timestamp`: When calibration was done
- `samples`: How many readings were averaged
