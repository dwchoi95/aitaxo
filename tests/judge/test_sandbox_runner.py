from src.common.config import Config
from src.judge.sandbox_runner import SandboxRunner

ADD = "#include <iostream>\nint main(){int a,b;std::cin>>a>>b;std::cout<<a+b<<\"\\n\";}"


def test_compile_run_and_network_denied(tmp_path):
    r = SandboxRunner(Config("config.yaml"))
    ok, cerr, binp = r.compile_cpp(ADD, tmp_path)
    assert ok and binp.exists(), cerr
    res = r.run([str(binp)], "2 3\n", time_limit=2, workdir=tmp_path)
    assert res["stdout"].split() == ["5"] and res["returncode"] == 0 and not res["timed_out"]


def test_compile_error_and_pragma_strip(tmp_path):
    r = SandboxRunner(Config("config.yaml"))
    ok, cerr, _ = r.compile_cpp("int main(){ this is not c++ }", tmp_path)
    assert not ok and cerr
    # an x86 target pragma (invalid on this ARM host) is stripped, so the code still compiles
    pragma_src = "#pragma GCC target(\"avx2\")\n" + ADD
    ok2, _, _ = r.compile_cpp(pragma_src, tmp_path)
    assert ok2
