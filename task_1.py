"""Задание 1. Синхронно vs асинхронно.

Синхронная версия ждёт каждый ответ по очереди; асинхронная перекрывает
сетевые ожидания разных запросов, поэтому обычно заканчивает раньше.
Скорость зависит от сети и сервера; ускорение не гарантировано.
Обе версии получают тела ответов, а не только заголовки или редиректы.

Замеры:
sync: 36.55 с.
async: 3.71 с.
"""
import asyncio
import time

import httpx
import requests

URLS = [f"https://picsum.photos/seed/{i}/800/600" for i in range(20)]


def timed(label, fn, *args):
    start = time.perf_counter()
    result = fn(*args)
    print(f"{label}: {time.perf_counter() - start:.2f}s")
    return result


def sync_main():
    results = []
    for url in URLS:
        with requests.get(url, timeout=30.0) as response:
            response.raise_for_status()
            results.append(response.status_code)
    return results


async def fetch(client: httpx.AsyncClient, url: str) -> int:
    response = await client.get(url)
    response.raise_for_status()
    return response.status_code


async def fast_main():
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        return await asyncio.gather(*(fetch(client, url) for url in URLS))


if __name__ == "__main__":
    timed("sync", sync_main)
    timed("async", lambda: asyncio.run(fast_main()))
