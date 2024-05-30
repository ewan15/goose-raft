{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "example-shell";

  buildInputs = [
    pkgs.python3
    pkgs.python311Packages.offtrac
  ];

  shellHook = ''
    echo "welcome to raft shell :o"
  '';
}

