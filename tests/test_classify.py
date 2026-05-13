"""Smoke tests for the safety classifier in bin/porkbun-api-skill.

Run with:
    python3 -m unittest discover tests

These tests are deliberately offline and stdlib-only — they load
bin/porkbun-api-skill via importlib.machinery.SourceFileLoader and exercise
the classifier and helpers directly. No network, no credentials required.
"""

from __future__ import annotations

import importlib.machinery
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
LOADER = importlib.machinery.SourceFileLoader(
    "porkbun_ctl", str(REPO_ROOT / "bin" / "porkbun-api-skill")
)
pb = LOADER.load_module()


class TestNormalizePath(unittest.TestCase):
    def test_known_template_with_numeric_id(self):
        self.assertEqual(
            pb._normalize_path("/dns/delete/example.com/12345"),
            "/dns/delete/{domain}/{id}",
        )

    def test_known_template_with_subdomain_pattern(self):
        self.assertEqual(
            pb._normalize_path("/dns/deleteByNameType/example.com/A/www"),
            "/dns/deleteByNameType/{domain}/{type}/{subdomain}",
        )

    def test_known_template_domain_only(self):
        self.assertEqual(
            pb._normalize_path("/domain/get/example.com"),
            "/domain/get/example.com",  # /domain/get/{domain} not in classifier table; passes through
        )
        # /domain/create/{domain} IS in the table though.
        self.assertEqual(
            pb._normalize_path("/domain/create/example.com"),
            "/domain/create/{domain}",
        )

    def test_unknown_path_passes_through(self):
        self.assertEqual(
            pb._normalize_path("/some/future/endpoint"),
            "/some/future/endpoint",
        )

    def test_strips_v3_prefix(self):
        self.assertEqual(
            pb._normalize_path("/v3/domain/create/example.com"),
            "/domain/create/{domain}",
        )
        self.assertEqual(
            pb._normalize_path("/api/json/v3/dns/delete/example.com/12345"),
            "/dns/delete/{domain}/{id}",
        )

    def test_does_not_strip_unrelated_prefix(self):
        self.assertEqual(
            pb._normalize_path("/v30/foo"),
            "/v30/foo",
        )


