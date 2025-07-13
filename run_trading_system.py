#!/usr/bin/env python3
import subprocess
import sys
import os
import signal
import time
import threading

# Optional: Check TWS connectivity before starting
try:
    from ib_insync import IB
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False

def check_tws_connection(host='127.0.0.1', port=7497, client_id=999):
    if not IB_AVAILABLE:
        print("[WARN] ib_insync not installed, skipping TWS connectivity check.")
        return True
    ib = IB()
    try:
        ib.connect(host, port, clientId=client_id, timeout=5)
        if ib.isConnected():
            print("[OK] Connected to TWS at {}:{}".format(host, port))
            ib.disconnect()
            return True
        else:
            print("[ERROR] Could not connect to TWS at {}:{}".format(host, port))
            return False
    except Exception as e:
        print(f"[ERROR] Exception connecting to TWS: {e}")
        return False

def stream_subprocess_output(proc, name):
    for line in iter(proc.stdout.readline, ''):
        if not line:
            break
        print(f"[{name}] {line.rstrip()}")
    proc.stdout.close()

def start_process(cmd, name, env=None):
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True,
        shell=False,
        env=env
    )
    t = threading.Thread(target=stream_subprocess_output, args=(proc, name), daemon=True)
    t.start()
    return proc

def main():
    # Paths
    cpp_engine = [os.path.join('cpp', 'build', 'Release', 'TWSConnect.exe')]

    # For Python, run as a module with correct PYTHONPATH
    python_path = os.path.abspath('python')
    env = os.environ.copy()
    env['PYTHONPATH'] = python_path
    python_engine = [sys.executable, '-m', 'python.main_data_engine']

    # Check TWS connectivity
    if not check_tws_connection():
        print("[FATAL] TWS not reachable. Start TWS and enable API access.")
        sys.exit(1)

    print("[INFO] Starting Python data engine...")
    py_proc = start_process(python_engine, 'PYTHON', env=env)
    time.sleep(2)
    print("[INFO] Starting C++ order engine...")
    cpp_proc = start_process(cpp_engine, 'CPP')

    procs = [py_proc, cpp_proc]
    running = True

    def shutdown(signum, frame):
        nonlocal running
        print(f"\n[INFO] Received signal {signum}, shutting down...")
        running = False
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()
        # Wait for processes to exit
        for proc in procs:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("[INFO] All processes stopped. Exiting.")
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while running:
            for proc, name in zip(procs, ['PYTHON', 'CPP']):
                ret = proc.poll()
                if ret is not None:
                    print(f"[ERROR] {name} process exited with code {ret}.")
                    shutdown(None, None)
            time.sleep(1)
    except Exception as e:
        print(f"[FATAL] Exception in orchestrator: {e}")
        shutdown(None, None)

if __name__ == "__main__":
    main() 