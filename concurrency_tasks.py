"""
Конкурентність у Python: 12 практичних завдань

Файл можна запускати напряму:

    python concurrency_tasks.py

Важливо:
- Task 1 демонструє race condition. У CPython через GIL помилка іноді може маскуватися,
  тому read-modify-write зроблено явно, щоб проблема стабільно проявлялась.
- Task 7 є CPU-bound і може виконуватися помітно довше.
- Для ProcessPoolExecutor обов'язково використовується if __name__ == "__main__".
"""

from __future__ import annotations

import os
import time
import threading
from functools import reduce
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import Any, Callable, Iterable, TypeVar


T = TypeVar("T")
R = TypeVar("R")


# ============================================================
# Helpers
# ============================================================

def print_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def measure_time(label: str, func: Callable[[], T]) -> tuple[T, float]:
    start = time.perf_counter()
    result = func()
    elapsed = time.perf_counter() - start
    print(f"{label}: {elapsed:.4f} секунд")
    return result, elapsed


def square(x: int) -> int:
    return x * x


def is_greater_than_100(x: int) -> bool:
    return x > 100


def increment_value(x: int) -> int:
    return x + 1


# ============================================================
# Завдання 1. Race condition
# ============================================================

counter = 0


def increment_racy(iterations: int = 100_000) -> None:
    """
    Небезпечна версія інкременту.

    Операція counter += 1 логічно складається з трьох кроків:
    1. прочитати counter
    2. додати 1
    3. записати counter назад

    Якщо два потоки одночасно працюють із цими кроками, один запис може
    перезаписати інший. Це і є race condition.

    Для стабільної демонстрації ми робимо ці кроки явно.
    """
    global counter

    for i in range(iterations):
        current = counter

        # Примусово даємо іншому потоку шанс втрутитися між читанням і записом.
        # Без цього CPython через GIL іноді показує "правильний" результат,
        # хоча сама ідея спільного mutable state без синхронізації лишається небезпечною.
        if i % 100 == 0:
            time.sleep(0)

        counter = current + 1


def task_1_race_condition(repeats: int = 5, iterations: int = 100_000) -> None:
    print_header("Завдання 1. Race condition")

    expected = 2 * iterations

    for run in range(1, repeats + 1):
        global counter
        counter = 0

        thread_1 = threading.Thread(target=increment_racy, args=(iterations,))
        thread_2 = threading.Thread(target=increment_racy, args=(iterations,))

        thread_1.start()
        thread_2.start()

        thread_1.join()
        thread_2.join()

        print(f"Спроба {run}: counter = {counter}, очікувалось = {expected}")

    print(
        "\nПояснення:\n"
        "- Результат неправильний, бо два потоки одночасно читають і змінюють одну "
        "глобальну змінну counter.\n"
        "- Race condition — це ситуація, коли результат програми залежить від того, "
        "у якому порядку потоки отримали доступ до спільного ресурсу.\n"
    )


# ============================================================
# Завдання 2. Усунення проблеми через Lock
# ============================================================

counter_with_lock = 0
counter_lock = threading.Lock()


def increment_with_lock(iterations: int = 100_000) -> None:
    global counter_with_lock

    for _ in range(iterations):
        with counter_lock:
            counter_with_lock += 1


def task_2_lock_solution(iterations: int = 100_000) -> None:
    print_header("Завдання 2. Усунення проблеми через Lock")

    global counter_with_lock
    counter_with_lock = 0

    expected = 2 * iterations

    thread_1 = threading.Thread(target=increment_with_lock, args=(iterations,))
    thread_2 = threading.Thread(target=increment_with_lock, args=(iterations,))

    thread_1.start()
    thread_2.start()

    thread_1.join()
    thread_2.join()

    print(f"counter_with_lock = {counter_with_lock}, очікувалось = {expected}")

    print(
        "\nПояснення:\n"
        "- Lock дозволяє лише одному потоку одночасно виконувати критичну секцію.\n"
        "- Критична секція тут — це counter_with_lock += 1.\n"
        "- Тому потоки більше не перезаписують результат один одного.\n\n"
        "Мінуси Lock:\n"
        "- зменшує паралелізм, бо частина коду виконується по черзі;\n"
        "- може створити bottleneck;\n"
        "- при неправильному використанні можливі deadlock-и;\n"
        "- код стає складнішим для аналізу.\n"
    )


# ============================================================
# Завдання 3. Без mutable state
# ============================================================

def increment(x: int) -> int:
    return x + 1


