#!/usr/bin/env python3
"""
01b — Monta os ZIPs de 2018–2025 a partir de volumes < 100 MB vindos do Drive.

Os volumes chegam em google_drive/ com nomes do tipo:
  infracoes_2018.zip.001, .002, ...   (7-Zip "Dividir arquivo")
  infracoes_2018.z01, .z02, ..., .zip  (WinZip/arrasto de volumes)
  infracoes_2018_part_1, _part_2, ...

Este script:
  1. Agrupa os volumes por nome-base.
  2. Concatena em ordem numérica → arquivo .zip único (remontagem byte a byte).
  3. Valida o ZIP (zipfile.testzip).
  4. Extrai para google_drive/_extracted/<ANO>/ (achatando subpastas).

Depois rode a unificação normal:
  .venv/bin/python scripts/01_unificar_anos.py <anos...>
"""
import re
import sys
import zipfile
from pathlib import Path

DRIVE = Path("google_drive")
EXTRACTED = DRIVE / "_extracted"


def agrupar_partes(files: list[Path]) -> dict[str, list[tuple[int, Path]]]:
    grupos: dict[str, list[tuple[int, Path]]] = {}
    for f in files:
        nome = f.name
        m = re.match(r"^(?P<base>.+)\.(?P<num>\d{3,})$", nome)          # x.zip.001 / x.001
        if m:
            grupos.setdefault(m.group("base"), []).append((int(m.group("num")), f))
            continue
        m = re.match(r"^(?P<base>.+)\.z(?P<num>\d{2,})$", nome, re.I)   # x.z01
        if m:
            grupos.setdefault(m.group("base"), []).append((int(m.group("num")), f))
            continue
        m = re.match(r"^(?P<base>.+?)[._-]part[._-]?(?P<num>\d+)$", nome, re.I)  # x_part_1
        if m:
            grupos.setdefault(m.group("base"), []).append((int(m.group("num")), f))
    return grupos


def ano_de(base: str) -> str | None:
    m = re.search(r"20\d{2}", base)
    return m.group(0) if m else None


def montar(grupo_base: str, partes: list[tuple[int, Path]]) -> Path:
    partes.sort(key=lambda t: t[0])
    nums = [n for n, _ in partes]
    if nums != list(range(nums[0], nums[0] + len(nums))):
        print(f"  [AVISO] sequência de volumes com lacunas: {nums}")

    destino = DRIVE / (grupo_base if grupo_base.endswith(".zip") else grupo_base + ".zip")
    with open(destino, "wb") as out:
        for _, p in partes:
            out.write(p.read_bytes())
    print(f"  remontado: {destino.name} ({destino.stat().st_size / 1e6:.1f} MB, "
          f"{len(partes)} volumes)")
    return destino


def extrair(zip_path: Path, ano: str) -> None:
    destino = EXTRACTED / ano
    destino.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        bad = zf.testzip()
        if bad:
            raise SystemExit(f"[ERRO] ZIP corrompido em {zip_path.name}: {bad}")
        for info in zf.infolist():
            if info.is_dir():
                continue
            nome = Path(info.filename).name          # achata subpastas
            if not nome.lower().endswith(".csv"):
                print(f"  (ignorado não-CSV: {info.filename})")
                continue
            with zf.open(info) as src, open(destino / nome, "wb") as dst:
                dst.write(src.read())
    csvs = sorted(p.name for p in destino.glob("*.csv"))
    print(f"  extraído: {zip_path.name} -> _extracted/{ano}/ ({len(csvs)} CSVs: {csvs})")


def main(alvos: list[str]):
    files = [f for f in DRIVE.iterdir() if f.is_file()]
    grupos = agrupar_partes(files)
    if not grupos:
        raise SystemExit("[ERRO] Nenhum conjunto de volumes encontrado em google_drive/. "
                         "Esperado: .001/.002, .z01/.z02 ou _part_N.")

    for base, partes in sorted(grupos.items()):
        ano = ano_de(base)
        if alvos and ano not in alvos:
            continue
        if ano is None:
            print(f"[AVISO] sem ano no nome: {base} — pulando")
            continue
        print(f"[{ano}] {base}: {len(partes)} volumes")
        z = montar(base, partes)
        extrair(z, ano)


if __name__ == "__main__":
    main(sys.argv[1:])
