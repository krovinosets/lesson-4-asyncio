"""Задание 2. Таймаут, ретраи и независимость запросов.

У каждого URL максимум три попытки: после первых двух неудач паузы
1 и 2 секунды; после третьей неудачи паузы нет. Для пауз используется
asyncio.sleep, чтобы не блокировать event loop.
HTTPX ограничивает сетевые операции, asyncio.timeout дополнительно
ограничивает всю попытку (вместе с переходами по редиректам) 5 секундами.
gather(return_exceptions=True) сохраняет результаты остальных URL.

Замер:
robust, 22 URL: 18.09 с.
Успешных: 20. Ошибок: 2.
"""
import asyncio
import time

import httpx

URLS = [f"https://picsum.photos/seed/{i}/800/600" for i in range(20)]
BAD_URLS = ["https://no-such-site.invalid", "https://httpbin.org/delay/10"]
ATTEMPTS = 3
REQUEST_TIMEOUT = 5.0


def timed(label, fn, *args):
    start = time.perf_counter()
    result = fn(*args)
    print(f"{label}: {time.perf_counter() - start:.2f}s")
    return result


async def robust_fetch(client: httpx.AsyncClient, url: str) -> int:
    for attempt in range(ATTEMPTS):
        try:
            response = await asyncio.wait_for(
                client.get(url, timeout=REQUEST_TIMEOUT),
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.status_code

        except (httpx.HTTPError, asyncio.TimeoutError):
            if attempt == ATTEMPTS - 1:
                raise

            await asyncio.sleep(2 ** attempt)

    raise AssertionError("ATTEMPTS должен быть положительным")


async def robust_main(urls: list[str] | None = None):
    urls = list(URLS + BAD_URLS if urls is None else urls)
    async with httpx.AsyncClient(follow_redirects=True) as client:
        outcomes = await asyncio.gather(
            *(robust_fetch(client, url) for url in urls),
            return_exceptions=True,
        )

    results: list[tuple[str, int]] = []
    errors: list[tuple[str, str]] = []
    for url, outcome in zip(urls, outcomes):
        if isinstance(outcome, asyncio.CancelledError):
            raise outcome
        if isinstance(outcome, Exception):
            errors.append((url, f"{type(outcome).__name__}: {outcome}"))
        else:
            results.append((url, outcome))
    return results, errors


if __name__ == "__main__":
    results, errors = timed("robust", lambda: asyncio.run(robust_main()))
    print(f"Успешных: {len(results)}; ошибок: {len(errors)}")
    for url, status in results:
        print(f"OK {status}: {url}")
    for url, error in errors:
        print(f"ERROR {url}: {error}")
