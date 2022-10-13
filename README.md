# psu-progs

A collection of utilities to put a computer-connected power supplies to good use.

The extraordinarily compact collection includes only a CLI tool for charging lithium-ion batteries with a Korad PSU.


# Installation
```shell
pip install psu-progs
```

# Quick-show-me-a-thing
```shell
# Charge a 1400mAh lithium-ion battery, with a Korad PSU connected at /dev/ttyACM0
korad-charge-lithium-ion -p /dev/ttyACM0 -c 1.4
```

# Full command help
```
Usage: korad-charge-lithium-ion [OPTIONS]

  Charge a Li-ion battery using a Korad K300XP power supply

Options:
  -p, --port DEVICE              Name of serial device the power supply can be
                                 communicated through, e.g. /dev/ttyACM0
                                 [default: /dev/ttyUSB1; required]
  -c, --capacity FLOAT           Labeled capacity of battery, in amp hours.
                                 [required]
  --charge-current FLOAT         Current to use while in the constant-current
                                 charging phase, in amps. If not specified,
                                 this defaults to half the battery_capacity.
  --charge-voltage FLOAT         Voltage to use while in constant-voltage
                                 phase. For Li-ion cells, this value should be
                                 ≤4.2.  [default: 4.2]
  --charge-cutoff-ratio FLOAT    Ratio of the charge_current used to derive
                                 the value of measured output current at which
                                 to stop charging.  [default: 0.1]
  --channel INT                  Which channel to output power from (for power
                                 supplies with multiple channels).  [default:
                                 0; 0<=x<=1]
  --num-samples INT              When measuring current, use the average of
                                 this many number of samples. Using a value
                                 over 1 is recommended, as anomalous blips may
                                 be measured. This also addresses low readings
                                 when output is first enabled.  [default: 3;
                                 x>=0]
  --max-successive-failures INT  After this number of continuous errors are
                                 encountered while attempting to read the
                                 output current, stop charging.  [default: 5;
                                 x>=0]
  --help                         Show this message and exit.
```

# Developing
This package uses poetry for dependency management. To get started hacking around the codebase:

1. Create a new virtualenv (or skip this step and let poetry do it for you)
2. `pip install poetry`
3. `poetry install`
4. Good luck!

# Contributing
If you have other utilities you'd like to add, or other PSUs you'd like to support, pull requests are welcomed! I may not be able to physically test all contributions, but I sure can review and merge :)
