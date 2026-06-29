from src.common.config import Config
from src.execute.sandbox import Sandbox

ADD = "#include <iostream>\nint main(){int a,b;std::cin>>a>>b;std::cout<<a+b<<\"\\n\";}"


def test_compile_run(tmp_path):
    s = Sandbox(Config("config.yaml"))
    ok, cerr, binp = s.compile_cpp(ADD, tmp_path)
    assert ok and binp.exists(), cerr
    res = s.run([str(binp)], "2 3\n", time_limit=2, workdir=tmp_path)
    assert res["stdout"].split() == ["5"] and res["returncode"] == 0 and not res["timed_out"]


def test_compile_error_and_pragma_strip(tmp_path):
    s = Sandbox(Config("config.yaml"))
    ok, cerr, _ = s.compile_cpp("int main(){ this is not c++ }", tmp_path)
    assert not ok and cerr
    # an x86 target pragma (invalid on this ARM host) is stripped, so the code still compiles
    ok2, _, _ = s.compile_cpp("#pragma GCC target(\"avx2\")\n" + ADD, tmp_path)
    assert ok2
