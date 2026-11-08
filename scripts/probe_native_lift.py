"""Compile the exact upstream lift template with a fixed-array storage shim."""
from pathlib import Path
import hashlib,json,subprocess
import numpy as np
root=Path(__file__).resolve().parents[1]
header=root/"data/upstream-research/calibration-utils.hpp"
text=header.read_text();start=text.index("template<unsigned K> auto lift");end=text.index("// -------------------------------------------------------------- Flip",start)
template=text[start:end]
out=root/"data/processed/site02-native-lift";out.mkdir(parents=True,exist_ok=True)
prelude="""#include <array>
#include <cassert>
#include <iostream>
#include <iomanip>
using real=double;
#define EIGEN_ALIGN 0
#define Ensures(x) assert(x)
namespace Eigen {
template<class T,int N,int C,int A> struct Matrix {
 std::array<T,N> values;
 int rows() const {return N;}
 T& operator()(int i) {return values.at(i);}
};
}
"""
main="""int main(){double x,y;while(std::cin>>x>>y){auto a=lift<8>(x,y);for(int i=0;i<45;++i)std::cout<<std::setprecision(17)<<a(i)<<' ';std::cout<<std::endl;}}
"""
source=out/"upstream-lift-probe.cpp";source.write_text(prelude+template+main)
subprocess.run(["g++","-std=c++17","-O2",str(source),"-o",str(out/"lift-probe")],check=True)
points=[(0.,0.),(1.,1.),(2.,3.),(-.4,.7),(1.2,-.8)]
result=subprocess.check_output([str(out/"lift-probe")],input="".join(f"{x} {y}\n" for x,y in points),text=True)
actual=np.array([[float(v) for v in line.split()] for line in result.splitlines()])
exponents=[(degree-j,j) for degree in range(8,-1,-1) for j in range(degree+1)]
expected=np.array([[x**a*y**b for a,b in exponents] for x,y in points])
assert actual.shape==(5,45)
np.testing.assert_allclose(actual,expected,rtol=1e-13,atol=1e-14)
report={"status":"pass","cases":len(points),"terms":45,"ordering":"descending total degree; descending x exponent within degree","exponents":exponents,"max_absolute_error":float(np.max(np.abs(actual-expected))),"header_sha256":hashlib.sha256(header.read_bytes()).hexdigest(),"scope":"Exact upstream lift algorithm extracted; fixed-array Eigen storage shim only. Does not validate full native camera construction, inverse distortion or physical accuracy."}
(out/"result.json").write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
