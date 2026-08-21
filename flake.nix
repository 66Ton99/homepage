{
  description = "66ton99.org.ua — static site generators";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs =
    { self, nixpkgs }:
    let
      # The generators are pure CLI scripts, so the same shell works everywhere.
      systems = [
        "aarch64-darwin"
        "x86_64-darwin"
        "aarch64-linux"
        "x86_64-linux"
      ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      # `nix develop` gets you the exact PHP and Node that CI runs, which is
      # what keeps the committed site/ reproducible: the build check compares
      # generator output byte for byte, so the interpreter version is part of
      # the contract.
      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [
            pkgs.php85 # gd + freetype + mbstring, all needed by the generators
            pkgs.nodejs_24
          ];
        };
      });
    };
}
