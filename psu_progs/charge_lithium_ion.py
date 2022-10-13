#!/usr/bin/env python
import math
import serial.tools.list_ports
import statistics
import time
from collections import deque
from datetime import datetime

import click

from .koradserial import ChannelMode, KoradSerial


def charge_lithium_ion_battery(
    port: str,
    battery_capacity: float,  # amps
    charge_current: float = None,  # amps
    charge_voltage: float = 4.2,
    charge_cutoff_ratio: float = 0.1,
    channel: int = 0,
    num_samples: int = 3,
    max_successive_failures: int = 5,
):
    """Charge a Li-ion battery using a Korad K300XP power supply

    :param port:
        Name of serial device the power supply can be communicated through,
        e.g. /dev/ttyACM0

    :param battery_capacity:
        Labeled capacity of battery, in amp hours.

    :param charge_current:
        Current to send to battery while in the constant-current charging phase, in amps.
        If not specified, this defaults to half the battery_capacity.

    :param charge_voltage:
        Voltage to use while in constant-voltage phase. For Li-ion cells, this
        value should be ≤4.2.

    :param charge_cutoff_ratio:
        Ratio of the charge_current used to derive the value of measured output
        current at which to stop charging.

    :param channel:
        Which channel to output power from (for power supplies with multiple channels).

    :param num_samples:
        When measuring current, use the average of this many number of samples.
        Using a value over 1 is recommended, as anomalous blips may be measured.
        This also addresses low readings when output is first enabled.

    :param max_successive_failures:
        After this number of continuous errors are encountered while attempting
        to read the output current, stop charging.

    """
    if charge_current is None:
        charge_current = battery_capacity / 2

    cutoff = charge_cutoff_ratio * charge_current

    print(f'Charging {battery_capacity} Ah battery until output current reaches {cutoff:.3f} amps')

    with KoradSerial(port) as psu:
        chan = psu.channels[channel]

        if channel == 0:
            get_channel_mode = lambda: psu.status.channel1
        elif channel == 1:
            get_channel_mode = lambda: psu.status.channel2
        else:
            raise ValueError(f'Unable to retrieve mode of channel {channel}')

        def _do_charge():
            chan.voltage = charge_voltage
            chan.current = charge_current

            psu.output.on()

            successive_failures = 0
            current_samples = deque(maxlen=num_samples)
            voltage_samples = deque(maxlen=num_samples)

            while True:
                try:
                    mode = get_channel_mode()
                    current = chan.output_current
                    voltage = chan.output_voltage

                    if current is not None:
                        current_samples.append(current)
                    if voltage is not None:
                        voltage_samples.append(voltage)

                    if current is None:
                        raise ValueError('Could not determine output current')
                    if voltage is None:
                        raise ValueError('Could not determine output voltage')

                    if len(current_samples) < current_samples.maxlen:
                        # continue reading until we've filled our samples buffer
                        continue

                    agg_current = statistics.mean(current_samples)
                    agg_voltage = statistics.mean(voltage_samples)

                    if mode == ChannelMode.constant_current:
                        charge_level = 0.5 * agg_voltage / charge_voltage
                    else:
                        # There appears to be an inflection point at 400mA, where the current decreases linearly
                        # until it reaches that point, and accounts for 1/4 the total constant-current charge time.
                        linear_ratio = 0.25
                        if agg_current > 0.4:
                            linear_level = (charge_current - agg_current) / (charge_current - 0.4)
                            cc_level = linear_ratio * linear_level
                        else:
                            n = (agg_current - cutoff) * 1000
                            b = (charge_current - cutoff) * 1000

                            if n >= 1:
                                cc_level = (1 - math.log(n, b)) * (1 - linear_ratio) + linear_ratio
                            else:
                                cc_level = 1.0

                        charge_level = 0.5 + 0.5 * cc_level

                    print(f'{datetime.now()} '
                          f'Current: {agg_current:01.3f}  (Inst: {current:01.3f})  '
                          f'Cutoff: {cutoff:1.3f}  '
                          f'Charge level: {charge_level:.1%}')
                    if agg_current < cutoff:
                        print('Reached cutoff. Ending output')
                        return

                except Exception as e:
                    successive_failures += 1
                    if successive_failures >= max_successive_failures:
                        psu.output.off()
                        raise RuntimeError(
                            f'Reached maximum number of failures ({max_successive_failures})'
                        ) from e
                else:
                    successive_failures = 0

                time.sleep(1)

        if psu.status.output:
            psu.output.off()

        try:
            _do_charge()
        finally:
            psu.output.off()


def get_serial_ports() -> tuple[str, ...]:
    port_infos = serial.tools.list_ports.comports()
    return tuple(port for port, desc, hwid in port_infos)


def get_default_serial_port():
    if ports := get_serial_ports():
        return ports[0]


@click.command()
@click.option('-p', '--port',
              default=get_default_serial_port(), required=True, show_default=True, metavar='DEVICE',
              help='Name of serial device the power supply can be communicated through, '
                   'e.g. /dev/ttyACM0')
@click.option('-c', '--capacity',
              type=click.FLOAT, required=True,
              help='Labeled capacity of battery, in amp hours.')
@click.option('--charge-current',
              type=click.FLOAT,
              help='Current to use while in the constant-current charging phase, in amps. '
                   'If not specified, this defaults to half the battery_capacity.')
@click.option('--charge-voltage',
              type=click.FLOAT, default=4.2, show_default=True,
              help='Voltage to use while in constant-voltage phase. '
                   'For Li-ion cells, this value should be ≤4.2.')
@click.option('--charge-cutoff-ratio',
              type=click.FLOAT, default=0.1, show_default=True,
              help='Ratio of the charge_current used to derive the value of measured output '
                   'current at which to stop charging.')
@click.option('--channel',
              type=click.IntRange(0, 1), default=0, show_default=True, metavar='INT',
              help='Which channel to output power from '
                   '(for power supplies with multiple channels).')
@click.option('--num-samples',
              type=click.IntRange(0), default=3, show_default=True, metavar='INT',
              help='When measuring current, use the average of this many number of samples. '
                   'Using a value over 1 is recommended, as anomalous blips may be measured. '
                   'This also addresses low readings when output is first enabled.')
@click.option('--max-successive-failures',
              type=click.IntRange(0), default=5, show_default=True, metavar='INT',
              help='After this number of continuous errors are encountered while attempting '
                   'to read the output current, stop charging.')
def charge(
    port: str,
    capacity: float,
    charge_current: float,
    charge_voltage: float,
    charge_cutoff_ratio: float,
    channel: int,
    num_samples: int,
    max_successive_failures: int,
):
    """Charge a Li-ion battery using a Korad K300XP power supply"""
    charge_lithium_ion_battery(
        port=port,
        battery_capacity=capacity,
        charge_current=charge_current,
        charge_voltage=charge_voltage,
        charge_cutoff_ratio=charge_cutoff_ratio,
        channel=channel,
        num_samples=num_samples,
        max_successive_failures=max_successive_failures,
    )


if __name__ == '__main__':
    charge()