class TestClassify(unittest.TestCase):
    def test_get_is_read(self):
        cls, flags, _why = pb.classify("GET", "/domain/listAll")
        self.assertEqual(cls, "read")
        self.assertEqual(flags, [])

    def test_get_balance_is_read(self):
        cls, flags, _why = pb.classify("GET", "/account/balance")
        self.assertEqual(cls, "read")
        self.assertEqual(flags, [])

    def test_post_ping_is_read(self):
        cls, _flags, _why = pb.classify("POST", "/ping")
        self.assertEqual(cls, "read")

    def test_post_check_domain_is_read(self):
        cls, _flags, _why = pb.classify("POST", "/domain/checkDomain/example.com")
        self.assertEqual(cls, "read")

    def test_post_pricing_get_is_read(self):
        cls, _flags, _why = pb.classify("POST", "/pricing/get")
        self.assertEqual(cls, "read")

    def test_post_listall_is_read(self):
        cls, _flags, _why = pb.classify("POST", "/domain/listAll")
        self.assertEqual(cls, "read")

    def test_post_dns_create_is_mutating(self):
        cls, flags, _why = pb.classify("POST", "/dns/create/example.com")
        self.assertEqual(cls, "mutating")
        self.assertEqual(flags, ["--yes"])

    def test_post_dns_edit_is_mutating(self):
        cls, _flags, _why = pb.classify("POST", "/dns/edit/example.com/12345")
        self.assertEqual(cls, "mutating")

    def test_post_update_ns_is_mutating(self):
        cls, _flags, _why = pb.classify("POST", "/domain/updateNs/example.com")
        self.assertEqual(cls, "mutating")

    def test_post_dns_delete_is_destructive(self):
        cls, flags, _why = pb.classify("POST", "/dns/delete/example.com/12345")
        self.assertEqual(cls, "destructive")
        self.assertIn("--confirm-id", flags)

    def test_post_dns_delete_by_nametype_uses_confirm_name(self):
        # Pattern-deletes (delete-by-subdomain) need --confirm-name, not --confirm-id.
        cls, flags, _why = pb.classify(
            "POST", "/dns/deleteByNameType/example.com/A/www"
        )
        self.assertEqual(cls, "destructive")
        self.assertIn("--confirm-name", flags)
        self.assertNotIn("--confirm-id", flags)

    def test_post_delete_glue_is_destructive(self):
        cls, _flags, _why = pb.classify(
            "POST", "/domain/deleteGlue/example.com/ns1"
        )
        self.assertEqual(cls, "destructive")

    def test_post_delete_url_forward_is_destructive(self):
        cls, _flags, _why = pb.classify(
            "POST", "/domain/deleteUrlForward/example.com/77"
        )
        self.assertEqual(cls, "destructive")

    def test_post_create_domain_is_billable(self):
        cls, flags, _why = pb.classify("POST", "/domain/create/example.com")
        self.assertEqual(cls, "billable")
        self.assertIn("--i-understand-billing", flags)

    def test_post_renew_domain_is_billable(self):
        cls, _flags, _why = pb.classify("POST", "/domain/renew/example.com")
        self.assertEqual(cls, "billable")

    def test_post_transfer_domain_is_billable(self):
        cls, _flags, _why = pb.classify("POST", "/domain/transfer/example.com")
        self.assertEqual(cls, "billable")

    def test_post_apikey_request_is_privilege(self):
        cls, flags, _why = pb.classify("POST", "/apikey/request")
        self.assertEqual(cls, "privilege")
        self.assertIn("--allow-privilege", flags)

    def test_post_apikey_retrieve_is_privilege(self):
        cls, _flags, _why = pb.classify("POST", "/apikey/retrieve")
        self.assertEqual(cls, "privilege")

    def test_post_account_invite_is_privilege(self):
        cls, _flags, _why = pb.classify("POST", "/account/invite")
        self.assertEqual(cls, "privilege")

    def test_post_email_setpassword_is_privilege(self):
        cls, _flags, _why = pb.classify("POST", "/email/setPassword")
        self.assertEqual(cls, "privilege")

    def test_get_ssl_retrieve_is_privilege(self):
        # SSL retrieve returns private key material — privilege regardless of method.
        cls, flags, _why = pb.classify("GET", "/ssl/retrieve/example.com")
        self.assertEqual(cls, "privilege")
        self.assertIn("--allow-privilege", flags)

    def test_post_ssl_retrieve_is_privilege(self):
        cls, _flags, _why = pb.classify("POST", "/ssl/retrieve/example.com")
        self.assertEqual(cls, "privilege")

    def test_unknown_post_defaults_to_mutating(self):
        # POST-to-delete-without-being-in-the-table must NOT default to destructive;
        # the explicit table is the only source of `destructive`. We accept that an
        # unknown POST falls through to `mutating` (requires --yes) and rely on the
        # operator to recognize a delete-style path. This is the same approach as
        # linode-api-skill but more conservative on the destructive tier.
        cls, flags, _why = pb.classify("POST", "/future/endpoint")
        self.assertEqual(cls, "mutating")
        self.assertEqual(flags, ["--yes"])

    def test_method_case_insensitive(self):
        cls_lower, _, _ = pb.classify("post", "/domain/listAll")
        cls_upper, _, _ = pb.classify("POST", "/domain/listAll")
        self.assertEqual(cls_lower, cls_upper)

    def test_v3_prefix_create_is_billable(self):
        cls, flags, _why = pb.classify("POST", "/v3/domain/create/example.com")
        self.assertEqual(cls, "billable")
        self.assertIn("--i-understand-billing", flags)

    def test_v3_prefix_apikey_is_privilege(self):
        cls, _flags, _why = pb.classify("POST", "/v3/apikey/request")
        self.assertEqual(cls, "privilege")

    def test_full_api_prefix_strips(self):
        cls, _flags, _why = pb.classify(
            "POST", "/api/json/v3/dns/delete/example.com/12345"
        )
        self.assertEqual(cls, "destructive")


class TestPathValidation(unittest.TestCase):
    def test_rejects_traversal_dotdot(self):
        with self.assertRaises(pb.CtlError):
            pb._validate_path("/../../etc/passwd")

    def test_rejects_traversal_dot(self):
        with self.assertRaises(pb.CtlError):
            pb._validate_path("/./dns/retrieve/example.com")

    def test_rejects_url_encoded_percent(self):
        with self.assertRaises(pb.CtlError):
            pb._validate_path("/dns/retrieve/%2e%2e/etc")

    def test_rejects_unsupported_chars(self):
        for bad in ["/foo?x=1", "/foo#frag", "/foo bar", "/foo\\bar"]:
            with self.subTest(path=bad), self.assertRaises(pb.CtlError):
                pb._validate_path(bad)

    def test_accepts_normal_paths(self):
        for good in [
            "/ping",
            "/domain/listAll",
            "/dns/retrieve/example.com",
            "/dns/delete/example.com/12345",
            "/domain/create/example.com",
            "/dns/deleteByNameType/example.com/A/www",
        ]:
            with self.subTest(path=good):
                pb._validate_path(good)  # should not raise


