# Proxmox VE — deploy landmine pack

Treat every version/default below as a hypothesis to verify against the live
cluster. `pveversion` first; runtime wins.

## Auth (the #1 silent failure)
- API token effective perms = **backing user's ACL ∩ token's ACL** when
  `privsep=1` (the default). A token 403s unless BOTH the user and the token
  carry the role on the path. PROBE: `pveum user token list <user>@<realm>`,
  `pveum acl list`.
- The token secret is shown once and is unrecoverable. PAM (`@pam`) vs PVE
  (`@pve`) realm matters: only `root@pam` does node-level SSH ops.

## Guest type
- VM (`qm`/KVM) required for: Windows/BSD, GPU/PCIe VFIO passthrough,
  untrusted/internet-facing, a kernel ≠ host, live-migrate-with-RAM. LXC
  (`pct`) is the better default for trusted Linux services. Not a cosmetic
  choice.

## Image / cloud-init
- Do not interactively install from ISO. Download a cloud image → build ONE
  template → `qm clone`. Template build needs `--serial0 socket --vga serial0`
  (cloud images often require a serial console) and `--ostype l26`.
- Cloud-init drive: `qm set <id> --ide2 <storage>:cloudinit` — regenerated on
  every `qm start` from the ci* params.
- **Guest-agent trap:** stock cloud images ship WITHOUT qemu-guest-agent, so
  even with `--agent enabled=1` Proxmox cannot report the DHCP-assigned IP —
  the VM is "up" but unreachable. Fix via custom user-data that installs the
  agent, or use a static IP. PROBE: check the image / user-data.
- `cicustom` snippets must live in a storage with **snippets** content-type
  enabled, and there is still no REST endpoint to upload snippets. PROBE:
  `pvesh get /storage` (check content types).

## Placement / storage
- VMID is cluster-unique; node/storage/bridge names are per-cluster and will
  not exist elsewhere. PROBE: `pvesh get /nodes`, `pvesh get /storage`,
  `pvesh get /nodes/<n>/network`.
- `discard=on,ssd=1` are block-storage (LVM/ZFS/Ceph) flags only.

## IaC
- 2026: the bpg/proxmox Terraform provider is preferred for cloud-init
  reliability, SDN, and API-closeness; telmate remains the incumbent. Verify
  the provider/version actually in use — do not assert. PROBE:
  `terraform providers`, `terraform version`.

## Clone identity
- Template-from-booted-image needs machine-id / SSH-host-key / DHCP-lease
  cleanup or every clone collides on identity and the DHCP server hands out
  duplicate IPs.
