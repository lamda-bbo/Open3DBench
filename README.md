# Open3DBench v1.1

Official implementation of the paper ["Open3DBench: Open-Source Benchmark for 3D-IC Backend Implementation and PPA Evaluation"](https://arxiv.org/abs/2503.12946).

This repository provides an open-source benchmarking framework for 3D-IC placement and backend PPA evaluation. The current version focuses on two complementary flows:

- `MoL` (memory-on-logic): our in-repository placement flow for face-to-face 3D integration
- `LoL` (logic-on-logic): conversion, benchmarking, and backend evaluation for [ICCAD 2022 CAD Contest](https://www.iccad-contest.org/2022/) and [ICCAD 2023 CAD Contest](https://www.iccad-contest.org/2023/) placers

At the framework level, Open3DBench extends the original 2D `NanGate45` setup into `NanGate45_3D`, using duplicated metal layers to emulate a two-tier stacked routing environment within a unified 3D backend flow.

For `MoL`, we model HBTs as vias so that standard routing engines can handle them directly during backend implementation; for `LoL`, we model HBTs as virtual buffers and explicitly account for their locations during placement and legalization.

## About This Release

This repository is maintained as **Open3DBench v1.1**, a major updated release based on the original [Open3DBench](https://github.com/lamda-bbo/Open3DBench) repository.

- `v1.0` contributors:
  - `Yunqi Shi, maintainer (shiyq@lamda.nju.edu.cn)`
  - `Chengrui Gao, MoL Placement developer (gaocr@lamda.nju.edu.cn)`
- `v1.1` contributors:
  - `Yunqi Shi, maintainer (shiyq@lamda.nju.edu.cn)`
  - `Chengrui Gao, MoL Placement contributor (gaocr@lamda.nju.edu.cn)`
  - `Peng Xie, developer (xiep@lamda.nju.edu.cn)`

Users who would like to refer to the earlier release line should consult the corresponding `v1.0` snapshot or tag when it is published alongside this repository. This `v1.1` branch/release is intended to be the main entry point for the updated framework.

## What's New In This Version

Compared with earlier versions of Open3DBench, the current release makes two major updates.

First, the `MoL` placement framework has been refactored and improved. The placement-centric codebase under `Place-MoL` now provides a clearer workflow for partitioning, macro placement, legalization, and bottom-die cell placement, with support for both `mol-analytical` and `mol-tiling`.

Second, the repository now supports full backend PPA evaluation and benchmarking for the [ICCAD 2022 CAD Contest](https://www.iccad-contest.org/2022/) and [ICCAD 2023 CAD Contest](https://www.iccad-contest.org/2023/) LoL binaries. The `Place-LoL` and `OpenROAD-3D` directories together cover LoL input conversion, contest-binary execution, output-to-DEF conversion, and complete backend evaluation.

## Repository Structure

This repository is organized around three top-level working directories:

```text
Open3DBench/
├── Place-MoL/     # MoL placement flow
│   ├── benchmarks/
│   ├── config/
│   ├── scripts/
│   └── src/
├── Place-LoL/     # LoL input/output conversion and contest-binary benchmarking
│   ├── benchmarks/
│   ├── binaries/
│   ├── test/
│   ├── convert_input.sh
│   └── convert_output.sh
└── OpenROAD-3D/   # backend PPA evaluation for both MoL and LoL
    └── flow/
        ├── run_lol_iccad2022.sh
        ├── run_lol_iccad2023.sh
        ├── run_mol_analytical.sh
        ├── run_mol_tiling.sh
        └── export_mol_defs_from_place_mol.sh
```

### `Place-MoL`

[Place-MoL](/home/xiaosi/hdd/shiyq/Open3DBench-release/Place-MoL/README.md) contains the memory-on-logic placement flow. It takes 3D benchmark cases, runs macro partitioning and placement, legalizes the layout, performs bottom-die cell placement, and writes final DEF results that can later be evaluated in `OpenROAD-3D`.

The main supported methods are:

- `mol-analytical`: analytical pseudo-3D macro placement that prioritizes wirelength
- `mol-tiling`: tiling-based macro placement that prioritizes layout regularity

Typical outputs are written under:

- `Place-MoL/results/mol-analytical/mol_final/`
- `Place-MoL/results/mol-tiling/mol_final/`

### `Place-LoL`

[Place-LoL](/home/xiaosi/hdd/shiyq/Open3DBench-release/Place-LoL/README.md) is the logic-on-logic workspace. It converts common benchmark descriptions into the input format expected by ICCAD contest placers, collects the raw placer outputs, and converts them into standardized DEF files for backend evaluation.

It supports two benchmark variants:

- `default`: consistent with the original LEF/DEF definitions
- `inflated`: corresponds to the `padded` setting in the paper

It also includes evaluation support for ICCAD 2022 and ICCAD 2023 contest placers, including the redistributed `tcad25` binary used in the ICCAD 2023 benchmarking flow.

Typical generated artifacts are written under:

- `Place-LoL/binaries/converted_input/`
- `Place-LoL/binaries/converted_output/`

### `OpenROAD-3D`

[OpenROAD-3D](/home/xiaosi/hdd/shiyq/Open3DBench-release/OpenROAD-3D/README.md) contains the complete backend implementation and PPA evaluation flow. It consumes DEF files produced by `Place-MoL` or `Place-LoL`, then runs OpenROAD-based backend stages and HotSpot thermal evaluation.

This directory supports:

- LoL evaluation using DEFs from `Place-LoL/binaries/converted_output/`
- MoL evaluation using either packaged reproducibility DEFs or custom DEFs exported from `Place-MoL`

Final logs and evaluation artifacts are archived under `OpenROAD-3D/flow/logs/`.

## MoL Workflow

The typical `MoL` workflow is:

1. Prepare the benchmark data in `Place-MoL/benchmarks/`.
2. Run `mol-analytical` or `mol-tiling` in `Place-MoL`.
3. Generate final DEFs under `Place-MoL/results/<method>/mol_final/`.
4. Use `OpenROAD-3D` to evaluate those DEFs.

For concrete commands, configuration files, and evaluation options, please refer to [Place-MoL](/home/xiaosi/hdd/shiyq/Open3DBench-release/Place-MoL/README.md) and [OpenROAD-3D](/home/xiaosi/hdd/shiyq/Open3DBench-release/OpenROAD-3D/README.md).

## LoL Workflow

The typical `LoL` workflow is:

1. Prepare `Place-LoL/benchmarks/` and `Place-LoL/binaries/`.
2. Convert benchmark cases into LoL placer inputs.
3. Run the selected ICCAD contest placer.
4. Convert raw placer outputs into standardized DEF files.
5. Evaluate those DEFs in `OpenROAD-3D`.

If you use the pre-generated LoL artifacts already included in this repository, you can skip the LoL reproduction steps and directly run the backend evaluation.

For concrete commands, benchmark variants, supported placers, and evaluation scripts, please refer to [Place-LoL](/home/xiaosi/hdd/shiyq/Open3DBench-release/Place-LoL/README.md) and [OpenROAD-3D](/home/xiaosi/hdd/shiyq/Open3DBench-release/OpenROAD-3D/README.md).

## Acknowledgments

In the new release, we sincerely thank the following people, listed in alphabetical order, for generously sharing winning contest binaries for our evaluation. Many of them also provided highly specific help and invested substantial time and effort in supporting this work.

- `Prof. Bei Yu (byu@cse.cuhk.edu.hk)`
- `Yan-Jen Chen (yjchen@eda.ee.ntu.edu.tw)`
- `Dr. Peiyu Liao (enzoliao95@gmail.com)`
- `Liang Xiao (lxiao23@cse.cuhk.edu.hk)`
- `Xueyan Zhao (zhaoxueyan21b@ict.ac.cn)`
- `Dr. Yuxuan Zhao (yxzhao21@cse.cuhk.edu.hk)`

We also especially thank:

- `Yuhao Ji (1155224012@link.cuhk.edu.hk)`
- `Prof. Zhiang Wang (zhiangwang@fudan.edu.cn)`

for their discussions and help during the development of the new release.

## Citation

```bibtex
@article{shi2025open3dbench,
      title={{Open3DBench}: Open-Source Benchmark for {3D-IC} Backend Implementation and {PPA} Evaluation},
      author={Yunqi Shi and Chengrui Gao and Wanqi Ren and Siyuan Xu and Ke Xue and Mingxuan Yuan and Chao Qian and Zhi-Hua Zhou},
      year={2025},
      journal={arXiv preprint}
}
```
