# Place-MoL

Memory-on-logic (MoL) placement flow in Open3DBench. This repository covers the placement-centric part of the MoL flow for face-to-face 3D integration, where the bottom die mainly hosts logic and the top die hosts memory macros. It takes benchmark cases and produces MoL placement results that can later be evaluated in `OpenROAD-3D`.

The main flow supports:

- **Partition**: split macros between top and bottom dies with `GNN`, `min-cut`, or `max-cut`
- **Macro placement**: either an analytical pseudo-3D method that prioritizes wirelength, or a tiling method that prioritizes regularity
- **Legalization**: grid-based macro legalization after continuous or greedy placement
- **Cell placement**: DREAMPlace-based bottom-die cell placement with top-die macros projected as fixed obstacles

Method naming:

- `mol-analytical` corresponds to the analytical pseudo-3D macro placement strategy
- `mol-tiling` corresponds to the tiling-based macro placement strategy

## Repository Layout

```text
Place-MoL/
├── benchmarks/              # Runtime benchmark data used by the 3D flow
│   ├── nangate45/           # LEF/LIB and related technology files
│   └── or_3D/               # 3D benchmark case inputs
├── config/                  # 3D JSON configs
├── scripts/                 # Entry scripts
├── src/                     # 3D placement code
├── DREAMPlace/              # DREAMPlace submodule / build tree
└── start_docker_place.sh    # Docker launch helper
```

## Installation

### 1. Get Docker image

(It is shared with Place-LoL, so if you have pulled one during Place-LoL, you don't have to pull again here)

```bash
docker pull shiyunqi/open3dbench:place
```

### 2. Get benchmark data

Download `benchmark_mol.tar.gz` from [Google Drive](https://drive.google.com/file/d/1RXBa9W5b28w_sv0u6hjv4-57EDpPo7xK/view?usp=sharing) and extract it under the current directory:

The downloaded file is `benchmark_mol.tar.gz`. After extraction and renaming, the directory should be `benchmarks/`.

```bash
cd Place-MoL
wget -O benchmark_mol.tar.gz 'https://drive.google.com/uc?export=download&id=1RXBa9W5b28w_sv0u6hjv4-57EDpPo7xK'
tar -xzf benchmark_mol.tar.gz -C .
mv benchmark_mol benchmarks
```

### 3. Launch container

Run from the `Place-MoL` root:

```bash
cd Place-MoL
./start_docker_place.sh
```

Inside the container, the `Place-MoL` root is mounted at `/workspace`.

## Usage

All commands below should be run from the `Place-MoL` root.
Inside Docker, this means running them from `/workspace`.

### Analytical MoL

```bash
python src/place_3d/main.py --benchmark=<benchmark> --seed=3 --config_file=<config_json>
```

Examples:

```bash
python src/place_3d/main.py --benchmark=ariane133 --seed=3 --config_file=or_3D.json
python src/place_3d/main.py --benchmark=bp_quad --seed=3 --config_file=or_3D_bp_quad.json
python src/place_3d/main.py --benchmark=bp_be --seed=3 --config_file=or_3D_bp_be.json
python src/place_3d/main.py --benchmark=swerv_wrapper --seed=3 --config_file=or_3D_swerv.json
```

This flow builds a 2D prototype, refines bottom-die macro positions, legalizes them, optimizes top-die macro coordinates, legalizes again, and finally runs bottom-die cell placement.

### Tiling MoL

```bash
python src/place_3d/main_greedy.py --benchmark=<benchmark> --seed=3 --config_file=<config_json>
```

Examples:

```bash
python src/place_3d/main_greedy.py --benchmark=ariane133 --seed=3 --config_file=or_3D.json
python src/place_3d/main_greedy.py --benchmark=bp_quad --seed=42 --config_file=or_3D_bp_quad.json
```

Compared with the analytical flow, this method uses a skyline-style packing procedure to obtain a more regular macro layout, then runs bottom-die cell placement.

### Batch Experiments

Analytical placement flow:

```bash
./scripts/experiments_mol_analytical.sh
```

Tiling placement flow:

```bash
./scripts/experiments_mol_tiling.sh
```

These scripts will:

- build DREAMPlace under `DREAMPlace/build/`
- install DREAMPlace into `DREAMPlace/install/`
- run the selected 3D benchmarks

After a run, generated outputs are written under `results/`, and the temporary build tree is recreated under `DREAMPlace/build/`.

## Pipeline Flow

### `mol-analytical`

`src/place_3d/main.py`

1. Partition macros into upper and bottom dies
2. Generate 2D prototype placement
3. Refine bottom-die macro placement
4. Legalize bottom-die macros
5. Place upper-die macros
6. Legalize upper-die macros
7. Run cell placement with fixed macros
8. Run cell legalization

### `mol-tiling`

`src/place_3d/main_greedy.py`

1. Partition macros into upper and bottom dies
2. Place upper-die macros with greedy skyline
3. Place bottom-die macros with greedy skyline
4. Run cell placement with fixed macros
5. Run cell legalization

## Configuration

Configuration files are under `config/`.

Available configs:

- `or_3D.json`
- `or_3D_bp_quad.json`
- `or_3D_bp_be.json`
- `or_3D_bp_fe.json`
- `or_3D_swerv.json`

Config usage:

- `or_3D.json` is the default config for the common cases
- dedicated configs are used only for the special cases listed above

Key options:

- `partition_params.method`: `GNN`, `min-cut`, or `max-cut`
- `partition_params.GNN`: GNN training hyperparameters
- `enable_bottom_die_refinement`: enable or disable bottom-die refinement
- `macro_refine_params`: main-flow refinement settings
- `macro_place_params`: macro placement settings
- `macro_legalize_params`: legalization settings

## Output

Results are written under `results/`.

Typical output directories:

- `results/mol-analytical/`
- `results/mol-analytical-min-cut/`
- `results/mol-analytical-max-cut/`
- `results/mol-tiling/`
- `results/mol-tiling-min-cut/`
- `results/mol-tiling-max-cut/`

Typical final files:

- `mol_final/<design>_suffixed.def`
- `mol_final/<design>_legalized.png`
- `mol_final/mem_on_logic_results.csv`

These DEFs are the MoL placement outputs later consumed by `OpenROAD-3D` for routing, timing analysis, and thermal evaluation.
