{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        tglogging = pkgs.python3Packages.buildPythonPackage {
          pname = "tglogging";
          version = "unstable";
          pyproject = true;
          src = pkgs.fetchFromGitHub {
            owner = "licryle";
            repo = "tglogging";
            rev = "v0.0.5";
            hash = "sha256-gO+1E38lPL+9HyIJOEcSq8SHPcloYxMY/WJEf3zGddo=";
          };
          build-system = [
            pkgs.python3Packages.setuptools
          ];
        };

        pythonEnv = pkgs.python3.withPackages (ps: [
          tglogging
          ps.pytest
          ps.requests
          ps.python-dotenv
        ]);
      in {
        devShells.default = pkgs.mkShell {
          packages = [
            pythonEnv

            pkgs.gitleaks
            pkgs.podman
          ];
        };
      });
}