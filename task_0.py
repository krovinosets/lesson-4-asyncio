"""Задание 0. Почему async не дал ускорения?

В slow_main каждый await завершается до начала следующего запроса:
запросы последовательны. gather в fast_main запускает их конкурентно,
перекрывая ожидание сети. Во всех AsyncClient включены редиректы.

Замеры:
slow: 9.85 с.
fast: 0.87 с.
"""
import asyncio
import time

import httpx

URLS = [f"https://picsum.photos/seed/{i}/800/600" for i in range(20)]


def timed(label, fn, *args):
    start = time.perf_counter()
    result = fn(*args)
    print(f"{label}: {time.perf_counter() - start:.2f}s")
    return result


async def fetch(client: httpx.AsyncClient, url: str) -> int:
    resp = await client.get(url)
    resp.raise_for_status()
    return resp.status_code


async def slow_main():
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        return [await fetch(client, url) for url in URLS]


async def fast_main():
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        return await asyncio.gather(*(fetch(client, url) for url in URLS))


if __name__ == "__main__":
    timed("slow", lambda: asyncio.run(slow_main()))
    timed("fast", lambda: asyncio.run(fast_main()))
