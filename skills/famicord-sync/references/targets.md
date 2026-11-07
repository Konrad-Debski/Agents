# Target repositories and websites

## Repository registry

This is the default target allowlist. Folder names are hints; Git remote identity is authoritative. Clone missing selected repositories from these URLs.

- https://github.com/empressia-co/pbkm-multisite
- https://github.com/empressia-co/wordpress-biogenis.ro
- https://github.com/empressia-co/wordpress-nabassaite.lv
- https://github.com/empressia-co/wordpress-famicord.ch
- https://github.com/empressia-co/wordpress-famicord.lu
- https://github.com/empressia-co/wordpress-krio.hu
- https://github.com/empressia-co/wordpress-sevibe.es
- https://github.com/empressia-co/wordpress-kordonkanibankasi.com
- https://github.com/empressia-co/famicord.com
- https://github.com/empressia-co/ir.famicord.com
- https://github.com/empressia-co/wordpress-famicordcryobank.ch
- https://github.com/empressia-co/smartcells.ae
- https://github.com/empressia-co/smartcells.com
- https://github.com/empressia-co/sorgente.com
- https://github.com/empressia-co/pupecnikovakrev.cz
- https://github.com/empressia-co/smartcells.com.hk
- https://github.com/empressia-co/cakam-babatko.sk
- https://github.com/empressia-co/crioestaminal.pt

## Website addresses

Use this mapping for website links and live checks. Repository names are not always public domains. Famicord and IR use the staging addresses below for this workflow; label them as staging, not production. These URLs do not establish FTP document roots or authorize deployments.

| Repository in empressia-co | Website URL | Environment |
| --- | --- | --- |
| pbkm-multisite | https://www.pbkm.pl | Production |
| wordpress-biogenis.ro | https://biogenis.ro | Production |
| wordpress-nabassaite.lv | https://cilmessunubanka.lv | Production |
| wordpress-famicord.ch | https://famicord.ch | Production |
| wordpress-famicord.lu | https://famicord.lu | Production |
| wordpress-krio.hu | https://krio.hu | Production |
| wordpress-sevibe.es | https://sevibe.es | Production |
| wordpress-kordonkanibankasi.com | https://kordonkanibankasi.com | Production |
| famicord.com | https://stage.famicord.com | Staging |
| ir.famicord.com | https://stageir.famicord.com | Staging |
| wordpress-famicordcryobank.ch | https://famicordcryobank.ch | Production |
| smartcells.ae | https://smartcells.ae | Production |
| smartcells.com | https://smartcells.com | Production |
| sorgente.com | https://sorgente.com | Production |
| pupecnikovakrev.cz | https://pupecnikovakrev.cz | Production |
| smartcells.com.hk | https://smartcells.com.hk | Production |
| cakam-babatko.sk | https://cakam-babatko.sk/ | Production |
| crioestaminal.pt | https://crioestaminal.pt | Staging |

## Staging server root exceptions

`stage.famicord.com` and `stageir.famicord.com` run on a different server from the other companies and use staging environments with autodeploy. Both use `/autostage/` as the WordPress root. Do not include `/public_html/` or a domain directory in their server paths.

| Repository | Website | Server WordPress root |
| --- | --- | --- |
| famicord.com | https://stage.famicord.com | `/autostage/` |
| ir.famicord.com | https://stageir.famicord.com | `/autostage/` |

For example, the Regions directory for either staging server is `/autostage/wp-content/themes/starter-empressia/resources/components/Regions/`. Keep the local repository path distinct for each company. Account for their known autodeploy when disclosing merge-triggered deployments before publication confirmation.
