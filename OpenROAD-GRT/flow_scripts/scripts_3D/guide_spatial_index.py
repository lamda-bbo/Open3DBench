"""Exact candidate queries for guide checks; no connectivity rules live here."""

from __future__ import annotations

import re
from functools import lru_cache


INDEX_THRESHOLD = 64
_METAL_RE = re.compile(r"^metal(\d+)$", re.I)
_LEAF_SIZE = 12


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
    """Share one exact spatial tree between pin coverage and guide neighbors.

    Node masks prune impossible layers and node maxima prune earlier guide
    indices. Neither filter changes coordinate tolerances or returned order.
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

    def _ensure_all(self):
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
        key = self._keys[i]
        keys = [key]
        if key[0] == "metal":
            keys.extend((("metal", key[1] - 1), ("metal", key[1] + 1)))
        allowed = 0
        for layer_key in keys:
            allowed |= self._bits.get(layer_key, 0)
        # Preserve the old nested-loop union order and component root IDs.
        return sorted(self._all.intersections(
            rect.x1 - 1, rect.y1 - 1, rect.x2 + 1, rect.y2 + 1, allowed, i))
