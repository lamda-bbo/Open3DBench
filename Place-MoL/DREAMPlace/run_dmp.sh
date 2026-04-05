cd ../build
cmake ..
make -j 8
make -j 8 install
cd ../install

design_names=(
    "superblue1"
    "superblue3"
    "superblue4"
    "superblue5"
    "superblue7"
    "superblue10"
    "superblue16"
    "superblue18"
)
design_names=("superblue1")
for design in "${design_names[@]}"; do
    echo "Processing design: $design"
    python dreamplace/Placer.py "test/iccad2015.ot/${design}.json"
done