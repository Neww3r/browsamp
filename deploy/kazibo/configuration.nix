# NixOS module for a Kazibo VM: nginx serves the Vite build (npm run build → dist/),
# copied to /var/www/browsamp. Kazibo terminates HTTPS, which the browser requires for
# audio input (getUserMedia) and AudioWorklets.
{ pkgs, ... }:
{
  services.nginx = {
    enable = true;
    recommendedGzipSettings = true;
    recommendedOptimisation = true;
    virtualHosts."browsamp" = {
      default = true;
      root = "/var/www/browsamp";
      locations."/" = {
        tryFiles = "$uri /index.html";
        extraConfig = ''
          add_header Cache-Control "no-cache";
        '';
      };
      # Hashed bundles and rendered art never change under the same name.
      locations."/assets/".extraConfig = ''
        add_header Cache-Control "public, max-age=31536000, immutable";
      '';
      locations."/art/".extraConfig = ''
        add_header Cache-Control "public, max-age=86400";
      '';
    };
  };

  systemd.tmpfiles.rules = [ "d /var/www/browsamp 0755 root root -" ];
  networking.firewall.allowedTCPPorts = [ 80 ];
}