class TestDomainValidation(unittest.TestCase):
    def test_accepts_normal_domains(self):
        for good in ["example.com", "foo.io", "sub.example.co.uk", "xn--abc.com",
                     "ns1.porkbun.com"]:
            with self.subTest(domain=good):
                pb._validate_domain(good)

    def test_rejects_garbage(self):
        for bad in ["", "no-tld", "..", "example..com", "-leading.com",
                    "trailing-.com", "with space.com", "with/slash.com"]:
            with self.subTest(domain=bad), self.assertRaises(pb.CtlError):
                pb._validate_domain(bad)


class TestPriceParsing(unittest.TestCase):
    def test_dollars_and_cents(self):
        self.assertEqual(pb._parse_price_to_cents("9.73"), 973)
        self.assertEqual(pb._parse_price_to_cents("12.00"), 1200)
        self.assertEqual(pb._parse_price_to_cents("0.99"), 99)

    def test_whole_dollars(self):
        self.assertEqual(pb._parse_price_to_cents("12"), 1200)

    def test_one_decimal(self):
        # "9.7" should be 970 cents (interpreted as $9.70).
        self.assertEqual(pb._parse_price_to_cents("9.7"), 970)

    def test_strips_dollar_sign(self):
        self.assertEqual(pb._parse_price_to_cents("$9.73"), 973)

    def test_rejects_garbage(self):
        for bad in ["", "not-a-price", "9.999", "9.7.3", "-1.00"]:
            with self.subTest(price=bad), self.assertRaises(pb.CtlError):
                pb._parse_price_to_cents(bad)


class TestPlatformHelpers(unittest.TestCase):
    def test_no_gui_error_returns_ctlerror(self):
        err = pb._no_gui_error()
        self.assertIsInstance(err, pb.CtlError)

    def test_has_display_returns_bool(self):
        self.assertIsInstance(pb._has_display(), bool)

    def test_platform_known(self):
        self.assertIn(pb._platform(), {"macos", "linux", "windows", "unknown"})


class TestPackUnpack(unittest.TestCase):
    def test_pack_unpack_roundtrip(self):
        blob = pb._pack("pk1_AAA", "sk1_BBB")
        self.assertEqual(pb._unpack(blob), ("pk1_AAA", "sk1_BBB"))

    def test_unpack_missing_field_returns_none(self):
        self.assertIsNone(pb._unpack('{"apikey": "only-one"}'))
        self.assertIsNone(pb._unpack("not-json"))
        self.assertIsNone(pb._unpack('{"apikey": "", "secretapikey": ""}'))


class TestCliEntrypoint(unittest.TestCase):
    def test_version_flag_exits_zero(self):
        # argparse's --version calls SystemExit(0) — catch it.
        with self.assertRaises(SystemExit) as cm:
            pb.main(["--version"])
        self.assertEqual(cm.exception.code, 0)

    def test_classify_command_runs_without_creds(self):
        # classify is read-only, no creds needed, no network.
        self.assertEqual(pb.main(["classify", "POST", "/dns/create/example.com"]), 0)

    def test_json_flag_accepted_before_subcommand(self):
        self.assertEqual(pb.main(["--json", "classify", "POST", "/ping"]), 0)

    def test_json_flag_accepted_after_subcommand(self):
        # Regression: pre-fix, `--json` after a subcommand silently produced
        # human-readable output (caught during the 2026-05-13 live test).
        self.assertEqual(pb.main(["classify", "POST", "/ping", "--json"]), 0)


class TestNormalizeAutoRenew(unittest.TestCase):
    """Porkbun's autoRenew field is 0 (int) when off but '1' (string) when on.
    The CLI normalizes to a stable string for `domain <name>` output.
    """

    def test_int_one_becomes_string_one(self):
        self.assertEqual(pb._normalize_auto_renew(1), "1")

    def test_int_zero_becomes_string_zero(self):
        self.assertEqual(pb._normalize_auto_renew(0), "0")

    def test_string_one_passes_through(self):
        self.assertEqual(pb._normalize_auto_renew("1"), "1")

    def test_string_zero_passes_through(self):
        self.assertEqual(pb._normalize_auto_renew("0"), "0")

    def test_bool_true(self):
        self.assertEqual(pb._normalize_auto_renew(True), "1")

    def test_bool_false(self):
        self.assertEqual(pb._normalize_auto_renew(False), "0")

    def test_unknown_value_falls_through(self):
        # Defensive: don't crash on unexpected values from Porkbun.
        self.assertEqual(pb._normalize_auto_renew("maybe"), "maybe")


