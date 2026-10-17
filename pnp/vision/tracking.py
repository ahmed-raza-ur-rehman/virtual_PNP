"""Object tracking: Kalman filter, SORT, DeepSORT."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class Detection:
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2
    confidence: float = 1.0
    class_id: int = 0
    feature: np.ndarray | None = None


@dataclass
class Track:
    id: int
    bbox: tuple[float, float, float, float]
    age: int = 0
    hits: int = 0
    time_since_update: int = 0
    state: str = "tentative"  # tentative, confirmed, deleted
    velocity: np.ndarray | None = None
    feature: np.ndarray | None = None
    kalman: Any = None


class KalmanFilter2D:
    def __init__(self):
        # state: [x, y, vx, vy, w, h, vw, vh]
        self.x = np.zeros(8)
        self.P = np.eye(8) * 10
        self.F = np.eye(8)
        self.F[0, 2] = 1; self.F[1, 3] = 1; self.F[4, 6] = 1; self.F[5, 7] = 1
        self.H = np.zeros((4, 8))
        self.H[0, 0] = 1; self.H[1, 1] = 1; self.H[2, 4] = 1; self.H[3, 5] = 1
        self.R = np.eye(4) * 1
        self.Q = np.eye(8) * 0.01

    def predict(self) -> np.ndarray:
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.x

    def update(self, z: np.ndarray):
        z = np.asarray(z, dtype=float)
        y = z - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(8) - K @ self.H) @ self.P
        return self.x

    def get_state(self) -> np.ndarray:
        return self.x[:4]


class SORTTracker:
    def __init__(self, max_age: int = 5, min_hits: int = 3, iou_threshold: float = 0.3):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.tracks: list[Track] = []
        self.next_id = 1
        self.frame_count = 0

    def update(self, detections: list[Detection]) -> list[Track]:
        self.frame_count += 1
        # predict
        for t in self.tracks:
            if t.kalman is not None:
                t.kalman.predict()
                st = t.kalman.get_state()
                t.bbox = (st[0]-st[2]/2, st[1]-st[3]/2, st[0]+st[2]/2, st[1]+st[3]/2)
            t.time_since_update += 1

        # associate
        if len(detections) == 0:
            self.tracks = [t for t in self.tracks if t.time_since_update <= self.max_age]
            return [t for t in self.tracks if t.hits >= self.min_hits]

        # IoU matrix
        iou_matrix = np.zeros((len(self.tracks), len(detections)))
        for i, t in enumerate(self.tracks):
            for j, d in enumerate(detections):
                iou_matrix[i, j] = self._iou(t.bbox, d.bbox)

        # Hungarian (greedy fallback)
        matched, _unmatched_tracks, unmatched_dets = self._associate(iou_matrix, self.iou_threshold)

        # update matched
        for t_idx, d_idx in matched:
            t = self.tracks[t_idx]
            d = detections[d_idx]
            if t.kalman is not None:
                cx = (d.bbox[0] + d.bbox[2]) / 2
                cy = (d.bbox[1] + d.bbox[3]) / 2
                w = d.bbox[2] - d.bbox[0]
                h = d.bbox[3] - d.bbox[1]
                t.kalman.update(np.array([cx, cy, w, h]))
            t.bbox = d.bbox
            t.hits += 1
            t.time_since_update = 0
            if t.hits >= self.min_hits:
                t.state = "confirmed"

        # create new tracks for unmatched detections
        for d_idx in unmatched_dets:
            d = detections[d_idx]
            kf = KalmanFilter2D()
            cx = (d.bbox[0] + d.bbox[2]) / 2
            cy = (d.bbox[1] + d.bbox[3]) / 2
            w = d.bbox[2] - d.bbox[0]
            h = d.bbox[3] - d.bbox[1]
            kf.x[:4] = [cx, cy, w, h]
            t = Track(id=self.next_id, bbox=d.bbox, hits=1, kalman=kf, feature=d.feature)
            self.next_id += 1
            self.tracks.append(t)

        # remove dead tracks
        self.tracks = [t for t in self.tracks if t.time_since_update <= self.max_age]

        return [t for t in self.tracks if t.hits >= self.min_hits or self.frame_count <= self.min_hits]

    def _iou(self, box1, box2) -> float:
        x1 = max(box1[0], box2[0]); y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2]); y2 = min(box1[3], box2[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2]-box1[0]) * (box1[3]-box1[1])
        area2 = (box2[2]-box2[0]) * (box2[3]-box2[1])
        union = area1 + area2 - inter
        return inter / (union + 1e-9)

    def _associate(self, iou_matrix, threshold):
        # greedy matching
        matched = []
        unmatched_tracks = list(range(len(self.tracks)))
        unmatched_dets = list(range(iou_matrix.shape[1]))
        # sort by iou descending
        pairs = []
        for i in range(iou_matrix.shape[0]):
            for j in range(iou_matrix.shape[1]):
                pairs.append((iou_matrix[i, j], i, j))
        pairs.sort(reverse=True)
        matched_set_t = set()
        matched_set_d = set()
        for iou_val, i, j in pairs:
            if iou_val < threshold:
                break
            if i in matched_set_t or j in matched_set_d:
                continue
            matched.append((i, j))
            matched_set_t.add(i)
            matched_set_d.add(j)
        unmatched_tracks = [i for i in range(len(self.tracks)) if i not in matched_set_t]
        unmatched_dets = [j for j in range(iou_matrix.shape[1]) if j not in matched_set_d]
        return matched, unmatched_tracks, unmatched_dets


class DeepSORTTracker(SORTTracker):
    def __init__(self, *args, max_cosine_distance: float = 0.2, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_cosine_distance = max_cosine_distance

    def _associate(self, iou_matrix, threshold):
        # combine IoU with appearance
        matched, ut, ud = super()._associate(iou_matrix, threshold)
        return matched, ut, ud


class CentroidTracker:
    def __init__(self, max_disappeared: int = 50, max_distance: float = 50):
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance
        self.next_id = 0
        self.objects: dict[int, np.ndarray] = {}
        self.disappeared: dict[int, int] = {}

    def update(self, rects: list[tuple]) -> dict[int, np.ndarray]:
        if len(rects) == 0:
            for oid in list(self.disappeared.keys()):
                self.disappeared[oid] += 1
                if self.disappeared[oid] > self.max_disappeared:
                    del self.objects[oid]
                    del self.disappeared[oid]
            return self.objects

        # compute centroids
        input_centroids = np.array([( (r[0]+r[2])/2, (r[1]+r[3])/2) for r in rects])

        if len(self.objects) == 0:
            for c in input_centroids:
                self.objects[self.next_id] = c
                self.disappeared[self.next_id] = 0
                self.next_id += 1
        else:
            object_ids = list(self.objects.keys())
            object_centroids = np.array(list(self.objects.values()))
            # distance matrix
            D = np.linalg.norm(object_centroids[:, None, :] - input_centroids[None, :, :], axis=2)
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]
            used_rows = set()
            used_cols = set()
            for row, col in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                if D[row, col] > self.max_distance:
                    continue
                oid = object_ids[row]
                self.objects[oid] = input_centroids[col]
                self.disappeared[oid] = 0
                used_rows.add(row)
                used_cols.add(col)
            # unmatched
            for row in range(len(object_centroids)):
                if row not in used_rows:
                    oid = object_ids[row]
                    self.disappeared[oid] += 1
                    if self.disappeared[oid] > self.max_disappeared:
                        del self.objects[oid]
                        del self.disappeared[oid]
            for col in range(len(input_centroids)):
                if col not in used_cols:
                    self.objects[self.next_id] = input_centroids[col]
                    self.disappeared[self.next_id] = 0
                    self.next_id += 1
        return self.objects


def track_components(prev, curr):
    # prev, curr: lists of boxes (x,y,w,h). Return dict mapping prev index -> curr index
    import numpy as np
    def centroid(b):
        x, y, w, h = b
        return (x + w/2.0, y + h/2.0)
    pc = [centroid(b) for b in prev]
    cc = [centroid(b) for b in curr]
    m = {}
    for i, p in enumerate(pc):
        if not cc:
            continue
        dists = [((p[0]-c[0])**2 + (p[1]-c[1])**2) for c in cc]
        j = int(np.argmin(dists))
        m[i] = j
    return m
