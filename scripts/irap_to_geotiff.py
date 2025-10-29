#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Конвертация IRAP ASCII grid в GeoTIFF для корректной работы в QGIS.
Логика выбора СК и возможной перестановки X/Y повторяет правила из sql-func.sql.

Пример:
  python scripts/irap_to_geotiff.py --input test.irap --output temp/test.tif
  python scripts/irap_to_geotiff.py --input test.irap --uwi AKG123 --output temp/test.tif

Если СК не удаётся определить (например, попали в gkN диапазон без UWI),
можно указать вручную исходный EPSG: --src-epsg 28469
"""

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Optional, Tuple, List

import numpy as np

try:
    import rasterio
    from rasterio.crs import CRS
    from rasterio.transform import Affine, array_bounds
    from rasterio.warp import calculate_default_transform, reproject, Resampling
except Exception as exc:
    print("[ERROR] Требуется пакет rasterio. Установите зависимости: pip install -r requirements.txt", file=sys.stderr)
    raise


@dataclass
class IRAPGrid:
    data: np.ndarray  # shape (nrows, ncols)
    ncols: int
    nrows: int
    dx: float
    dy: float
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    nodata: float


# --- Логика из sql-func.sql -------------------------------------------------

# Диапазоны как в sql-файле
WGS_BOUNDS = (45, 85, 37, 57)           # x in [45,85], y in [37,57]
GK9_BOUNDS = (9200000, 9800000, 4500000, 6000000)
GK10_BOUNDS = (10200000, 10800000, 4500000, 6000000)
GK11_BOUNDS = (11200000, 11800000, 4500000, 6000000)
GK12_BOUNDS = (12200000, 12800000, 4500000, 6000000)
SK66_BOUNDS = (11500000, 12500000, 3500000, 4500000)
GKN_BOUNDS = (200000, 800000, 4500000, 6000000)

# Префиксы UWI из sql-файла
UWI_PREFIXES_8 = [
    'AKG', 'AIR', 'AKD', 'AKK', 'ALA', 'ASA', 'ASH', 'ATA', 'ATB', 'ATK', 'BBK',
    'BEK', 'BJR', 'BLG', 'BNS', 'BTN', 'BUR', 'DMB', 'DSK', 'DSR', 'ELZ', 'ESB',
    'GRN', 'IKN', 'JET', 'KAL', 'KKL', 'KKR', 'KMB', 'KNK', 'KON', 'KRK', 'KRT',
    'KSG', 'KSH', 'KSM', 'KZH', 'LMN', 'MKT', 'MSB', 'NBZ', 'NRG', 'OIM', 'PRI',
    'RVN', 'SAK', 'SGZ', 'SJB', 'SKA', 'STV', 'TNU', 'TSG', 'TTR', 'TZH', 'UAZ',
    'UJE', 'UKM', 'UVK', 'UVN', 'UZK', 'UZN', 'UZS', 'UZV', 'VMT', 'VOS', 'ZBN',
    'ZHT', 'ZPV'
]
UWI_PREFIXES_9 = [
    'ALB', 'JLM', 'KLR', 'KNB', 'KOZ', 'KRA', 'KSB', 'KSC', 'KTU', 'LAK', 'SKS',
    'STS', 'STU', 'STV', 'SZK', 'TLS', 'UKM', 'VMB'
]
UWI_PREFIXES_10 = [
    'AKH', 'AKH', 'AKH', 'AKS', 'AKS', 'NUR'  # Дубликаты сохранены как в sql
]


@dataclass
class CoordSystemDecision:
    cs_id: Optional[int]
    swapped_xy: bool


def _in_bounds(x: float, y: float, bounds: Tuple[float, float, float, float]) -> bool:
    return (bounds[0] < x < bounds[1]) and (bounds[2] < y < bounds[3])


def _check_x_y_point(x: float, y: float) -> Tuple[Optional[Tuple[float, float]], bool]:
    """Имитация mapbuilder.check_x_y для одной точки.
    Возвращает (point_or_none, swapped).
    """
    # как в sql: сначала проверяем "как есть"
    ranges_normal = [WGS_BOUNDS, GK9_BOUNDS, GK10_BOUNDS, GK11_BOUNDS, GK12_BOUNDS, SK66_BOUNDS, GKN_BOUNDS]
    for b in ranges_normal:
        if _in_bounds(x, y, b):
            return (x, y), False
    # затем проверяем с перестановкой X/Y для зон GK9-12 и SK66
    ranges_swap = [GK9_BOUNDS, GK10_BOUNDS, GK11_BOUNDS, GK12_BOUNDS, SK66_BOUNDS]
    for b in ranges_swap:
        if _in_bounds(y, x, b):
            return (y, x), True
    return None, False


def _uwi_matches(uwi: Optional[str], prefixes: List[str]) -> bool:
    if not uwi:
        return False
    up = uwi.strip().upper()
    return any(up.startswith(p) for p in prefixes)


def decide_coord_system(x: float, y: float, uwi: Optional[str]) -> CoordSystemDecision:
    """Имитация mapbuilder.get_coord_system с дополнительной проверкой перестановки X/Y.
    Возвращает cs_id и признак, что пришлось менять X/Y.
    """
    pt, swapped = _check_x_y_point(x, y)
    if pt is None:
        return CoordSystemDecision(cs_id=None, swapped_xy=False)
    x2, y2 = pt

    cs_id: Optional[int] = None
    if _in_bounds(x2, y2, WGS_BOUNDS):
        cs_id = 1
    elif _in_bounds(x2, y2, GK9_BOUNDS):
        cs_id = 3
    elif _in_bounds(x2, y2, GK10_BOUNDS):
        cs_id = 4
    elif _in_bounds(x2, y2, GK11_BOUNDS):
        cs_id = 5
    elif _in_bounds(x2, y2, GK12_BOUNDS):
        cs_id = 6
    elif _in_bounds(x2, y2, SK66_BOUNDS):
        cs_id = 7
    elif _in_bounds(x2, y2, GKN_BOUNDS):
        if _uwi_matches(uwi, UWI_PREFIXES_8):
            cs_id = 8
        elif _uwi_matches(uwi, UWI_PREFIXES_9):
            cs_id = 9
        elif _uwi_matches(uwi, UWI_PREFIXES_10):
            cs_id = 10
        else:
            cs_id = None  # требуется UWI, иначе из sql-логики вернуть нельзя

    return CoordSystemDecision(cs_id=cs_id, swapped_xy=swapped)


def cs_id_to_epsg(cs_id: int) -> int:
    """Как в mapbuilder.get_geometry (SRID источника перед трансформацией в 4326)."""
    if cs_id == 1:
        return 4326
    if cs_id == 3:
        return 28409
    if cs_id == 4:
        return 28410
    if cs_id == 5:
        return 28411
    if cs_id == 6:
        return 28412
    if cs_id == 7:
        # В sql-файле указан 420966. Если GDAL/PROJ его не знает, используйте --src-epsg.
        return 420966
    if cs_id == 8:
        return 28469
    if cs_id == 9:
        return 28470
    if cs_id == 10:
        return 28471
    raise ValueError(f"Неизвестный cs_id: {cs_id}")


# --- Парсер IRAP -------------------------------------------------------------

def parse_irap(path: str) -> IRAPGrid:
    """Простой парсер IRAP на основе примера формата из репозитория.
    Ожидания:
      1-я строка: NODATA, NCOLS, DX, DY
      2-я строка: Xmin, Xmax, Ymin, Ymax
      Далее: значения построчно (nrows строк, по ncols значений в строке)
    """
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    if len(lines) < 3:
        raise ValueError("IRAP: Слишком мало строк")

    # Первая строка
    parts1 = lines[0].split()
    if len(parts1) < 4:
        raise ValueError("IRAP: ожидается 4 значения в первой строке: NODATA NCOLS DX DY")
    nodata = float(parts1[0])
    ncols = int(float(parts1[1]))
    dx = float(parts1[2])
    dy = float(parts1[3])

    # Вторая строка
    parts2 = lines[1].split()
    if len(parts2) < 4:
        raise ValueError("IRAP: ожидается 4 значения во второй строке: Xmin Xmax Ymin Ymax")
    x_min, x_max, y_min, y_max = map(float, parts2[:4])

    # Остальные строки — данные
    value_lines = lines[2:]
    data_list: List[List[float]] = []
    for ln in value_lines:
        row = [float(x) for x in ln.split()]
        if len(row) != ncols:
            raise ValueError(f"IRAP: строка данных имеет {len(row)} значений, ожидалось {ncols}")
        data_list.append(row)

    nrows = len(data_list)
    if nrows <= 0:
        raise ValueError("IRAP: нет данных")

    # Преобразуем в массив (nrows, ncols)
    data = np.array(data_list, dtype=np.float32)

    # Лёгкая валидация согласованности геометрии (не критично)
    # Если extents приходят как размеры (Xmax - Xmin) ~= ncols * dx
    expected_width = abs(x_max - x_min)
    expected_height = abs(y_max - y_min)
    if not np.isclose(expected_width, ncols * dx):
        # допускаем расхождение, но предупредим
        print(f"[WARN] Ширина по экстенту ({expected_width}) != ncols*dx ({ncols*dx})", file=sys.stderr)
    if not np.isclose(expected_height, nrows * dy):
        print(f"[WARN] Высота по экстенту ({expected_height}) != nrows*dy ({nrows*dy})", file=sys.stderr)

    return IRAPGrid(
        data=data,
        ncols=ncols,
        nrows=nrows,
        dx=dx,
        dy=dy,
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        nodata=nodata,
    )


# --- Геопривязка и репроекция -----------------------------------------------

def build_transform(x_min: float, x_max: float, y_min: float, y_max: float, ncols: int, nrows: int, dx: float, dy: float) -> Affine:
    """Аффинное преобразование: пиксель (0,0) — верхний левый угол (x_min, y_max)."""
    # Предполагаем, что данные идут строками сверху вниз (north->south),
    # тогда шаг по Y отрицательный.
    return Affine(dx, 0, x_min, 0, -dy, y_max)


def write_geotiff(path: str, data: np.ndarray, transform: Affine, crs: CRS, nodata: float) -> None:
    height, width = data.shape
    profile = {
        'driver': 'GTiff',
        'height': height,
        'width': width,
        'count': 1,
        'dtype': data.dtype,
        'transform': transform,
        'crs': crs,
        'nodata': nodata,
        'tiled': True,
        'compress': 'deflate',
        'predictor': 2,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with rasterio.open(path, 'w', **profile) as dst:
        dst.write(data, 1)


def reproject_to_epsg4326(src_data: np.ndarray, src_transform: Affine, src_crs: CRS, nodata: float, out_path: str) -> None:
    dst_crs = CRS.from_epsg(4326)

    # Рассчитываем оптимальную геометрию назначения
    src_height, src_width = src_data.shape
    left, bottom, right, top = array_bounds(src_height, src_width, src_transform)
    dst_transform, dst_width, dst_height = calculate_default_transform(
        src_crs, dst_crs, src_width, src_height, left=left, bottom=bottom, right=right, top=top
    )

    dst_data = np.full((dst_height, dst_width), nodata, dtype=src_data.dtype)

    kwargs = {
        'src_transform': src_transform,
        'src_crs': src_crs,
        'src_nodata': nodata,
        'dst_transform': dst_transform,
        'dst_crs': dst_crs,
        'dst_nodata': nodata,
        'resampling': Resampling.bilinear,
    }

    with rasterio.Env():
        reproject(
            source=src_data,
            destination=dst_data,
            **kwargs,
        )

    write_geotiff(out_path, dst_data, dst_transform, dst_crs, nodata)


# --- CLI ---------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="IRAP ASCII -> GeoTIFF (4326) по логике sql-func.sql")
    parser.add_argument('--input', '-i', required=True, help='Путь к IRAP-файлу')
    parser.add_argument('--output', '-o', required=False, help='Путь к выходному GeoTIFF (по умолчанию temp/<name>.tif)')
    parser.add_argument('--uwi', required=False, help='UWI (для выбора cs_id 8/9/10 в зоне gkN)')
    parser.add_argument('--src-epsg', required=False, type=int, help='Явный EPSG исходной СК (перекрывает авто-логику)')
    parser.add_argument('--keep-src-crs', action='store_true', help='Не репроецировать в 4326, сохранить исходную СК')

    args = parser.parse_args()

    in_path = os.path.abspath(args.input)
    if not os.path.isfile(in_path):
        print(f"[ERROR] Файл не найден: {in_path}", file=sys.stderr)
        return 2

    # Выходной путь по умолчанию — в temp/
    if args.output:
        out_path = os.path.abspath(args.output)
    else:
        base = os.path.splitext(os.path.basename(in_path))[0] + '.tif'
        out_path = os.path.abspath(os.path.join(os.getcwd(), 'temp', base))

    # Парсинг IRAP
    grid = parse_irap(in_path)

    # Точка для определения СК — центр экстента
    cx = (grid.x_min + grid.x_max) / 2.0
    cy = (grid.y_min + grid.y_max) / 2.0

    decision = decide_coord_system(cx, cy, args.uwi)

    # Если авто-логика не смогла определить СК, пробуем src-epsg
    src_epsg: Optional[int] = None
    swapped = decision.swapped_xy

    if args.src_epsg is not None:
        src_epsg = int(args.src_epsg)
    else:
        if decision.cs_id is None:
            print(
                "[ERROR] Не удалось определить систему координат по данным и UWI. "
                "Укажите --src-epsg или передайте корректный --uwi.",
                file=sys.stderr,
            )
            return 2
        src_epsg = cs_id_to_epsg(decision.cs_id)

    # При необходимости переставляем оси: транспонируем данные и меняем экстенты
    data = grid.data
    ncols, nrows = grid.ncols, grid.nrows
    x_min, x_max, y_min, y_max = grid.x_min, grid.x_max, grid.y_min, grid.y_max
    dx, dy = grid.dx, grid.dy

    if swapped:
        data = data.T.copy()
        ncols, nrows = nrows, ncols
        # Меняем местами оси и параметры экстента/шага
        x_min, x_max, y_min, y_max = y_min, y_max, x_min, x_max
        dx, dy = dy, dx

    src_transform = build_transform(x_min, x_max, y_min, y_max, ncols, nrows, dx, dy)

    try:
        src_crs = CRS.from_epsg(src_epsg)
    except Exception:
        print(
            f"[ERROR] Не удалось создать CRS из EPSG:{src_epsg}. "
            f"Укажите корректный --src-epsg (например, 28409/28410/28411/28412/4326)",
            file=sys.stderr,
        )
        return 2

    # Если не требуется репроекция — пишем как есть
    if args.keep_src_crs or src_epsg == 4326:
        write_geotiff(out_path, data, src_transform, src_crs, grid.nodata)
        print(f"[OK] Записан GeoTIFF: {out_path}")
        return 0

    # Иначе — репроекция в 4326, как делает get_geometry
    reproject_to_epsg4326(data, src_transform, src_crs, grid.nodata, out_path)
    print(f"[OK] Записан GeoTIFF (EPSG:4326): {out_path}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
