# Place-LoL

`Place-LoL` is the LoL workspace in this repository. It is used for two things:

1. convert common 3D benchmark descriptions into LoL placer inputs
2. convert LoL placer outputs into standardized DEFs for `OpenROAD-3D`

## Getting Started

Pull the Docker image:

```bash
docker pull shiyunqi/open3dbench:place
```

Download `benchmarks_lol.tar.gz` from [Google Drive](https://drive.google.com/file/d/1wVYCgee2k7_1JdmV4o6Q4sIgDpoCkAcn/view?usp=sharing) and extract it under the current directory as `benchmarks/`:

```bash
cd Place-LoL
wget -O benchmarks_lol.tar.gz 'https://drive.google.com/uc?export=download&id=1wVYCgee2k7_1JdmV4o6Q4sIgDpoCkAcn'
tar -xzf benchmarks_lol.tar.gz
```

Download `binaries.tar.gz` from [Google Drive](https://drive.google.com/file/d/1QA2zse8jm1pD3OZ3aOPU08T47cPj-xSe/view?usp=sharing) and extract it under the current directory as `binaries/`:

```bash
cd Place-LoL
wget -O binaries.tar.gz 'https://drive.google.com/file/d/1QA2zse8jm1pD3OZ3aOPU08T47cPj-xSe/view?usp=sharing'
tar -xzf binaries.tar.gz
```

Enter the container from the `Place-LoL` root:

```bash
cd Place-LoL
./start_docker_place.sh
```

Inside the container, the `Place-LoL` root is mounted at `/workspace`.

## Files You Will Use

```text
Place-LoL/
├── start_docker_place.sh  # start the Docker environment
├── convert_input.sh       # generate LoL input files
├── convert_output.sh      # convert raw placer outputs into DEF files
├── convert_file.sh        # compatibility wrapper around the two scripts above
├── binaries/              # contest placer bundles, logs, raw outputs, and converted artifacts
├── test/                  # per-design JSON configs for default and inflated
├── benchmarks/            # shared benchmark resources used by conversion
├── cmake/                 # CMake helper files for the conversion stack
├── dreamplace/            # DREAMPlace-related source and support code used by the flow
└── thirdparty/            # third-party dependencies used by the conversion and placement stack
```

## Variants

Two benchmark variants are supported:

- `default`: the default converted netlist, consistent with the original LEF/DEF definitions
- `inflated`: each cell is expanded by 5 site widths during placement, i.e. `0.95um`, to create a looser layout; this corresponds to the `padded` setting described in the paper

Their JSON configs are stored under:

- [3D_input_default](./test/3D_input_default)
- [3D_input_inflated](./test/3D_input_inflated)

## Main Workflow

**Pre-generated artifacts are already included in this repository.**

The converted input files are already stored under <u>`binaries/converted_input/`</u>.

For each placer, the runtime logs and raw placement outputs are already stored under that placer's own <u>`logs/`</u> and <u>`output/`</u> directories.

The converted DEF files generated from those placer outputs are already stored under <u>`binaries/converted_output/`</u>.

**These DEF files can be used directly for evaluation in `OpenROAD-3D`.**

If you would like to reproduce this pipeline yourself, you can follow the workflow below.

### 1. Generate LoL inputs

```bash
cd Place-LoL
bash convert_input.sh <design|iccad_2022_all|iccad_2023_all> <default|inflated> 100
```

Here, the unit is `0.01um`, and the terminal size is set to `100`, which corresponds to a terminal size of `1um` and a spacing of `1um`.

Examples:

```bash
bash convert_input.sh aes default 100
bash convert_input.sh bp default 100
bash convert_input.sh iccad_2022_all default 100
bash convert_input.sh iccad_2023_all inflated 100
```

This generates standardized input files under `binaries/converted_input/`.

### 2. Run a LoL placer

Run the selected placer inside `binaries/iccad2022/` or `binaries/iccad2023/`.

As one concrete example, this repository includes the `tcad25` placer under [Place-LoL/binaries/iccad2023/tcad25](./binaries/iccad2023/tcad25), which we are authorized to redistribute by Dr. Yuxuan Zhao and Prof. Bei Yu. This placer corresponds to the paper [`Analytical Heterogeneous Die-to-Die 3D Placement with Macros`](https://ieeexplore.ieee.org/document/10637265/), and one of its detailed usage instructions can be found in the [`tcad25` README](./binaries/iccad2023/tcad25/README.md). We sincerely thank Dr. Yuxuan Zhao and Prof. Bei Yu for their authorization and support.

Examples:

```bash
cd Place-LoL/binaries/iccad2022/cadb1021
# run the vendor-provided placer using files under input/
```

```bash
cd Place-LoL/binaries/iccad2023/tcad25
bash run.sh default
```

At this stage, each placer is expected to write its raw results into its own `output/` directory.

### 3. Convert raw outputs into DEF

```bash
cd Place-LoL
bash convert_output.sh <design|iccad2022_all|iccad2023_all> <method> <default|inflated>
```

Examples:

```bash
bash convert_output.sh aes cadb1021 default
bash convert_output.sh iccad2022_all cadb1051 default
bash convert_output.sh iccad2023_all cadb1038 default
bash convert_output.sh iccad2023_all tcad25 inflated
```

This writes DEF files into `binaries/converted_output/`.

## Output Locations

- Generated LoL inputs:
  `binaries/converted_input/<variant>/`
- Converted DEF outputs:
  `binaries/converted_output/<variant>/<method>/`

Examples:

- `binaries/converted_input/default/aes.input`
- `binaries/converted_input/default/bp_quad.input`
- `binaries/converted_output/default/cadb1021/aes.def`
- `binaries/converted_output/default/cadb1038/ariane133.def`
- `binaries/converted_output/inflated/tcad25/bp.def`

## LoL Evaluation

`Place-LoL` does not do the final evaluation. After DEF conversion, the final outputs are:

```text
Place-LoL/binaries/converted_output/<variant>/<method>/*.def
```

These DEFs are later consumed by `OpenROAD-3D` for backend implementation and evaluation.

So the full flow is:

1. generate LoL inputs in `Place-LoL`
2. run a LoL placer in `binaries/`
3. convert outputs to DEF in `Place-LoL`
4. evaluate the DEFs in `OpenROAD-3D`

## Notes

- Contest-specific evaluator helpers and per-placer notes are documented under:
  [iccad2022](./binaries/iccad2022/README.md)
  [iccad2023](./binaries/iccad2023/README.md)