def task_3_without_mutable_state() -> None:
    print_header("Завдання 3. Без mutable state")

    values = list(range(10))
    result = list(map(increment, values))

    print(f"Початковий список: {values}")
    print(f"Після increment:   {result}")

    print(
        "\nПояснення:\n"
        "- Немає глобальної змінної counter.\n"
        "- Функція increment не змінює зовнішній стан, а повертає нове значення.\n"
        "- Такий підхід легше паралелити й тестувати.\n"
    )


# ============================================================
# Завдання 4. Паралельна обробка без стану
# ============================================================

def task_4_parallel_square() -> None:
    print_header("Завдання 4. Паралельна обробка без стану")

    data = [1, 2, 3, 4, 5]

    with ThreadPoolExecutor() as executor:
        result = list(executor.map(square, data))

    print(f"data:   {data}")
    print(f"square: {result}")


# ============================================================
# Завдання 5. Паралельний map
# ============================================================

def parallel_map(
    func: Callable[[T], R],
    data: Iterable[T],
    max_workers: int | None = None,
) -> list[R]:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(func, data))


def task_5_parallel_map() -> None:
    print_header("Завдання 5. Паралельний map")

    data = [1, 2, 3, 4, 5]
    result = parallel_map(square, data)

    print(f"data:                {data}")
    print(f"parallel_map square: {result}")


# ============================================================
# Завдання 6. Порівняння часу
# ============================================================

def task_6_compare_time() -> None:
    print_header("Завдання 6. Порівняння часу: map vs parallel_map")

    data = range(1_000_000)

    ordinary_result, ordinary_time = measure_time(
        "Звичайний map",
        lambda: list(map(square, data)),
    )

    # range треба створити повторно, бо попередній iterable уже міг бути використаний.
    data = range(1_000_000)

    parallel_result, parallel_time = measure_time(
        "parallel_map через ThreadPoolExecutor",
        lambda: parallel_map(square, data, max_workers=os.cpu_count() or 4),
    )

    print(f"Результати однакові: {ordinary_result == parallel_result}")

    if parallel_time < ordinary_time:
        print("parallel_map швидший у цьому запуску.")
    else:
        print(
            "Звичайний map швидший у цьому запуску. "
            "Для простих CPU-операцій ThreadPool часто програє через overhead і GIL."
        )


# ============================================================
# Завдання 7. CPU-bound задача
# ============================================================

def heavy_task(x: int) -> int:
    total = 0
    for i in range(10_000_000):
        total += i * x
    return total


def task_7_cpu_bound() -> None:
    print_header("Завдання 7. CPU-bound задача")

    data = [1, 2, 3, 4]

    sequential_result, sequential_time = measure_time(
        "Послідовно",
        lambda: [heavy_task(x) for x in data],
    )

    thread_result, thread_time = measure_time(
        "ThreadPoolExecutor",
        lambda: parallel_map(heavy_task, data, max_workers=len(data)),
    )

    process_result, process_time = measure_time(
        "ProcessPoolExecutor",
        lambda: process_map(heavy_task, data, max_workers=len(data)),
    )

    print(f"Результати однакові: {sequential_result == thread_result == process_result}")

    times = {
        "послідовно": sequential_time,
        "ThreadPool": thread_time,
        "ProcessPool": process_time,
    }
    fastest = min(times, key=times.get)

    print(f"Найшвидший варіант у цьому запуску: {fastest}")

    print(
        "\nПояснення:\n"
        "- heavy_task є CPU-bound: основне навантаження йде на процесор.\n"
        "- ThreadPool у CPython зазвичай не прискорює CPU-bound задачі через GIL.\n"
        "- ProcessPool може бути швидшим, бо використовує окремі процеси й окремі "
        "інтерпретатори Python.\n"
        "- ProcessPool має overhead на створення процесів і передачу даних, тому для "
        "малих задач він може бути повільнішим.\n"
    )


def process_map(
    func: Callable[[T], R],
    data: Iterable[T],
    max_workers: int | None = None,
) -> list[R]:
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(func, data))


# ============================================================
# Завдання 8. Паралельний pipeline
# ============================================================

def parallel_filter(
    predicate: Callable[[T], bool],
    data: Iterable[T],
    max_workers: int | None = None,
) -> list[T]:
    items = list(data)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        flags = list(executor.map(predicate, items))

    return [item for item, keep in zip(items, flags) if keep]


def task_8_parallel_pipeline() -> None:
    print_header("Завдання 8. Паралельний pipeline")

    data = range(100)

    mapped = parallel_map(square, data)
    filtered = parallel_filter(is_greater_than_100, mapped)
    result = reduce(lambda acc, x: acc + x, filtered, 0)

    print("Pipeline: map x*x -> filter x > 100 -> reduce sum")
    print(f"Результат: {result}")


