#!/usr/bin/env python3
"""Bounded, read-only ADB key probe. Raw identifiers never leave process memory."""
import argparse
import collections
import datetime
import json
from pathlib import Path
import queue
import re
import subprocess
import threading
import time

KEYS = frozenset({
    'KEY_VOLUMEUP', 'KEY_VOLUMEDOWN', 'KEY_ZOOMIN', 'KEY_ZOOMOUT',
    'KEY_VIDEO_NEXT', 'KEY_PLAYPAUSE', 'KEY_CAMERA', 'KEY_UNKNOWN', 'KEY_VCR2',
})
EVENT = re.compile(
    r'^\[\s*([0-9.]+)\]\s+(/dev/input/event\d+):\s+EV_KEY\s+(KEY_[A-Z0-9_]+)\s+(DOWN|UP|REPEAT)\s*$'
)
FAILURE = re.compile(r'permission denied|permission denial|could not open|could not get|not found|device offline|no devices|unauthorized|error:', re.I)


class Filter:
    def __init__(self):
        self.aliases = {}
        self.origin = None

    def parse(self, line):
        match = EVENT.fullmatch(line.strip())
        if not match or match[3] not in KEYS:
            return None
        stamp, node, code, value = match.groups()
        stamp = float(stamp)
        if self.origin is None:
            self.origin = stamp
        alias = self.aliases.setdefault(node, 'device_' + str(len(self.aliases) + 1))
        return {'relative_seconds': round(stamp - self.origin, 6),
                'device': alias, 'code': code, 'value': value}


def command(argv):
    return subprocess.run(argv, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=15)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', default='adb', help='Path to official adb executable')
    parser.add_argument('--seconds', type=int, default=60, help='10..300 seconds')
    parser.add_argument('--output', type=Path, help='New JSON file; never overwrite')
    args = parser.parse_args()
    if not 10 <= args.seconds <= 300:
        parser.error('--seconds must be between 10 and 300')
    try:
        listing = command([args.adb, 'devices'])
        devices = []
        for line in listing.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] in ('device', 'offline', 'unauthorized'):
                devices.append(parts[:2])
        if listing.returncode or len(devices) != 1 or devices[0][1] != 'device':
            raise RuntimeError('Connect exactly one authorized, online phone; approve USB debugging on the phone.')
        prefix = [args.adb, '-s', devices[0][0]]
        caps = command(prefix + ['shell', 'getevent', '-lp'])
        if caps.returncode or FAILURE.search(caps.stdout + caps.stderr):
            raise RuntimeError('Input enumeration failed or was denied. No root or permission changes attempted.')
        expected = set(re.findall(r'add device \d+:\s*(/dev/input/event\d+)', caps.stdout))
        if not expected:
            raise RuntimeError('No input nodes enumerated; cannot start a valid observation.')
    except (OSError, subprocess.TimeoutExpired) as exc:
        print('SETUP FAILED: check adb installation, USB connection and authorization (' + type(exc).__name__ + ').')
        return 1
    except RuntimeError as exc:
        print('SETUP FAILED: ' + str(exc))
        return 1

    output = args.output or Path('captures') / ('input-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Reserve a new file before the capture. Never overwrite an earlier observation.
    try:
        destination = output.open('x', encoding='utf-8')
    except FileExistsError:
        print('OUTPUT EXISTS: choose a new --output path.')
        return 1
    events, opened = [], set()
    filt = Filter()
    inbox = queue.Queue(maxsize=2048)
    done = threading.Event()
    overflow = threading.Event()
    process = None
    reason = 'duration_limit'
    denied = False
    ready = False
    started = time.monotonic()
    print('Preparing read-only input capture...', flush=True)
    try:
        process = subprocess.Popen(prefix + ['shell', 'getevent', '-lt'],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding='utf-8', errors='replace', bufsize=1)

        def reader():
            try:
                for line in process.stdout:
                    if done.is_set():
                        break
                    try:
                        inbox.put_nowait(line)
                    except queue.Full:
                        overflow.set()
            finally:
                done.set()

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        while time.monotonic() - started < args.seconds:
            try:
                line = inbox.get(timeout=0.1)
            except queue.Empty:
                if done.is_set():
                    reason = 'stream_ended'
                    break
                continue
            if FAILURE.search(line):
                denied = True
                reason = 'input_access_error'
                break
            match = re.search(r'add device \d+:\s*(/dev/input/event\d+)', line)
            if match:
                opened.add(match[1])
            if not ready and expected <= opened:
                ready = True
                print('READY: operate one OM8 control; note the actual camera response. Ctrl+C to stop.', flush=True)
            event = filt.parse(line)
            if event is not None:
                events.append(event)
                print(json.dumps(event), flush=True)
            if len(events) >= 10000:
                reason = 'event_limit'
                break
    except KeyboardInterrupt:
        reason = 'user_stop'
    except (OSError, subprocess.SubprocessError) as exc:
        reason = 'capture_error_' + type(exc).__name__
    finally:
        done.set()
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
            process.stdout.close()
        counts = collections.Counter((x['code'], x['value']) for x in events)
        result = {
            'schema_version': 1, 'finish_reason': reason,
            'all_enumerated_nodes_opened': ready, 'input_access_error': denied,
            'stream_queue_overflow': overflow.is_set(),
            'elapsed_seconds': round(time.monotonic() - started, 2),
            'event_counts': [{'code': k[0], 'value': k[1], 'count': v} for k, v in sorted(counts.items())],
            'events': events,
            'limitations': ['Aliases are per run, not proof of OM8 identity.',
                           'An empty capture or access error is not proof of absent HID.',
                           'Camera response must be observed separately.',
                           'Only explicitly allowlisted Linux control keys are retained.'],
        }
        with destination:
            json.dump(result, destination, ensure_ascii=False, indent=2)
            destination.write('\n')
    print('Saved filtered result. Review before sharing; no raw capture was saved.')
    return 0 if ready and not denied and not overflow.is_set() and reason in ('duration_limit', 'user_stop') else 1


if __name__ == '__main__':
    raise SystemExit(main())
