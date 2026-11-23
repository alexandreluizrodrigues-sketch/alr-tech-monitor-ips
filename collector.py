"""Coleta continuamente o estado dos IPs cadastrados via ICMP ping."""
import concurrent.futures
from datetime import datetime, timedelta
import os
import platform
import re
import subprocess
import time
from storage import connect, setup

INTERVAL_SECONDS = max(2, int(os.environ.get('MONITOR_INTERVAL_SECONDS', '5')))
RETENTION_DAYS = max(1, int(os.environ.get('MONITOR_RETENTION_DAYS', '90')))
RTT_PATTERN = re.compile(r'(?:tempo|time)\s*[=<]\s*(\d+(?:[,.]\d+)?)\s*ms', re.IGNORECASE)


def probe(target):
    target_id, address = target
    if platform.system() == 'Windows':
        command = ['ping', '-n', '1', '-w', '1000', address]
    else:
        command = ['ping', '-n', '-c', '1', '-W', '1', address]
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                errors='replace', timeout=3, shell=False)
        online = result.returncode == 0
        found = RTT_PATTERN.search(result.stdout)
        latency = float(found.group(1).replace(',', '.')) if found and online else None
    except (OSError, subprocess.TimeoutExpired):
        online, latency = False, None
    return (target_id, datetime.now().astimezone().isoformat(timespec='seconds'), int(online), latency)


def main():
    setup()
    print(f'Monitor de IPs iniciado | intervalo {INTERVAL_SECONDS}s | retenção {RETENTION_DAYS} dias', flush=True)
    last_cleanup = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as executor:
        while True:
            started = time.monotonic()
            with connect() as db:
                targets = db.execute('SELECT id, address FROM targets WHERE enabled = 1').fetchall()
            if targets:
                results = list(executor.map(probe, targets))
                with connect() as db:
                    db.executemany('INSERT INTO checks (target_id, checked_at, online, latency_ms) VALUES (?, ?, ?, ?)', results)
                print(f'{datetime.now():%d/%m/%Y %H:%M:%S} | {len(results)} IP(s) verificado(s)', flush=True)
            if time.monotonic() - last_cleanup >= 86400 or not last_cleanup:
                cutoff = (datetime.now().astimezone() - timedelta(days=RETENTION_DAYS)).isoformat(timespec='seconds')
                with connect() as db:
                    db.execute('DELETE FROM checks WHERE checked_at < ?', (cutoff,))
                last_cleanup = time.monotonic()
            time.sleep(max(0.5, INTERVAL_SECONDS - (time.monotonic() - started)))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Coleta finalizada.')
