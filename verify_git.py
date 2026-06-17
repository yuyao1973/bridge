#!/usr/bin/env python3
import subprocess
import sys

try:
    result = subprocess.run(['git', 'remote', '-v'], capture_output=True, text=True, cwd='C:\\source_code\\桥牌叫牌训练')
    print(f"Remote: {result.stdout if result.stdout else result.stderr}")
    
    result = subprocess.run(['git', 'log', '--oneline', '-1'], capture_output=True, text=True, cwd='C:\\source_code\\桥牌叫牌训练')
    print(f"Commit: {result.stdout if result.stdout else result.stderr}")
    
    result = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True, cwd='C:\\source_code\\桥牌叫牌训练')
    print(f"Status: {result.stdout if result.stdout else '(clean)'}")
    
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
