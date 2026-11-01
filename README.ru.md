# test-writer — навык для ИИ-агентов: тесты, которые ловят баги

[![CI](https://github.com/sofetizm/test-writer/actions/workflows/ci.yml/badge.svg)](https://github.com/sofetizm/test-writer/actions/workflows/ci.yml)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sofetizm/test-writer/blob/main/notebooks/benchmark_colab.ipynb)

**[English version](README.md)**

ИИ-ассистенты пишут тесты, которые проходят. Это не то же самое, что тесты, которые
**падают, когда код неправильный**. `test-writer` — навык (Agent Skill) для Claude Code,
Codex CLI, GitHub Copilot, Cursor, Gemini CLI и других агентов. С ним агент проверяет
свои тесты через **mutation testing**: в код вносятся маленькие баги, и агент улучшает
тесты, пока они их не поймают.

В репозитории также есть **бенчмарк**, который измеряет, помогает ли навык: одна и та же
модель пишет тесты к 10 модулям с навыком и без, а тесты оцениваются по доле пойманных
внесённых багов.

## Проблема на примере

Типичный тест от ИИ для функции пагинации:

```python
def test_paginate():
    result = paginate(45, 2)
    assert result is not None
    assert result["page"] == 2
    assert result["has_next"]
```

Он проходит. Скрипт навыка вносит в `paginate` 25 багов и запускает тест:

```text
Mutation score: 40.0%  (10/25 mutants killed, 15 survived, 0 timeouts) in 9.9s

Surviving mutants (behaviour that no test checks):
  line 12:8    `<` -> `<=`                        | if total < 0:
  line 19:22   `//` -> `/`                        | pages = max(1, -(-total // per_page))
  line 25:20   `-` -> `+`                         | "offset": (page - 1) * per_page,
  line 26:21   `>` -> `>=`                        | "has_prev": page > 1,
  ...
```

60% таких багов прошли бы незамеченными. С навыком агент читает этот список и добавляет
недостающие проверки границ и полей, пока выжившие мутанты не исчезнут или не окажутся
эквивалентными (не меняющими поведение кода).

## Установка

```bash
npx skills add sofetizm/test-writer
```

Или скопируй папку `skills/test-writer/` в папку навыков своего агента:

| Агент | В проекте | Для всех проектов |
|---|---|---|
| Claude Code | `.claude/skills/test-writer/` | `~/.claude/skills/test-writer/` |
| Codex CLI | `.agents/skills/test-writer/` | `~/.agents/skills/test-writer/` |
| GitHub Copilot | `.github/skills/test-writer/` | — |
| Cursor | `.cursor/skills/test-writer/` | — |
| Gemini CLI | `.gemini/skills/test-writer/` | — |

После этого достаточно попросить: *«напиши тесты для `src/billing/discounts.py`»*.

## Что навык заставляет делать агента

1. **Составить план**: поведение, ветки, границы (`b-1`, `b`, `b+1` для каждого сравнения),
   ошибки, инварианты, изменения состояния.
2. **Писать точные тесты**: точные ожидаемые значения, сравнение структур целиком,
   `pytest.raises(..., match=...)`, таблицы границ через `parametrize`, property-based
   тесты, подменённые часы вместо `sleep`.
3. **Запустить на исходном коде.** Упавший тест — это либо неверное ожидание (исправить
   тест), либо настоящий баг (оставить как `xfail(strict=True)` и сообщить). Код под
   тестом не меняется ради прохождения тестов.
4. **Запустить mutation testing** и закрыть каждого выжившего мутанта или объяснить, почему
   он эквивалентный. Остановиться на ≥ 90% или после 4 итераций.
5. **Отчитаться**: что покрыто, итоговый score, найденные баги.

## Бенчмарк

- 10 модулей с подвохами: длительности, интервалы, округление денег, slug с транслитерацией,
  LRU-кеш, политика паролей, rate limiter, пагинация, semver, задержки повторов.
- Три условия с одной и той же моделью и одинаковыми инструментами:
  `baseline` (без навыка), `skill` (навык целиком), `skill-text` (абляция: текст навыка
  без скрипта mutation testing).
- **Метрика:** mutation score итогового файла тестов. Тесты, падающие на правильном коде,
  исключаются до подсчёта.
- **Потолок:** эталонные тесты дают 100% на 8 задачах; на двух оставшиеся мутанты
  эквивалентные, их невозможно поймать ([`bench/ceiling.json`](bench/ceiling.json)).
- **Статистика:** главный результат — парная разница skill − baseline на одних и тех же
  задачах с 95% доверительным интервалом (бутстреп).

### Результаты

> Запусти [ноутбук](notebooks/benchmark_colab.ipynb) и вставь сюда таблицу из `results/RESULTS.md`.

| Модель | baseline | skill | Δ (парная) | 95% ДИ |
|---|---|---|---|---|
| gpt-oss-120b | — | — | — | — |

### Как воспроизвести

```bash
pip install -r requirements.txt && pip install -e .
export OPENAI_API_KEY=... OPENAI_BASE_URL=https://api.groq.com/openai/v1
python -m twbench.run --model openai/gpt-oss-120b --name gpt-oss-120b \
    --conditions baseline,skill,skill-text --reasoning-effort low --rpm 4
python -m twbench.report --results results
```

Прогон можно прерывать: готовые эпизоды пропускаются при повторном запуске.

## Ограничения

- Только Python и pytest.
- 10 задач — небольшой бенчмарк: разницу в несколько пунктов смотри вместе с доверительным
  интервалом.
- Агент в бенчмарке — простой цикл, а не настоящий Claude Code или Codex CLI. Он проверяет
  содержание навыка в одинаковых условиях; поведение внутри реальных агентов может отличаться.

## Лицензия

MIT
