from __future__ import annotations
from MRzeroCore import _prepass
from MRzeroCore._prepass import PyDistribution as PrePassState
from ..sequence import Sequence
from ..phantom.sim_data import SimData
import torch
import numpy as np
import matplotlib.pyplot as plt
from typing import Literal


# TODO: Add documentation and functions to analyze the graph
# TODO: Maybe convert tensors to list (nyquist and fov) only in compute_graph_ext


def compute_graph(
    seq: Sequence,
    data: SimData,
    max_state_count: int = 200,
    min_state_mag: float = 1e-4
) -> Graph:
    """Like pre_pass.compute_graph, but computes args from `` data``."""
    return compute_graph_ext(
        seq,
        float(torch.mean(data.T1)),
        float(torch.mean(data.T2)),
        float(torch.mean(data.T2dash)),
        float(torch.mean(data.D)),
        max_state_count,
        min_state_mag,
        data.nyquist.tolist(),
        data.fov.tolist(),
        data.avg_B1_trig
    )


def compute_graph_ext(
    seq: Sequence,
    T1: float,
    T2: float,
    T2dash: float,
    D: float,
    max_state_count: int = 200,
    min_state_mag: float = 1e-4,
    nyquist: tuple[float, float, float] = (float('inf'), float('inf'), float('inf')),
    fov: tuple[float, float, float] = (1.0, 1.0, 1.0),
    avg_b1_trig: torch.Tensor | None = None,
) -> Graph:
    if min_state_mag < 0:
        min_state_mag = 0

    if avg_b1_trig is None:
        angle = torch.linspace(0, 2*np.pi, 361)
        avg_b1_trig = torch.stack([
            torch.sin(angle),
            torch.cos(angle),
            torch.sin(angle/2)**2
        ], dim=1).type(torch.float32)

    return Graph(_prepass.compute_graph(
        seq,
        T1, T2, T2dash, D,
        max_state_count, min_state_mag,
        nyquist, fov,
        avg_b1_trig
    ))


class Graph(list):
    def __init__(self, graph: list[list[PrePassState]]) -> None:
        super().__init__(graph)

    def plot(self,
             transversal_mag: bool = True,
             dephasing: Literal["k_x", "k_y", "k_z", "t"] = "t",
             color: Literal[
                 "abs(mag)", "phase(mag)", "weight", "signal", "rel. signal"
             ] = "weight",
             log_color: bool = True):
        data = []
        kt_idx = {"k_x": 0, "k_y": 1, "k_z": 2, "t": 3}[dephasing]

        def extract(state: PrePassState):
            if color == "abs(mag)":
                value = np.abs(state.prepass_mag)
            elif color == "phase(mag)":
                value = np.angle(state.prepass_mag)
            elif color == "weight":
                value = state.weight
            elif color == "signal":
                value = state.signal
            elif color == "rel. signal":
                value = state.rel_signal
            if log_color:
                value = np.log10(np.abs(value) + 1e-7)
            return value

        for r, rep in enumerate(self):
            for state in rep:
                if transversal_mag == (state.dist_type == "+"):
                    data.append((
                        r,
                        state.prepass_kt_vec[kt_idx],
                        extract(state),
                    ))

        data.sort(key=lambda d: d[2])
        data = np.asarray(data)

        plt.scatter(data[:, 0], data[:, 1], c=data[:, 2], s=20)
        plt.xlabel("Repetition")
        plt.ylabel(f"${dephasing}$ - Dephasing")
        if log_color:
            plt.colorbar(label="log. " + color)
        else:
            plt.colorbar(label=color)
