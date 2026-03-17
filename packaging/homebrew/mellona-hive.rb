# typed: strict
# frozen_string_literal: true

# Formula for mellona-hive.
class MellonaHive < Formula
  include Language::Python::Virtualenv

  desc "Git-backed control plane for autonomous agent work"
  homepage "https://github.com/intertwine/hive-orchestrator"
  url "https://files.pythonhosted.org/packages/19/8c/737ae523b2b7ca09ee6a63674d1ad29443665a36daef4a1a9f8568d60bf3/mellona_hive-2.2.1.tar.gz"
  sha256 "6934158eaccc5f2808387105724967e588ac42b9b2a4e13588f2253c92d2117d"
  license "MIT"

  depends_on "libyaml"
  depends_on "python@3.13"

  resource "pyyaml" do
    on_arm do
      url "https://files.pythonhosted.org/packages/b1/16/95309993f1d3748cd644e02e38b75d50cbc0d9561d21f390a76242ce073f/pyyaml-6.0.3-cp313-cp313-macosx_11_0_arm64.whl"
      sha256 "2283a07e2c21a2aa78d9c4442724ec1eb15f5e42a723b99cb3d822d48f5f7ad1"
    end
    on_intel do
      url "https://files.pythonhosted.org/packages/d1/11/0fd08f8192109f7169db964b5707a2f1e8b745d4e239b784a5a1dd80d1db/pyyaml-6.0.3-cp313-cp313-macosx_10_13_x86_64.whl"
      sha256 "8da9669d359f02c0b91ccc01cac4a67f16afec0dac22c2ad09f46bee0697eba8"
    end
  end

  resource "certifi" do
    url "https://files.pythonhosted.org/packages/9a/3c/c17fb3ca2d9c3acff52e30b309f538586f9f5b9c9cf454f3845fc9af4881/certifi-2026.2.25-py3-none-any.whl"
    sha256 "027692e4402ad994f1c42e52a4997a9763c646b73e4096e4d5d6db8af1d6f0fa"
  end

  resource "charset-normalizer" do
    url "https://files.pythonhosted.org/packages/1e/1d/4fdabeef4e231153b6ed7567602f3b68265ec4e5b76d6024cf647d43d981/charset_normalizer-3.4.6-cp313-cp313-macosx_10_13_universal2.whl"
    sha256 "11afb56037cbc4b1555a34dd69151e8e069bee82e613a73bef6e714ce733585f"
  end

  resource "hatchling" do
    url "https://files.pythonhosted.org/packages/d3/8a/44032265776062a89171285ede55a0bdaadc8ac00f27f0512a71a9e3e1c8/hatchling-1.29.0-py3-none-any.whl"
    sha256 "50af9343281f34785fab12da82e445ed987a6efb34fd8c2fc0f6e6630dbcc1b0"
  end

  resource "idna" do
    url "https://files.pythonhosted.org/packages/0e/61/66938bbb5fc52dbdf84594873d5b51fb1f7c7794e9c0f5bd885f30bc507b/idna-3.11-py3-none-any.whl"
    sha256 "771a87f49d9defaf64091e6e6fe9c18d4833f140bd19464795bc32d966ca37ea"
  end

  resource "packaging" do
    url "https://files.pythonhosted.org/packages/b7/b9/c538f279a4e237a006a2c98387d081e9eb060d203d8ed34467cc0f0b9b53/packaging-26.0-py3-none-any.whl"
    sha256 "b36f1fef9334a5588b4166f8bcd26a14e521f2b55e6b9de3aaa80d3ff7a37529"
  end

  resource "pathspec" do
    url "https://files.pythonhosted.org/packages/ef/3c/2c197d226f9ea224a9ab8d197933f9da0ae0aac5b6e0f884e2b8d9c8e9f7/pathspec-1.0.4-py3-none-any.whl"
    sha256 "fb6ae2fd4e7c921a165808a552060e722767cfa526f99ca5156ed2ce45a5c723"
  end

  resource "pluggy" do
    url "https://files.pythonhosted.org/packages/54/20/4d324d65cc6d9205fabedc306948156824eb9f0ee1633355a8f7ec5c66bf/pluggy-1.6.0-py3-none-any.whl"
    sha256 "e920276dd6813095e9377c0bc5566d94c932c33b27a3e3945d8389c374dd4746"
  end

  resource "python-dotenv" do
    url "https://files.pythonhosted.org/packages/0b/d7/1959b9648791274998a9c3526f6d0ec8fd2233e4d4acce81bbae76b44b2a/python_dotenv-1.2.2-py3-none-any.whl"
    sha256 "1d8214789a24de455a8b8bd8ae6fe3c6b69a5e3d64aa8a8e5d68e694bbcb285a"
  end

  resource "python-frontmatter" do
    url "https://files.pythonhosted.org/packages/49/87/3c8da047b3ec5f99511d1b4d7a5bc72d4b98751c7e78492d14dc736319c5/python_frontmatter-1.1.0-py3-none-any.whl"
    sha256 "335465556358d9d0e6c98bbeb69b1c969f2a4a21360587b9873bfc3b213407c1"
  end

  resource "requests" do
    url "https://files.pythonhosted.org/packages/1e/db/4254e3eabe8020b458f1a747140d32277ec7a271daf1d235b70dc0b4e6e3/requests-2.32.5-py3-none-any.whl"
    sha256 "2462f94637a34fd532264295e186976db0f5d453d1cdd31473c85a6a161affb6"
  end

  resource "trove-classifiers" do
    url "https://files.pythonhosted.org/packages/bb/4a/2e5583e544bc437d5e8e54b47db87430df9031b29b48d17f26d129fa60c0/trove_classifiers-2026.1.14.14-py3-none-any.whl"
    sha256 "1f9553927f18d0513d8e5ff80ab8980b8202ce37ecae0e3274ed2ef11880e74d"
  end

  resource "urllib3" do
    url "https://files.pythonhosted.org/packages/39/08/aaaad47bc4e9dc8c725e68f9d04865dbcb2052843ff09c97b08904852d84/urllib3-2.6.3-py3-none-any.whl"
    sha256 "bf272323e553dfb2e87d9bfd225ca7b0f467b919d7bbd355436d3fd37cb0acd4"
  end

  def install
    virtualenv_create(libexec, "python3.13")
    python = Formula["python@3.13"].opt_bin/"python3.13"

    resources.each do |resource|
      wheel = buildpath/File.basename(resource.url)
      cp resource.cached_download, wheel
      system python, "-m", "pip", "--python=#{libexec/"bin/python"}", "install", "--no-deps", wheel
    end

    system libexec/"bin/python", "-m", "pip", "install", "--no-deps", "--no-build-isolation", buildpath
    bin.install_symlink libexec/"bin/hive"
  end

  test do
    assert_match "\"ok\": true", shell_output("#{bin}/hive doctor --json")
  end
end