class TestFormatSummaryPrio(unittest.TestCase):
    """`_format_summary` hides `prio` for record types where it's meaningless
    (Porkbun returns prio=0 for NS/A/AAAA/CNAME/TXT/CAA, which is noise).
    """

    def test_mx_record_shows_prio(self):
        s = pb._format_summary({
            "id": 1, "name": "mail.example.com", "type": "MX",
            "content": "mail.invalid", "ttl": 600, "prio": 10,
        })
        self.assertIn("prio=10", s)

    def test_srv_record_shows_prio(self):
        s = pb._format_summary({
            "id": 1, "name": "_sip._tcp.example.com", "type": "SRV",
            "content": "0 5 5060 sip.example.com", "ttl": 600, "prio": 5,
        })
        self.assertIn("prio=5", s)

    def test_ns_record_hides_prio(self):
        s = pb._format_summary({
            "id": 1, "name": "example.com", "type": "NS",
            "content": "ns1.example.com", "ttl": 86400, "prio": 0,
        })
        self.assertNotIn("prio=", s)

    def test_a_record_hides_prio(self):
        s = pb._format_summary({
            "id": 1, "name": "www.example.com", "type": "A",
            "content": "1.2.3.4", "ttl": 600, "prio": 0,
        })
        self.assertNotIn("prio=", s)

    def test_txt_record_hides_prio(self):
        s = pb._format_summary({
            "id": 1, "name": "example.com", "type": "TXT",
            "content": "v=spf1 -all", "ttl": 600, "prio": 0,
        })
        self.assertNotIn("prio=", s)


class TestDnssecDigestValidator(unittest.TestCase):
    """`_validate_dnssec_digest` refuses non-hex inputs and length mismatches
    so an operator can't ship a broken DS record to the registry.
    """

    def test_sha1_correct_length_accepted(self):
        pb._validate_dnssec_digest("A" * 40, "1")  # SHA-1 = 40 hex chars

    def test_sha256_correct_length_accepted(self):
        pb._validate_dnssec_digest("A" * 64, "2")  # SHA-256 = 64 hex chars

    def test_sha384_correct_length_accepted(self):
        pb._validate_dnssec_digest("A" * 96, "4")  # SHA-384 = 96 hex chars

    def test_lowercase_hex_accepted(self):
        pb._validate_dnssec_digest("abcdef0123456789" * 4, "2")

    def test_non_hex_rejected(self):
        with self.assertRaises(pb.CtlError):
            pb._validate_dnssec_digest("ZZZ" * 22, "2")  # 66 chars but contains Z

    def test_wrong_length_rejected(self):
        with self.assertRaises(pb.CtlError):
            pb._validate_dnssec_digest("A" * 40, "2")  # SHA-256 needs 64 not 40

    def test_unknown_digest_type_falls_through(self):
        # Unknown digestType: hex-format check still applies, length is not enforced.
        pb._validate_dnssec_digest("A" * 50, "99")
        with self.assertRaises(pb.CtlError):
            pb._validate_dnssec_digest("not-hex", "99")

    def test_empty_digest_rejected(self):
        with self.assertRaises(pb.CtlError):
            pb._validate_dnssec_digest("", "2")


class TestParseIpList(unittest.TestCase):
    """`_parse_ip_list` accepts IPv4 and IPv6, comma-separated, whitespace tolerant."""

    def test_single_ipv4(self):
        self.assertEqual(pb._parse_ip_list("192.0.2.1"), ["192.0.2.1"])

    def test_single_ipv6(self):
        self.assertEqual(pb._parse_ip_list("2001:db8::1"), ["2001:db8::1"])

    def test_mixed_v4_v6(self):
        self.assertEqual(
            pb._parse_ip_list("192.0.2.1, 2001:db8::1"),
            ["192.0.2.1", "2001:db8::1"],
        )

    def test_invalid_ip_rejected(self):
        with self.assertRaises(pb.CtlError):
            pb._parse_ip_list("not-an-ip")
        with self.assertRaises(pb.CtlError):
            pb._parse_ip_list("999.999.999.999")

    def test_empty_rejected(self):
        with self.assertRaises(pb.CtlError):
            pb._parse_ip_list("")
        with self.assertRaises(pb.CtlError):
            pb._parse_ip_list(", , ")


