"""Задание 3*. CPU-bound и пульс event loop.

Тела скачиваются конкурентно один раз, затем одинаковые данные
хешируются сначала прямо в event loop, потом в ProcessPoolExecutor.
Прямые вызовы не содержат await, поэтому ticker не получает управление.
При await run_in_executor вычисления идут в отдельных процессах,
а event loop может выполнять ticker. Его отмена ожидается в finally.

Замеры на моей машине (заполнить после запуска):
download: 6.07 с.
heavy directly: 0.78 с.
heavy processes: 0.56 с.
cpu total: 7.82 с.

Процессы нужны здесь для демонстрации отзывчивости, а не гарантированного
ускорения: запуск процессов и передача данных тоже стоят времени.
body * 1000 требует много памяти; поэтому рабочих процессов только два.
Для hashlib возможны и потоки: при больших буферах он освобождает GIL.
Но прямой вызов hashlib всё равно занимает поток самого event loop.
"""
import asyncio
import hashlib
import time
from concurrent.futures import ProcessPoolExecutor
from contextlib import suppress

import httpx

URLS = [f"https://picsum.photos/seed/{i}/800/600" for i in range(20)]


def timed(label, fn, *args):
    start = time.perf_counter()
    result = fn(*args)
    print(f"{label}: {time.perf_counter() - start:.2f}s")
    return result


def heavy(body: bytes) -> str:
    return hashlib.sha256(body * 1000).hexdigest()


async def ticker():
    while True:
        print(".", end="", flush=True)
        await asyncio.sleep(0.1)


async def download(client: httpx.AsyncClient, url: str) -> bytes:
    response = await client.get(url)
    response.raise_for_status()
    return response.content


async def cpu_main():
    pulse = asyncio.create_task(ticker())
    try:
        await asyncio.sleep(0)
        print("\nСкачивание:", flush=True)
        start = time.perf_counter()
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            bodies = await asyncio.gather(*(download(client, url) for url in URLS))
        print(f"\ndownload: {time.perf_counter() - start:.2f}s", flush=True)

        print("Прямой heavy: точки остановятся", flush=True)
        await asyncio.sleep(0.2)
        start = time.perf_counter()
        direct_hashes = [heavy(body) for body in bodies]
        print(f"\nheavy directly: {time.perf_counter() - start:.2f}s", flush=True)

        print("Процессы: точки продолжаются", flush=True)
        await asyncio.sleep(0.2)
        loop = asyncio.get_running_loop()
        start = time.perf_counter()
        with ProcessPoolExecutor(max_workers=2) as pool:
            process_hashes = await asyncio.gather(
                *(loop.run_in_executor(pool, heavy, body) for body in bodies)
            )
        print(f"\nheavy processes: {time.perf_counter() - start:.2f}s", flush=True)
        assert direct_hashes == process_hashes
        print(f"Совпали все {len(process_hashes)} хешей")
        return process_hashes
    finally:
        pulse.cancel()
        with suppress(asyncio.CancelledError):
            await pulse
        print()


if __name__ == "__main__":
    timed("cpu total", lambda: asyncio.run(cpu_main()))
