"""Exact candidate queries for guide checks; no connectivity rules live here."""

from __future__ import annotations

import re
from functools import lru_cache


INDEX_THRESHOLD = 64
_METAL_RE = re.compile(r"^metal(\d+)$", re.I)
_LEAF_SIZE = 12
_GRID_CELL_SIZE = 16800
_GRID_MEMBERSHIPS_PER_RECT = 16


class _RectGrid:
    """Bounded sparse cells that only produce exact intersection candidates.

    Typical route guides span few cells. A complete membership-count pass
    precedes construction, so a large rectangle cannot expand this index
    beyond a fixed multiple of its input size.
    """

    @classmethod
    def try_build(cls, rects, layer_bits):
        memberships = 0
        limit = len(rects) * _GRID_MEMBERSHIPS_PER_RECT
        for rect in rects:
            # Keep the original hierarchy for geometry outside the integer,
            # ordered boxes emitted by the guide writer.
            if (any(type(value) is not int for value in
                    (rect.x1, rect.y1, rect.x2, rect.y2))
                    or rect.x1 > rect.x2 or rect.y1 > rect.y2):
                return None
            memberships += ((rect.x2 // _GRID_CELL_SIZE - rect.x1 // _GRID_CELL_SIZE + 1)
                            * (rect.y2 // _GRID_CELL_SIZE - rect.y1 // _GRID_CELL_SIZE + 1))
            if memberships > limit:
                return None
        return cls(rects, layer_bits)

    def __init__(self, rects, layer_bits):
        self.rects = rects
        self.layer_bits = layer_bits
        self._bit_values = tuple(dict.fromkeys(layer_bits))
        self._cells = {}
        for i, rect in enumerate(rects):
            for x in range(rect.x1 // _GRID_CELL_SIZE, rect.x2 // _GRID_CELL_SIZE + 1):
                for y in range(rect.y1 // _GRID_CELL_SIZE, rect.y2 // _GRID_CELL_SIZE + 1):
                    self._cells.setdefault((x, y, layer_bits[i]), []).append(i)

    def intersections(self, x1, y1, x2, y2, allowed=0, after=-1):
        rects = self.rects
        if any(type(value) is not int for value in (x1, y1, x2, y2)):
            candidates = range(len(rects))
        else:
            # A negative coverage margin inverts the query. Enumerate a
            # conservative enclosing range, then retain the exact old test.
            xlo, xhi = min(x1, x2) // _GRID_CELL_SIZE, max(x1, x2) // _GRID_CELL_SIZE
            ylo, yhi = min(y1, y2) // _GRID_CELL_SIZE, max(y1, y2) // _GRID_CELL_SIZE
            if (xhi - xlo + 1) * (yhi - ylo + 1) > max(512, len(rects) * 8):
                # A huge pin margin must not expand the sparse query range.
                candidates = range(len(rects))
            else:
                bits = [bit for bit in self._bit_values if not allowed or allowed & bit]
                candidates = set()
                for x in range(xlo, xhi + 1):
                    for y in range(ylo, yhi + 1):
                        for bit in bits:
                            for i in self._cells.get((x, y, bit), ()):
                                if i > after:
                                    candidates.add(i)
        for i in candidates:
            if i <= after or (allowed and not (allowed & self.layer_bits[i])):
                continue
            rect = rects[i]
            if not (rect.x2 < x1 or x2 < rect.x1 or rect.y2 < y1 or y2 < rect.y1):
                yield i


class _RectIndex:
    """Static bounding-box hierarchy over original rectangle indices.

    Every node bounds all its members, so pruning cannot discard an actual
    intersection. Degenerate or densely overlapping inputs may still require
    quadratic work, but never switch to an approximate connectivity decision.
    """

    def __init__(self, rects, indices, layer_bits):
        self.rects = rects
        self.layer_bits = layer_bits
        self.root = self._build(list(indices))

    def _build(self, indices):
        rects = self.rects
        bounds = (min(rects[i].x1 for i in indices),
                  min(rects[i].y1 for i in indices),
                  max(rects[i].x2 for i in indices),
                  max(rects[i].y2 for i in indices))
        if len(indices) <= _LEAF_SIZE:
            mask = 0
            for i in indices:
                mask |= self.layer_bits[i]
            maximum = max(indices)
            return bounds, None, None, indices, mask, maximum
        # Split by center spread, rather than rectangle width: many parallel
        # long guides have identical X extents but are separated along Y.
        xcenters = [rects[i].x1 + rects[i].x2 for i in indices]
        ycenters = [rects[i].y1 + rects[i].y2 for i in indices]
        if max(xcenters) - min(xcenters) >= max(ycenters) - min(ycenters):
            indices.sort(key=lambda i: (rects[i].x1 + rects[i].x2, i))
        else:
            indices.sort(key=lambda i: (rects[i].y1 + rects[i].y2, i))
        middle = len(indices) // 2
        left = self._build(indices[:middle])
        right = self._build(indices[middle:])
        return bounds, left, right, None, left[4] | right[4], max(left[5], right[5])

    def intersections(self, x1, y1, x2, y2, allowed=0, after=-1):
        stack = [self.root]
        rects = self.rects
        while stack:
            bounds, left, right, indices, mask, maximum = stack.pop()
            if maximum <= after or (allowed and not (allowed & mask)):
                continue
            if bounds[2] < x1 or x2 < bounds[0] or bounds[3] < y1 or y2 < bounds[1]:
                continue
            if indices is None:
                stack.append(right)
                stack.append(left)
                continue
            for i in indices:
                if i <= after or (allowed and not (allowed & self.layer_bits[i])):
                    continue
                rect = rects[i]
                if not (rect.x2 < x1 or x2 < rect.x1 or rect.y2 < y1 or y2 < rect.y1):
                    yield i


class GuideSpatialIndex:
    """Share one exact spatial index between pin coverage and guide neighbors.

    Sparse cells accelerate bounded guide boxes; the hierarchy handles large
    or unusual geometry. Neither changes coordinate tolerances or order.
    """

    def __init__(self, rects):
        self.rects = rects
        self._all = None
        self._bits = {}
        self._keys = [self._layer_key(r.layer) for r in rects]
        for key in self._keys:
            if key not in self._bits:
                self._bits[key] = 1 << len(self._bits)
        self._layer_bits = [self._bits[key] for key in self._keys]
        self._neighbor_bits = {}
        for key, bit in self._bits.items():
            if key[0] == "metal":
                bit |= (self._bits.get(("metal", key[1] - 1), 0)
                        | self._bits.get(("metal", key[1] + 1), 0))
            self._neighbor_bits[key] = bit

    def _ensure_all(self):
        if self._all is None:
            self._all = _RectGrid.try_build(self.rects, self._layer_bits)
            if self._all is None:
                self._all = _RectIndex(self.rects, range(len(self.rects)), self._layer_bits)

    @staticmethod
    @lru_cache(maxsize=128)
    def _layer_key(layer):
        match = _METAL_RE.match(layer)
        return ("metal", int(match.group(1))) if match else ("raw", layer)

    def first_covering_rect(self, x, y, margin):
        if not self.rects:
            return None
        self._ensure_all()
        # Original file order decides which component a covered pin belongs
        # to; traversal order of the hierarchy must not affect that choice.
        return min(self._all.intersections(x - margin, y - margin,
                                           x + margin, y + margin), default=None)

    def later_neighbors(self, i):
        self._ensure_all()
        rect = self.rects[i]
        allowed = self._neighbor_bits[self._keys[i]]
        # Preserve the old nested-loop union order and component root IDs.
        return sorted(self._all.intersections(
            rect.x1 - 1, rect.y1 - 1, rect.x2 + 1, rect.y2 + 1, allowed, i))