# ============================================================
# Завдання 9. Functional pipeline API
# ============================================================

def pipeline(data: Any, steps: list[Callable[[Any], Any]]) -> Any:
    result = data

    for step in steps:
        result = step(result)

    return result


def step_parallel_square(data: Iterable[int]) -> list[int]:
    return parallel_map(square, data)


def step_filter_greater_than_100(data: Iterable[int]) -> list[int]:
    return parallel_filter(is_greater_than_100, data)


def step_sum(data: Iterable[int]) -> int:
    return sum(data)


def task_9_functional_pipeline_api() -> None:
    print_header("Завдання 9. Functional pipeline API")

    data = range(100)
    steps = [
        step_parallel_square,
        step_filter_greater_than_100,
        step_sum,
    ]

    result = pipeline(data, steps)

    print("pipeline(data, steps)")
    print(f"Результат: {result}")


# ============================================================
# Завдання 10. Safe execution
# ============================================================

def risky(x: int) -> float:
    if x == 0:
        raise ValueError("x не може дорівнювати 0")
    return 10 / x


def safe_call(func: Callable[[T], R], item: T) -> dict[str, Any]:
    try:
        return {
            "ok": True,
            "input": item,
            "result": func(item),
            "error": None,
        }
    except Exception as error:
        return {
            "ok": False,
            "input": item,
            "result": None,
            "error": f"{type(error).__name__}: {error}",
        }


def safe_parallel_map(
    func: Callable[[T], R],
    data: Iterable[T],
    max_workers: int | None = None,
) -> list[dict[str, Any]]:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(safe_call, func, item) for item in data]
        return [future.result() for future in as_completed(futures)]


def task_10_safe_execution() -> None:
    print_header("Завдання 10. Safe execution")

    data = [5, 2, 1, 0, -1, -2]
    result = safe_parallel_map(risky, data)

    # as_completed повертає результати в порядку завершення.
    result_sorted = sorted(result, key=lambda item: item["input"])

    for item in result_sorted:
        if item["ok"]:
            print(f"input={item['input']}: result={item['result']}")
        else:
            print(f"input={item['input']}: error={item['error']}")

    print("\nПрограма не падає, бо виняток перехоплюється всередині safe_call.")


# ============================================================
# Завдання 11. Обробка транзакцій
# ============================================================

def is_valid_transaction(x: int) -> bool:
    # Приклад фільтра: беремо тільки парні транзакції.
    return x % 2 == 0


def process_transaction(x: int) -> int:
    # Приклад обробки: умовно подвоюємо суму/значення транзакції.
    return x * 2


def task_11_transactions_pipeline() -> None:
    print_header("Завдання 11. Обробка транзакцій")

    transactions = range(1_000_000)

    valid_transactions = parallel_filter(
        is_valid_transaction,
        transactions,
        max_workers=os.cpu_count() or 4,
    )

    processed_transactions = parallel_map(
        process_transaction,
        valid_transactions,
        max_workers=os.cpu_count() or 4,
    )

    total = sum(processed_transactions)

    print("Pipeline: filter -> map -> sum")
    print(f"Кількість валідних транзакцій: {len(valid_transactions)}")
    print(f"Сума після обробки: {total}")


# ============================================================
# Завдання 12. API simulation
# ============================================================

def fetch_data(x: int) -> int:
    time.sleep(1)
    return x


def task_12_api_simulation() -> None:
    print_header("Завдання 12. API simulation")

    data = list(range(10))

    sequential_result, sequential_time = measure_time(
        "Послідовно",
        lambda: [fetch_data(x) for x in data],
    )

    parallel_result, parallel_time = measure_time(
        "Паралельно через ThreadPoolExecutor",
        lambda: parallel_map(fetch_data, data, max_workers=10),
    )

    print(f"Послідовний результат: {sequential_result}")
    print(f"Паралельний результат: {parallel_result}")

    print(
        "\nПояснення:\n"
        "- fetch_data імітує I/O-bound задачу, бо основний час іде на очікування sleep.\n"
        "- Для I/O-bound задач ThreadPool добре підходить: поки один потік очікує, "
        "інші можуть працювати.\n"
    )


# ============================================================
# Main
# ============================================================

def main() -> None:
    task_1_race_condition()
    task_2_lock_solution()
    task_3_without_mutable_state()
    task_4_parallel_square()
    task_5_parallel_map()
    task_6_compare_time()
    task_7_cpu_bound()
    task_8_parallel_pipeline()
    task_9_functional_pipeline_api()
    task_10_safe_execution()
    task_11_transactions_pipeline()
    task_12_api_simulation()


if __name__ == "__main__":
    main()
