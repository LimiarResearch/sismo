#!/bin/sh
# Builds htm.core (htm-community/htm.core, commit 96309f4) for the HTM of the benchmark, with the dependencies pinned to commits and
# placed where htm.core itself looks for local copies (build/Thirdparty/<name>), without downloading anything during the build.
# Installs the "htm" package into the given Python. Usage: data/build_htm.sh <benchmark_python> <work_folder>
set -e
PY=$1; W=$2
[ -n "$PY" ] && [ -n "$W" ] || { echo "usage: $0 <python> <folder>" >&2; exit 1; }
for tool in git cmake g++ curl unzip uv sha256sum; do
  command -v "$tool" > /dev/null 2>&1 || { echo "build_htm.sh: $tool not found" >&2; exit 1; }
done
mkdir -p "$W" && cd "$W"
fetch() { # repository, commit, destination
  [ -d "$3/.git" ] || { git init -q "$3" && git -C "$3" remote add origin "$1"; }
  git -C "$3" fetch -q --depth 1 origin "$2" && git -C "$3" checkout -q FETCH_HEAD
}
fetch https://github.com/htm-community/htm.core 96309f4969b1488ede172b3eec649dcb9702557d htm.core
TP=htm.core/build/Thirdparty; mkdir -p $TP
fetch https://github.com/USCiLab/cereal ebef1e929807629befafbb2918ea1a08c7194554 $TP/cereal
fetch https://github.com/yhirose/cpp-httplib 5c1a34e766817cf0865ca8bc5af5edeb0f9b2df4 $TP/cpp-httplib
fetch https://github.com/kerukuro/digestpp 4beae7541f5c280389898ae6e6111028852f466a $TP/digestpp
fetch https://gitlab.com/libeigen/eigen.git 3147391d946bb4b6c68edd901f2add6ac1f31f8c $TP/eigen
fetch https://github.com/google/googletest b514bdc898e2951020cbdca1304b75f5950d1f59 $TP/gtest
fetch https://github.com/yaml/libyaml 2c891fc7a770e8ba2fec34fc6b545c672beb37e6 $TP/libyaml
fetch https://github.com/wichtounet/mnist 3b65c35ede53b687376c4302eeb44fdf76e0129b $TP/mnist
[ -f sqlite.zip ] || curl -sSL -o sqlite.zip https://www.sqlite.org/2024/sqlite-amalgamation-3470000.zip
echo "2842fddbb1cc33f66c7da998a57535f14a6bfee159676a07bb4bf3e59375d93e  sqlite.zip" | sha256sum -c -
rm -rf $TP/sqlite3 && mkdir -p $TP/sqlite3 && cd $TP/sqlite3 && unzip -q -o ../../../../sqlite.zip && mv sqlite-amalgamation-3470000/* . && rmdir sqlite-amalgamation-3470000 && cd - > /dev/null
uv pip install -q --python "$PY" "pybind11==3.1.0" "scikit-build-core==1.1.1" "build==1.6.1"
cd htm.core
cmake -S . -B build/cmake -DBINDING_BUILD=CPP_Only -DCMAKE_BUILD_TYPE=Release > ../cmake_config.log
cmake --build build/cmake --target htm_core htm_core_shared hello dynamic_hello napi_hello napi_hello_database mnist_sp rest_server rest_client -j 4 > ../cmake_build.log
cmake -DCMAKE_INSTALL_LOCAL_ONLY=1 -P build/cmake/src/cmake_install.cmake > ../cmake_install.log
rm -f dist/htm-*.whl
"$PY" -m build --wheel --no-isolation > ../wheel.log
set -- dist/htm-2.2.0-*.whl
[ $# -eq 1 ] && [ -f "$1" ] || { echo "build_htm.sh: expected one htm-2.2.0 wheel in htm.core/dist, found: $*" >&2; exit 1; }
WHEEL=$1
uv pip install -q --python "$PY" "$WHEEL"
"$PY" -c "from htm.bindings.algorithms import SpatialPooler; print('htm installed')"
echo "wheel: $W/htm.core/$WHEEL"
