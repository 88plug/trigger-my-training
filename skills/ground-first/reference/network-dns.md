# Network / DNS / TLS — cutover landmine pack

Treat every TTL/record/cert/firewall fact below as a hypothesis to verify
against the live resolvers and hosts. Query the AUTHORITATIVE nameserver and a
public resolver, not just your cache, before any change. ASK: is there a
rollback path that does not require the access you are about to change?

## DNS TTL before cutover
- Lower the record's TTL **before** the cutover — by at least the OLD TTL, so
  every resolver has expired the old value by switch time. Cutting over while
  the TTL is still high means clients keep hitting the old target for up to that
  TTL after you "switched". Raise the TTL back only after the cutover settles.
  PROBE: `dig +noall +answer <name> <type>` (current TTL),
  `dig @<authoritative-ns> <name> <type>`, `dig @1.1.1.1 <name>` (a public
  resolver's cached view).
- The effective TTL is the authoritative record's, but negative caching (SOA
  minimum) governs how long NXDOMAIN sticks — a typo'd record can cache absent.
  PROBE: `dig <name> SOA +noall +answer`.

## Dual-serve during propagation
- Keep BOTH old and new targets serving the full window; do not decommission the
  old backend until the full old-TTL window (plus a safety margin for
  misbehaving resolvers that ignore TTL) has elapsed. PROBE: poll
  `dig @<several resolvers> <name>` until all return the new value; confirm the
  new target actually answers (`curl -sS https://<name>/health --resolve
  <name>:443:<new-ip>`) before trusting DNS alone.
- CNAME-at-apex, dangling CNAME to a deprovisioned resource, and CDN/ALIAS
  flattening behave provider-specifically — verify the actual record type live.

## TLS chain / expiry
- A served leaf cert without its intermediate(s) validates in browsers that
  cache the intermediate but fails in fresh clients, curl, and many SDKs —
  "works in my browser" is a false negative. Verify the chain order is
  leaf → intermediate(s) and that intermediates are bundled. PROBE:
  `openssl s_client -connect <host>:443 -servername <host> </dev/null |
  openssl x509 -noout -dates -subject -issuer`;
  full chain: `openssl s_client -connect <host>:443 -servername <host>
  -showcerts </dev/null`.
- Check expiry AND that the renewal hook actually reloads the server — a renewed
  cert on disk that the running process never re-read still serves the expired
  one. After cutover, the cert must cover the NEW name/SAN. PROBE: confirm SANs
  (`... | openssl x509 -noout -text | grep -A1 'Subject Alternative Name'`),
  and that the service was reloaded after renewal.

## Firewall / remote lockout
- A bad `iptables`/`nftables` rule, a default-DROP without an established/SSH
  allow, or a security-group/NACL edit can lock you out of a remote host with no
  out-of-band path back. NEVER apply a connectivity-affecting change without a
  timed auto-revert staged FIRST. PROBE: `ss -tlnp` (what is actually
  listening), `iptables -S` / `nft list ruleset`, `ip route`.
- Stage the revert before the risky rule: e.g.
  `( sleep 120 && <restore-known-good> ) &` then apply; cancel it only after you
  have RE-VERIFIED access on a NEW connection (not the existing session, which
  may survive on an established-conntrack rule while new connections are blocked).
- Cloud security groups are stateful (return traffic auto-allowed); NACLs are
  stateless and need explicit ephemeral-port return rules — a one-sided NACL
  rule silently blackholes replies. PROBE: check both SG and NACL on the subnet.
- A firewall change plus a DNS cutover at once makes failures un-attributable —
  change one variable at a time.
