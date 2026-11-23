# ErgoFlow: End-to-End Project Roadmap

## Phase 1: Python Ingestion & Spatial Geometry (Completed)
* **Chart Parsing:** Parse raw `.simai` chart files, resolving BPM changes and beat subdivisions into exact millisecond timestamps.
* **Spatial Projection:** Map perimeter buttons (`1–8`) and touch zones onto normalized 2D Cartesian coordinates $(x, y)$ on the unit circle ($R = 1.0$), generating valid candidate contact points (e.g., physical switch vs. inner glass edge).
* **In-Memory C++ Boundary:** Group concurrent events into chronological `TimedNoteGroup` objects backed by C++ structs exposed via `pybind11`, eliminating intermediate disk serialization.

---

## Phase 2: C++17 Kinematics Solver Engine
* **Configuration & Output Telemetry:** Define and bind `SolverConfig` (beam width, velocity limits, biomechanical penalty weights) and `KinematicFeatures` (mean/peak velocity, crossover duration percentage, hand balance, jack count, peak rolling NPS, and feasibility flag).
* **Trellis State Representation:** Implement cache-friendly, Plain Old Data (POD) `TrellisNode` structs tracking left/right hand coordinates, active hold lockout timers (`lock_until`), last active hand, cumulative path cost, and `parent_idx` for backtracking.
* **Biomechanical Cost Function:** Evaluate candidate hand transitions with hard constraints ($+\infty$ for hold lockout violations or exceeding $v_{\max}$) and soft biomechanical penalties (kinetic travel effort, arm crossovers where $x_L > x_R$, and rapid same-hand jacks).
* **Beam-Pruned Viterbi Search:** Step chronologically through the event trellis, branching single notes and 2-note chords across valid hand assignments while using `std::nth_element` to prune each column down to the top $K$ (e.g., $K = 32$) lowest-cost states.
* **Backtracking & Feature Aggregation:** Reconstruct the optimal hand sequence from $t_N \to t_0$ and compute summary physical telemetry in a single linear pass.

---

## Phase 3: Calibration, Validation & Dataset Generation
* **Synthetic Pattern Unit Tests:** Verify routing invariants across canonical test patterns (16th-note trills, slow single-side repeats, clockwise rotational spins, wide jumps, and hold-plus-stream lockouts) using `pytest`.
* **Weight Calibration:** Normalize cost sub-terms and tune transition weights ($w_{\text{vel}}, w_{\text{cross}}, w_{\text{jack}}$) against real `.simai` charts across difficulty tiers to align ergonomic strain scores with official chart difficulty ratings.
* **Batch Feature Extraction:** Run the compiled solver across a corpus of charts and export the resulting `KinematicFeatures` and pattern traces into a compressed Apache Parquet dataset (`features.parquet`).

---

## Phase 4: LLM Fine-Tuning & Backend Inference Pipeline
* **Instruction Dataset Construction:** Pair extracted kinematic telemetry and local bottleneck diagnostics (e.g., peak velocity spikes, heavy crossover sections, high-BPM jack bursts) with structured natural-language coaching and difficulty explanations.
* **Model Fine-Tuning (Qwen):** Fine-tune a Qwen language model to translate raw biomechanical solver metrics into actionable player feedback and pattern breakdowns.
* **Serving Infrastructure (vLLM + FastAPI):** Deploy the fine-tuned model via `vLLM` behind an async API endpoint that ingests an uploaded `.simai` file, runs the in-memory `pybind11` C++ solver in milliseconds, and returns structured JSON trajectories and diagnostics.

---

## Phase 5: Interactive Web Frontend & Visualizer
* **Chart Upload & Sandbox Interface:** Build a clean, responsive web UI allowing players to upload `.simai` files (or paste raw chart snippets) and dynamically tweak `SolverConfig` weights (velocity, crossover, jack penalties) in real time.
* **2D Cabinet Hand-Trajectory Visualizer:** Render an interactive HTML5 Canvas / SVG model of the 8-button *maimai* cabinet face with timeline scrubbing, animating predicted Left/Right hand paths, active hold lockouts, and crossover zones frame-by-frame.
* **Telemetry Dashboard & LLM Coaching Panel:** Display synchronized strain timelines (rolling NPS, velocity spikes, crossover windows) alongside the fine-tuned LLM's natural-language breakdown of difficult patterns and execution tips.

---

## Phase 6: Future Feature Expansion
* **Slide Path Kinematics:** Extend the geometry projector and C++ state machine to model continuous touch-screen slide trajectories (`-`, `^`, `v`, `p`, `q`, `s`, `z`, `w`) and star-tap-to-slide hand commitments.
* **Multi-Touch & Complex Chords:** Expand chord permutation handling to support 3+ simultaneous touch notes and multi-finger/palm contact zones.