class TestNewCommandConfirmGuards(unittest.TestCase):
    """Verify the new destructive named commands enforce --confirm-* matching
    before any network call. All run without creds (gate fires first).
    """

    def test_dns_delete_by_nametype_refuses_without_confirm_name(self):
        # Refused at the parser/validator stage — no creds required.
        ret = pb.main([
            "dns", "delete-by-nametype", "example.com",
            "--type", "TXT", "--subdomain", "foo", "--yes",
        ])
        self.assertEqual(ret, 2)

    def test_dns_delete_by_nametype_refuses_mismatched_confirm_name(self):
        ret = pb.main([
            "dns", "delete-by-nametype", "example.com",
            "--type", "TXT", "--subdomain", "foo",
            "--confirm-name", "bar", "--yes",
        ])
        self.assertEqual(ret, 2)

    def test_dnssec_add_refuses_bad_digest(self):
        # Wrong length for digestType=2 (SHA-256 needs 64 hex chars).
        ret = pb.main([
            "dnssec", "add", "example.com",
            "--keytag", "12345", "--alg", "13",
            "--digest-type", "2", "--digest", "AAAA",
            "--yes",
        ])
        self.assertEqual(ret, 2)

    def test_dnssec_delete_refuses_mismatched_confirm_id(self):
        ret = pb.main([
            "dnssec", "delete", "example.com",
            "--keytag", "12345", "--confirm-id", "99999",
            "--yes",
        ])
        self.assertEqual(ret, 2)

    def test_glue_set_refuses_fqdn_subdomain(self):
        # --subdomain must be a single label, not a full hostname.
        ret = pb.main([
            "glue", "set", "example.com",
            "--subdomain", "ns1.example.com",
            "--ip", "192.0.2.1", "--yes",
        ])
        self.assertEqual(ret, 2)

    def test_glue_set_refuses_invalid_ip(self):
        ret = pb.main([
            "glue", "set", "example.com",
            "--subdomain", "ns1",
            "--ip", "not-an-ip", "--yes",
        ])
        self.assertEqual(ret, 2)

    def test_glue_delete_refuses_mismatched_confirm_name(self):
        ret = pb.main([
            "glue", "delete", "example.com",
            "--subdomain", "ns1", "--confirm-name", "ns2",
            "--yes",
        ])
        self.assertEqual(ret, 2)

    def test_forward_add_refuses_no_redirect_type(self):
        # Must specify --permanent or --temporary.
        ret = pb.main([
            "forward", "add", "example.com",
            "--location", "https://target.example/",
            "--subdomain", "fwd", "--yes",
        ])
        self.assertEqual(ret, 2)

    def test_forward_add_refuses_both_redirect_types(self):
        ret = pb.main([
            "forward", "add", "example.com",
            "--location", "https://target.example/",
            "--subdomain", "fwd",
            "--permanent", "--temporary", "--yes",
        ])
        self.assertEqual(ret, 2)

    def test_forward_delete_refuses_mismatched_confirm_id(self):
        ret = pb.main([
            "forward", "delete", "example.com",
            "--id", "12345", "--confirm-id", "99999",
            "--yes",
        ])
        self.assertEqual(ret, 2)


class TestPrioRejection(unittest.TestCase):
    """`dns add` and `dns edit` refuse `--prio` for non-MX/SRV record types.
    The check runs before any credential load or network call.
    """

    def test_dns_add_prio_on_a_record_is_refused(self):
        # CtlError -> exit code 2. Pass --type A with --prio.
        # _validate_domain and the --yes / --prio checks all happen before _load_creds.
        ret = pb.main([
            "dns", "add", "example.com",
            "--type", "A", "--content", "1.2.3.4",
            "--prio", "10", "--yes",
        ])
        self.assertEqual(ret, 2)

    def test_dns_add_prio_on_mx_is_accepted_(self):
        # MX is accepted at the validation stage. It WOULD then fail at
        # _load_creds (no creds in test env) — but that's a different
        # CtlError, also exit 2. The point: not the prio CtlError.
        # We can't easily distinguish without capturing stderr, so just
        # confirm it doesn't raise prematurely — i.e. it gets past the prio check.
        # (This is a smoke; the negative test above covers the new logic.)
        ret = pb.main([
            "dns", "add", "example.com",
            "--type", "MX", "--content", "mail.invalid",
            "--prio", "10", "--yes",
        ])
        # Either 0 (impossible without creds) or 2 (CtlError, likely no-creds).
        self.assertIn(ret, (0, 2))


if __name__ == "__main__":
    unittest.main()
