# luraph-v15.2-deobf

Основа для деобфускатора Luraph v15.2: код из `luraph-v15-deobf` плюс первые правки под v15.2.
Статус и найденные отличия: [V15_2.md](V15_2.md). Общая документация проекта: [CLAUDE.md](CLAUDE.md), [LURAPH.md](LURAPH.md).

## Запуск в GitHub Codespaces

```bash
./setup.sh                                   # собирает deobf/bin/luau и deobf/bin/luau-ast (несколько минут)
python3 deobf/deob.py sample.luau --detect   # определить обфускатор
python3 deobf/deob.py sample.luau --no-devirt --debug   # трасса поведения + промежуточные файлы в output/
```

`--debug` кладёт рядом `sample.chunk_<ключ>.luau` (VM из `loadstring`), `sample.protos.json` и `sample.deobf.luau`.
Результат пока не читаемый исходник: см. «Что не работает» в V15_2.md.

## Что нужно для проверки

Пара «исходник и обфусцированный результат» (например `sample_src.luau` и `sample_fly_obf.luau`), чтобы сверять вывод построчно.
