# NixOS module for the Kazibo VM. The site is the web build published as a GitHub release
# asset (npm run build → dist/ → browsamp-dist.tar.gz), fetched and pinned by hash.
# Kazibo terminates HTTPS, which browsers require for audio input and AudioWorklets.
#
# To ship a new version: publish a new release asset, update `version` and `hash`
# (sha256-$(openssl dgst -sha256 -binary browsamp-dist.tar.gz | base64)), redeploy.
{ pkgs, ... }:
let
  version = "v2.1.1";
  site = pkgs.runCommand "browsamp-site-${version}" { } ''
    mkdir -p $out
    tar -xzf ${
      pkgs.fetchurl {
        url = "https://github.com/Neww3r/browsamp/releases/download/${version}/browsamp-dist.tar.gz";
        hash = "sha256-dgm8kIb1NJo6QlhRJw/ozBxT2slM104QWc15ITG9C+Y=";
      }
    } -C $out
  '';
in
{
  services.nginx = {
    enable = true;
    recommendedGzipSettings = true;
    recommendedOptimisation = true;
    virtualHosts.default = {
      default = true;
      root = site;
      locations."/" = {
        tryFiles = "$uri /index.html";
        extraConfig = ''
          add_header Cache-Control "no-cache";
        '';
      };
      # Hashed bundles never change under the same name.
      locations."/assets/".extraConfig = ''
        add_header Cache-Control "public, max-age=31536000, immutable";
      '';
      locations."/art/".extraConfig = ''
        add_header Cache-Control "public, max-age=86400";
      '';
    };
  };

  networking.firewall.allowedTCPPorts = [ 80 ];
}
