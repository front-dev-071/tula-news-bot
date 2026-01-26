import sys
import os

print(f"Python: {sys.version}")
print(f"Интерпретатор: {sys.executable}")
print(f"Виртуальное окружение: {'venv' in sys.executable}")

# Проверка пакетов
try:
    import requests
    print("✓ requests установлен")
except ImportError:
    print("✗ requests НЕ установлен")